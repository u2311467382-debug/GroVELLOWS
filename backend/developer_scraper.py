"""
German Developer Projects Scraper
Scrapes project announcements from major German property developers
Tracks project schedules and timelines
Focus on NRW (Nordrhein-Westfalen) and Brandenburg regions
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re
import logging

logger = logging.getLogger(__name__)

class DeveloperProjectsScraper:
    """Scraper for German property developer project announcements"""
    
    # Region mapping
    REGIONS = {
        "NRW": ["Düsseldorf", "Köln", "Dortmund", "Essen", "Duisburg", "Bochum", "Wuppertal", 
                "Bielefeld", "Bonn", "Münster", "Gelsenkirchen", "Mönchengladbach", "Aachen",
                "Krefeld", "Oberhausen", "Hagen", "Hamm", "Mülheim", "Leverkusen", "Solingen",
                "Nordrhein-Westfalen", "NRW", "Ruhrgebiet"],
        "Brandenburg": ["Potsdam", "Cottbus", "Brandenburg an der Havel", "Frankfurt (Oder)",
                       "Oranienburg", "Falkensee", "Bernau", "Eberswalde", "Königs Wusterhausen",
                       "Brandenburg", "Spreewald", "Uckermark", "Barnim", "Havelland"],
        "Berlin": ["Berlin", "Berlin-Mitte", "Charlottenburg", "Kreuzberg", "Prenzlauer Berg",
                  "Friedrichshain", "Neukölln", "Tempelhof", "Spandau", "Pankow"],
    }
    
    # Major German property developers with their websites
    DEVELOPERS = [
        # Major national developers
        {"name": "CESA Group", "url": "https://www.cesa-group.de", "type": "residential"},
        {"name": "Vonovia", "url": "https://www.vonovia.de", "type": "residential"},
        {"name": "Deutsche Wohnen", "url": "https://www.deutsche-wohnen.com", "type": "residential"},
        {"name": "LEG Immobilien", "url": "https://www.leg-wohnen.de", "type": "residential"},
        {"name": "TAG Immobilien", "url": "https://www.tag-wohnen.de", "type": "residential"},
        {"name": "Instone Real Estate", "url": "https://www.instone.de", "type": "mixed"},
        {"name": "Bonava Deutschland", "url": "https://www.bonava.de", "type": "residential"},
        {"name": "Ten Brinke", "url": "https://www.tenbrinke.com", "type": "commercial"},
        {"name": "Pandion", "url": "https://www.pandion.de", "type": "residential"},
        {"name": "Greyfield Group", "url": "https://www.greyfield.de", "type": "mixed"},
        {"name": "BPD Immobilienentwicklung", "url": "https://www.bpd.de", "type": "residential"},
        {"name": "Catella", "url": "https://www.catella.com", "type": "commercial"},
        
        # NRW focused developers
        {"name": "Corpus Sireo", "url": "https://www.corpussireo.com", "type": "commercial", "region": "NRW"},
        {"name": "HOCHTIEF", "url": "https://www.hochtief.de", "type": "infrastructure", "region": "NRW"},
        {"name": "Strabag", "url": "https://www.strabag.de", "type": "infrastructure", "region": "NRW"},
        {"name": "Ed. Züblin", "url": "https://www.zueblin.de", "type": "commercial", "region": "NRW"},
        {"name": "Aurelis Real Estate", "url": "https://www.aurelis-real-estate.de", "type": "commercial", "region": "NRW"},
        {"name": "Gerchgroup", "url": "https://www.gerchgroup.de", "type": "mixed", "region": "NRW"},
        
        # Brandenburg/Berlin focused developers  
        {"name": "Gewobag", "url": "https://www.gewobag.de", "type": "residential", "region": "Brandenburg"},
        {"name": "HOWOGE", "url": "https://www.howoge.de", "type": "residential", "region": "Brandenburg"},
        {"name": "Degewo", "url": "https://www.degewo.de", "type": "residential", "region": "Brandenburg"},
        {"name": "WBM", "url": "https://www.wbm.de", "type": "residential", "region": "Brandenburg"},
        {"name": "GESOBAU", "url": "https://www.gesobau.de", "type": "residential", "region": "Brandenburg"},
        {"name": "STADT UND LAND", "url": "https://www.stadtundland.de", "type": "residential", "region": "Brandenburg"},
        {"name": "BUWOG", "url": "https://www.buwog.de", "type": "residential", "region": "Brandenburg"},
    ]
    
    def __init__(self, db):
        self.db = db
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8'
        }
    
    async def fetch_page(self, url: str) -> str:
        """Fetch a page with error handling"""
        try:
            async with self.session.get(url, headers=self.headers, timeout=30, ssl=False) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"Failed to fetch {url}: Status {response.status}")
                    return ""
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return ""
    
    def detect_region(self, text: str) -> Optional[str]:
        """Detect which region a project belongs to based on location text"""
        text_lower = text.lower()
        
        for region, cities in self.REGIONS.items():
            for city in cities:
                if city.lower() in text_lower:
                    return region
        
        return None
    
    def extract_budget(self, text: str) -> Optional[str]:
        """Extract budget/investment amount from text"""
        patterns = [
            r'(\d+(?:[\.,]\d+)?)\s*(?:Mio\.?|Millionen?)\s*(?:Euro|EUR|€)',
            r'(\d+(?:[\.,]\d+)?)\s*(?:Mrd\.?|Milliarden?)\s*(?:Euro|EUR|€)',
            r'(?:Euro|EUR|€)\s*(\d+(?:[\.,]\d+)?)\s*(?:Mio\.?|Millionen?)',
            r'Investition(?:svolumen)?\s*(?:von)?\s*(?:ca\.?)?\s*(\d+(?:[\.,]\d+)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount = match.group(1).replace(',', '.')
                if 'mrd' in text.lower() or 'milliard' in text.lower():
                    return f"€{amount} Mrd."
                return f"€{amount} Mio."
        
        return None
    
    def extract_timeline(self, text: str) -> Dict:
        """Extract project timeline information"""
        timeline = {
            "start_date": None,
            "completion_date": None,
            "phases": []
        }
        
        # Look for year patterns
        year_pattern = r'(20[2-3]\d)'
        years = re.findall(year_pattern, text)
        
        if years:
            years = sorted(set(years))
            if len(years) >= 1:
                timeline["start_date"] = f"01.01.{years[0]}"
            if len(years) >= 2:
                timeline["completion_date"] = f"31.12.{years[-1]}"
            elif len(years) == 1:
                # Assume 2-3 year project
                completion_year = int(years[0]) + 2
                timeline["completion_date"] = f"31.12.{completion_year}"
        
        # Common project phases
        phase_keywords = {
            "Planung": ["planung", "geplant", "entwurf", "konzept"],
            "Genehmigung": ["genehmigung", "baugenehmigung", "genehmigt"],
            "Baustart": ["baustart", "baubeginn", "spatenstich", "grundsteinlegung"],
            "Rohbau": ["rohbau", "rohbauarbeiten"],
            "Innenausbau": ["innenausbau", "ausbau"],
            "Fertigstellung": ["fertigstellung", "fertiggestellt", "bezugsfertig", "übergabe"],
        }
        
        text_lower = text.lower()
        for phase_name, keywords in phase_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    timeline["phases"].append({
                        "phase": phase_name,
                        "status": "ongoing" if phase_name in ["Planung", "Genehmigung"] else "pending",
                        "progress": 0
                    })
                    break
        
        # Set default phases if none found
        if not timeline["phases"]:
            timeline["phases"] = [
                {"phase": "Planung", "status": "ongoing", "progress": 50},
                {"phase": "Genehmigung", "status": "pending", "progress": 0},
                {"phase": "Baustart", "status": "pending", "progress": 0},
                {"phase": "Fertigstellung", "status": "pending", "progress": 0},
            ]
        
        return timeline
    
    def determine_project_status(self, text: str) -> str:
        """Determine project status from text"""
        text_lower = text.lower()
        
        if any(kw in text_lower for kw in ['fertiggestellt', 'abgeschlossen', 'übergeben', 'bezogen']):
            return 'completed'
        elif any(kw in text_lower for kw in ['verzöger', 'aufgeschoben', 'pausiert']):
            return 'delayed'
        elif any(kw in text_lower for kw in ['bau', 'bauarbeiten', 'fortschritt', 'rohbau', 'errichtet']):
            return 'ongoing'
        else:
            return 'planning'
    
    def determine_project_type(self, text: str, developer_type: str) -> str:
        """Determine project type from text"""
        text_lower = text.lower()
        
        if any(kw in text_lower for kw in ['wohnung', 'wohnhaus', 'residential', 'appartement', 'eigentum']):
            return 'Residential'
        elif any(kw in text_lower for kw in ['büro', 'office', 'gewerbe', 'geschäft']):
            return 'Commercial'
        elif any(kw in text_lower for kw in ['hotel', 'gastgewerbe']):
            return 'Hospitality'
        elif any(kw in text_lower for kw in ['logistik', 'lager', 'warehouse', 'industrie']):
            return 'Industrial'
        elif any(kw in text_lower for kw in ['mixed', 'quartier', 'stadtentwicklung']):
            return 'Mixed-Use'
        elif developer_type == 'residential':
            return 'Residential'
        elif developer_type == 'commercial':
            return 'Commercial'
        else:
            return 'Mixed-Use'
    
    async def scrape_developer_news(self, developer: Dict) -> List[Dict]:
        """Scrape project news from a developer's website"""
        projects = []
        
        # Common news/press page paths
        news_paths = [
            "/news", "/aktuelles", "/presse", "/pressemitteilungen", 
            "/neuigkeiten", "/projekte", "/referenzen", "/portfolio"
        ]
        
        for path in news_paths:
            url = f"{developer['url']}{path}"
            html = await self.fetch_page(url)
            
            if html:
                soup = BeautifulSoup(html, 'lxml')
                
                # Look for news/project articles
                articles = soup.select('article, .news-item, .project-item, .card, .teaser, [class*="news"], [class*="project"]')
                
                for article in articles[:10]:  # Limit per page
                    try:
                        # Extract title
                        title_elem = article.select_one('h1, h2, h3, h4, .title, .headline')
                        title = title_elem.get_text(strip=True) if title_elem else None
                        
                        if not title or len(title) < 10:
                            continue
                        
                        # Skip if not project-related
                        project_keywords = ['projekt', 'bau', 'neubau', 'entwicklung', 'quartier', 
                                          'wohnung', 'immobilie', 'grundsteinlegung', 'fertigstellung']
                        if not any(kw in title.lower() for kw in project_keywords):
                            continue
                        
                        # Extract description
                        desc_elem = article.select_one('p, .description, .excerpt, .summary, .text')
                        description = desc_elem.get_text(strip=True) if desc_elem else title
                        
                        # Extract link
                        link_elem = article.select_one('a[href]')
                        link = link_elem.get('href', '') if link_elem else ''
                        if link and not link.startswith('http'):
                            link = f"{developer['url']}{link}"
                        
                        # Combine text for analysis
                        full_text = f"{title} {description}"
                        
                        # Detect region
                        region = self.detect_region(full_text) or developer.get('region', 'Germany')
                        
                        # Skip if not in target regions (NRW or Brandenburg) unless it's a major project
                        budget = self.extract_budget(full_text)
                        
                        # Extract timeline
                        timeline = self.extract_timeline(full_text)
                        
                        # Determine status
                        status = self.determine_project_status(full_text)
                        
                        # Determine project type
                        project_type = self.determine_project_type(full_text, developer.get('type', 'mixed'))
                        
                        # Extract location from text
                        location = region
                        for region_name, cities in self.REGIONS.items():
                            for city in cities:
                                if city.lower() in full_text.lower():
                                    location = f"{city}, {region_name}"
                                    break
                        
                        project = {
                            'developer_name': developer['name'],
                            'developer_url': developer['url'],
                            'project_name': title,
                            'description': description[:500] if description else f"Projekt von {developer['name']}",
                            'location': location,
                            'region': region if region in ['NRW', 'Brandenburg', 'Berlin'] else 'Other',
                            'budget': budget,
                            'project_type': project_type,
                            'status': status,
                            'start_date': timeline.get('start_date') or datetime.utcnow().strftime('%Y-%m-%d'),
                            'expected_completion': timeline.get('completion_date') or (datetime.utcnow() + timedelta(days=730)).strftime('%Y-%m-%d'),
                            'timeline_phases': timeline.get('phases', []),
                            'source_url': link or url,
                            'scraped_at': datetime.utcnow(),
                        }
                        
                        projects.append(project)
                        
                    except Exception as e:
                        logger.debug(f"Error parsing article from {developer['name']}: {e}")
                        continue
                
                await asyncio.sleep(0.3)  # Rate limiting
        
        return projects
    
    async def scrape_all_developers(self) -> List[Dict]:
        """Scrape projects from all developers"""
        all_projects = []
        
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            for developer in self.DEVELOPERS:
                logger.info(f"Scraping {developer['name']}...")
                try:
                    projects = await self.scrape_developer_news(developer)
                    all_projects.extend(projects)
                    logger.info(f"  Found {len(projects)} projects from {developer['name']}")
                except Exception as e:
                    logger.error(f"Error scraping {developer['name']}: {e}")
                
                await asyncio.sleep(0.5)  # Rate limiting between developers
        
        # Deduplicate by project name
        seen_names = set()
        unique_projects = []
        for project in all_projects:
            name_key = project['project_name'].lower()[:50]
            if name_key not in seen_names:
                seen_names.add(name_key)
                unique_projects.append(project)
        
        logger.info(f"Total unique developer projects found: {len(unique_projects)}")
        return unique_projects
    
    async def save_projects(self, projects: List[Dict]) -> int:
        """Save projects to database"""
        added = 0
        
        for project in projects:
            # Check if project already exists
            existing = await self.db.developer_projects.find_one({
                'project_name': project['project_name'],
                'developer_name': project['developer_name']
            })
            
            if not existing:
                project['created_at'] = datetime.utcnow()
                project['updated_at'] = datetime.utcnow()
                await self.db.developer_projects.insert_one(project)
                added += 1
            else:
                # Update existing project
                await self.db.developer_projects.update_one(
                    {'_id': existing['_id']},
                    {'$set': {
                        'status': project['status'],
                        'timeline_phases': project['timeline_phases'],
                        'updated_at': datetime.utcnow()
                    }}
                )
        
        return added
    
    async def run(self) -> int:
        """Run the full scraping process"""
        logger.info("Starting German Developer Projects Scraper...")
        
        projects = await self.scrape_all_developers()
        added = await self.save_projects(projects)
        
        logger.info(f"Developer Projects Scraper complete. Added {added} new projects.")
        return added


# Sample/seed data for immediate display
def get_sample_developer_projects() -> List[Dict]:
    """Generate sample developer projects for NRW and Brandenburg regions"""
    
    sample_projects = [
        # NRW Projects
        {
            "developer_name": "CESA Group",
            "project_name": "Quartier Belsenpark Düsseldorf",
            "description": "Entwicklung eines neuen Stadtquartiers mit 500 Wohnungen und Gewerbeflächen im Düsseldorfer Hafen. Nachhaltige Bauweise mit Fokus auf erneuerbare Energien.",
            "location": "Düsseldorf, NRW",
            "region": "NRW",
            "budget": "€180 Mio.",
            "project_type": "Mixed-Use",
            "status": "ongoing",
            "start_date": "2024-03-01",
            "expected_completion": "2027-06-30",
            "timeline_phases": [
                {"phase": "Planung", "status": "completed", "progress": 100},
                {"phase": "Genehmigung", "status": "completed", "progress": 100},
                {"phase": "Baustart", "status": "completed", "progress": 100},
                {"phase": "Rohbau", "status": "ongoing", "progress": 45},
                {"phase": "Fertigstellung", "status": "pending", "progress": 0},
            ],
            "source_url": "https://www.cesa-group.de/projekte",
        },
        {
            "developer_name": "Vonovia",
            "project_name": "Wohnquartier Köln-Mülheim",
            "description": "Neubau von 320 energieeffizienten Mietwohnungen mit KfW-40 Standard. Grüne Innenhöfe und moderne Mobilitätskonzepte.",
            "location": "Köln, NRW",
            "region": "NRW",
            "budget": "€95 Mio.",
            "project_type": "Residential",
            "status": "planning",
            "start_date": "2025-01-15",
            "expected_completion": "2028-03-31",
            "timeline_phases": [
                {"phase": "Planung", "status": "ongoing", "progress": 75},
                {"phase": "Genehmigung", "status": "pending", "progress": 20},
                {"phase": "Baustart", "status": "pending", "progress": 0},
                {"phase": "Fertigstellung", "status": "pending", "progress": 0},
            ],
            "source_url": "https://www.vonovia.de/projekte",
        },
        {
            "developer_name": "Instone Real Estate",
            "project_name": "Rheinpark Residence Duisburg",
            "description": "Exklusives Wohnprojekt direkt am Rhein mit 180 Eigentumswohnungen und Penthäusern. Premium-Ausstattung und Rheinblick.",
            "location": "Duisburg, NRW",
            "region": "NRW",
            "budget": "€120 Mio.",
            "project_type": "Residential",
            "status": "ongoing",
            "start_date": "2024-06-01",
            "expected_completion": "2026-12-31",
            "timeline_phases": [
                {"phase": "Planung", "status": "completed", "progress": 100},
                {"phase": "Genehmigung", "status": "completed", "progress": 100},
                {"phase": "Baustart", "status": "completed", "progress": 100},
                {"phase": "Rohbau", "status": "ongoing", "progress": 60},
                {"phase": "Innenausbau", "status": "pending", "progress": 10},
            ],
            "source_url": "https://www.instone.de/projekte",
        },
        {
            "developer_name": "Ten Brinke",
            "project_name": "Business Park Essen-Rüttenscheid",
            "description": "Moderner Bürokomplex mit 25.000 m² Gewerbefläche. DGNB Gold Zertifizierung angestrebt. Flexible Grundrisse für verschiedene Nutzer.",
            "location": "Essen, NRW",
            "region": "NRW",
            "budget": "€85 Mio.",
            "project_type": "Commercial",
            "status": "planning",
            "start_date": "2025-04-01",
            "expected_completion": "2027-09-30",
            "timeline_phases": [
                {"phase": "Planung", "status": "ongoing", "progress": 60},
                {"phase": "Genehmigung", "status": "pending", "progress": 0},
                {"phase": "Baustart", "status": "pending", "progress": 0},
                {"phase": "Fertigstellung", "status": "pending", "progress": 0},
            ],
            "source_url": "https://www.tenbrinke.com/projekte",
        },
        {
            "developer_name": "LEG Immobilien",
            "project_name": "Wohnanlage Dortmund-Phoenix",
            "description": "Revitalisierung des Phoenix-See Areals mit 240 modernen Mietwohnungen. Barrierefreie Zugänge und Smart-Home Technologie.",
            "location": "Dortmund, NRW",
            "region": "NRW",
            "budget": "€72 Mio.",
            "project_type": "Residential",
            "status": "ongoing",
            "start_date": "2024-02-01",
            "expected_completion": "2026-08-31",
            "timeline_phases": [
                {"phase": "Planung", "status": "completed", "progress": 100},
                {"phase": "Genehmigung", "status": "completed", "progress": 100},
                {"phase": "Baustart", "status": "completed", "progress": 100},
                {"phase": "Rohbau", "status": "completed", "progress": 100},
                {"phase": "Innenausbau", "status": "ongoing", "progress": 35},
            ],
            "source_url": "https://www.leg-wohnen.de/projekte",
        },
        
        # Brandenburg Projects
        {
            "developer_name": "HOWOGE",
            "project_name": "Wohnquartier Potsdam-Babelsberg",
            "description": "Entwicklung eines nachhaltigen Wohnquartiers mit 400 Wohnungen und sozialer Infrastruktur. Nahe dem Filmpark Babelsberg.",
            "location": "Potsdam, Brandenburg",
            "region": "Brandenburg",
            "budget": "€145 Mio.",
            "project_type": "Residential",
            "status": "ongoing",
            "start_date": "2024-01-15",
            "expected_completion": "2027-04-30",
            "timeline_phases": [
                {"phase": "Planung", "status": "completed", "progress": 100},
                {"phase": "Genehmigung", "status": "completed", "progress": 100},
                {"phase": "Baustart", "status": "completed", "progress": 100},
                {"phase": "Rohbau", "status": "ongoing", "progress": 30},
                {"phase": "Fertigstellung", "status": "pending", "progress": 0},
            ],
            "source_url": "https://www.howoge.de/projekte",
        },
        {
            "developer_name": "Degewo",
            "project_name": "Stadtquartier Cottbus-Süd",
            "description": "Neues Stadtquartier mit 280 Wohnungen, Kindergarten und Nahversorgung. Energieeffiziente Bauweise nach KfW-55 Standard.",
            "location": "Cottbus, Brandenburg",
            "region": "Brandenburg",
            "budget": "€88 Mio.",
            "project_type": "Mixed-Use",
            "status": "planning",
            "start_date": "2025-06-01",
            "expected_completion": "2028-12-31",
            "timeline_phases": [
                {"phase": "Planung", "status": "ongoing", "progress": 80},
                {"phase": "Genehmigung", "status": "pending", "progress": 15},
                {"phase": "Baustart", "status": "pending", "progress": 0},
                {"phase": "Fertigstellung", "status": "pending", "progress": 0},
            ],
            "source_url": "https://www.degewo.de/projekte",
        },
        {
            "developer_name": "BUWOG",
            "project_name": "Wohnen am Griebnitzsee",
            "description": "Premium-Wohnanlage mit 120 Eigentumswohnungen und direktem Seezugang. Hochwertige Ausstattung und großzügige Balkone.",
            "location": "Potsdam-Babelsberg, Brandenburg",
            "region": "Brandenburg",
            "budget": "€65 Mio.",
            "project_type": "Residential",
            "status": "ongoing",
            "start_date": "2024-04-01",
            "expected_completion": "2026-10-31",
            "timeline_phases": [
                {"phase": "Planung", "status": "completed", "progress": 100},
                {"phase": "Genehmigung", "status": "completed", "progress": 100},
                {"phase": "Baustart", "status": "completed", "progress": 100},
                {"phase": "Rohbau", "status": "ongoing", "progress": 70},
                {"phase": "Innenausbau", "status": "pending", "progress": 5},
            ],
            "source_url": "https://www.buwog.de/projekte",
        },
        {
            "developer_name": "Gewobag",
            "project_name": "Wohnpark Falkensee",
            "description": "Familienfreundliche Wohnanlage mit 200 Mietwohnungen am Stadtrand. Großzügige Grünflächen und Spielplätze.",
            "location": "Falkensee, Brandenburg",
            "region": "Brandenburg",
            "budget": "€55 Mio.",
            "project_type": "Residential",
            "status": "planning",
            "start_date": "2025-03-01",
            "expected_completion": "2027-08-31",
            "timeline_phases": [
                {"phase": "Planung", "status": "ongoing", "progress": 65},
                {"phase": "Genehmigung", "status": "pending", "progress": 0},
                {"phase": "Baustart", "status": "pending", "progress": 0},
                {"phase": "Fertigstellung", "status": "pending", "progress": 0},
            ],
            "source_url": "https://www.gewobag.de/projekte",
        },
        {
            "developer_name": "STADT UND LAND",
            "project_name": "Quartier Bernau-Friedenstal",
            "description": "Neuentwicklung eines Wohnquartiers mit 350 Wohnungen und Gewerbeeinheiten. S-Bahn Anbindung nach Berlin.",
            "location": "Bernau, Brandenburg",
            "region": "Brandenburg",
            "budget": "€110 Mio.",
            "project_type": "Mixed-Use",
            "status": "ongoing",
            "start_date": "2024-05-15",
            "expected_completion": "2027-11-30",
            "timeline_phases": [
                {"phase": "Planung", "status": "completed", "progress": 100},
                {"phase": "Genehmigung", "status": "completed", "progress": 100},
                {"phase": "Baustart", "status": "completed", "progress": 100},
                {"phase": "Rohbau", "status": "ongoing", "progress": 25},
                {"phase": "Fertigstellung", "status": "pending", "progress": 0},
            ],
            "source_url": "https://www.stadtundland.de/projekte",
        },
        {
            "developer_name": "WBM",
            "project_name": "Wohnanlage Oranienburg-Nord",
            "description": "Bezahlbarer Wohnraum mit 160 Wohnungen für Familien und Senioren. Energetisch optimierte Bauweise.",
            "location": "Oranienburg, Brandenburg",
            "region": "Brandenburg",
            "budget": "€42 Mio.",
            "project_type": "Residential",
            "status": "planning",
            "start_date": "2025-09-01",
            "expected_completion": "2028-02-28",
            "timeline_phases": [
                {"phase": "Planung", "status": "ongoing", "progress": 40},
                {"phase": "Genehmigung", "status": "pending", "progress": 0},
                {"phase": "Baustart", "status": "pending", "progress": 0},
                {"phase": "Fertigstellung", "status": "pending", "progress": 0},
            ],
            "source_url": "https://www.wbm.de/projekte",
        },
    ]
    
    # Add timestamps
    for project in sample_projects:
        project['created_at'] = datetime.utcnow()
        project['updated_at'] = datetime.utcnow()
        project['scraped_at'] = datetime.utcnow()
    
    return sample_projects


async def seed_developer_projects(db) -> int:
    """Seed database with sample developer projects"""
    # Clear existing
    await db.developer_projects.delete_many({})
    
    # Insert sample projects
    projects = get_sample_developer_projects()
    if projects:
        await db.developer_projects.insert_many(projects)
    
    logger.info(f"Seeded {len(projects)} developer projects")
    return len(projects)
