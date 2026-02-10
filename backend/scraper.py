"""
Live Tender Scraper for German Construction Tender Portals
Scrapes public tender data from official German government portals
"""

import aiohttp
import asyncio
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import logging
import re
from typing import List, Dict, Optional
import hashlib

logger = logging.getLogger(__name__)

class TenderScraper:
    """Base scraper class for German tender portals"""
    
    def __init__(self):
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8',
        }
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession(headers=self.headers)
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def generate_tender_id(self, title: str, platform: str, deadline: str) -> str:
        """Generate unique ID for tender deduplication"""
        unique_string = f"{title}_{platform}_{deadline}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:16]
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text.strip())
    
    def parse_german_date(self, date_str: str) -> Optional[datetime]:
        """Parse German date formats"""
        if not date_str:
            return None
        
        date_str = self.clean_text(date_str)
        formats = [
            "%d.%m.%Y",
            "%d.%m.%Y %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d. %B %Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def parse_budget(self, budget_str: str) -> Optional[str]:
        """Parse and normalize budget strings"""
        if not budget_str:
            return None
        
        # Extract numbers and format
        numbers = re.findall(r'[\d.,]+', budget_str)
        if numbers:
            amount = numbers[0].replace('.', '').replace(',', '.')
            try:
                value = float(amount)
                if value >= 1000000:
                    return f"€{value/1000000:.1f}M"
                elif value >= 1000:
                    return f"€{value/1000:.0f}K"
                else:
                    return f"€{value:.0f}"
            except ValueError:
                pass
        
        return budget_str if budget_str else None
    
    def categorize_tender(self, title: str, description: str) -> Dict[str, str]:
        """Categorize tender based on content - focused on construction project management"""
        text = f"{title} {description}".lower()
        
        # Check if this is a relevant construction/project management tender
        construction_keywords = [
            'bau', 'construction', 'neubau', 'umbau', 'sanierung', 'renovierung',
            'architektur', 'architect', 'planung', 'planning', 'ingenieur', 'engineer',
            'hochbau', 'tiefbau', 'gebäude', 'building', 'projekt', 'project',
            'immobilie', 'real estate', 'facility', 'facilities', 'infrastruktur',
            'wettbewerb', 'competition', 'controlling', 'management'
        ]
        
        is_relevant = any(kw in text for kw in construction_keywords)
        
        # Category detection - focused on construction project management services
        category = "General"
        
        # Integrierte Projektabwicklung (German term for IPA)
        if any(word in text for word in ['integrierte projektabwicklung', 'ipa verfahren', 'allianzvertrag', 'projektallianzen']):
            category = "Integrierte Projektabwicklung"
        # Integrated Project Management
        elif any(word in text for word in ['integrated project management', 'integriertes projektmanagement', 'gesamtprojektmanagement']):
            category = "Integrated Project Management"
        # PMO - Project Management Office
        elif any(word in text for word in ['pmo', 'project management office', 'projektmanagementbüro', 'projektbüro']):
            category = "PMO"
        # Wettbewerbsbegleitung - Competition Management
        elif any(word in text for word in ['wettbewerbsbegleitung', 'wettbewerb', 'competition management', 'architekturwettbewerb', 'vergabewettbewerb']):
            category = "Wettbewerbsbegleitung"
        # Finanzcontrolling - Financial Controlling
        elif any(word in text for word in ['finanzcontrolling', 'financial controlling', 'finanzsteuerung', 'budgetcontrolling', 'kostencontrolling']):
            category = "Finanzcontrolling"
        # Agiles Projektmanagement - Agile Project Management
        elif any(word in text for word in ['agil', 'agile', 'scrum', 'kanban', 'agiles projektmanagement', 'agile project']):
            category = "Agiles Projektmanagement"
        # Projekt Coaching - Project Coaching
        elif any(word in text for word in ['projekt coaching', 'project coaching', 'projektcoaching', 'bauherrenberatung', 'projektberatung']):
            category = "Projekt Coaching"
        # Nutzermanagement - User Management
        elif any(word in text for word in ['nutzermanagement', 'user management', 'nutzerbetreuung', 'nutzerkoordination', 'stakeholder management']):
            category = "Nutzermanagement"
        # Krisenmanagement - Crisis Management
        elif any(word in text for word in ['krisenmanagement', 'crisis management', 'konfliktmanagement', 'claim management', 'claimmanagement']):
            category = "Krisenmanagement"
        # Vertragsmanagement - Contract Management
        elif any(word in text for word in ['vertragsmanagement', 'contract management', 'vertragssteuerung', 'nachtragsmanagement', 'vertragscontrolling']):
            category = "Vertragsmanagement"
        # Risikomanagement - Risk Management
        elif any(word in text for word in ['risikomanagement', 'risk management', 'risikoanalyse', 'risikobewertung', 'risikosteuerung']):
            category = "Risikomanagement"
        # Lean Management
        elif any(word in text for word in ['lean', 'lean construction', 'lean management', 'prozessoptimierung']):
            category = "Lean Management"
        # Construction Supervision
        elif any(word in text for word in ['bauüberwachung', 'construction supervision', 'bauleitung', 'bauaufsicht', 'baubegleitung', 'objektüberwachung']):
            category = "Bauüberwachung"
        # Cost Management
        elif any(word in text for word in ['kostenmanagement', 'cost management', 'kostensteuerung', 'kostenkontrolle', 'kalkulation']):
            category = "Kostenmanagement"
        # Project Management (general)
        elif any(word in text for word in ['projektmanagement', 'project management', 'projektsteuerung', 'projektleitung']):
            category = "Projektmanagement"
        # Procurement
        elif any(word in text for word in ['beschaffung', 'procurement', 'einkauf', 'vergabemanagement']):
            category = "Beschaffungsmanagement"
        
        # Building typology detection - more keywords
        building_typology = None
        if any(word in text for word in ['krankenhaus', 'klinik', 'hospital', 'medizin', 'gesundheit', 'pflege', 'praxis', 'ambulanz']):
            building_typology = "Healthcare"
        elif any(word in text for word in ['rechenzentrum', 'data center', 'datacenter', 'serverraum', 'it-infrastruktur']):
            building_typology = "Data Center"
        elif any(word in text for word in ['wohn', 'residential', 'apartment', 'wohnung', 'mehrfamilienhaus', 'einfamilienhaus', 'siedlung']):
            building_typology = "Residential"
        elif any(word in text for word in ['büro', 'office', 'gewerbe', 'commercial', 'geschäftshaus', 'verwaltung']):
            building_typology = "Commercial"
        elif any(word in text for word in ['mixed', 'gemischt', 'quartier']):
            building_typology = "Mixed-Use"
        elif any(word in text for word in ['industrie', 'industrial', 'fabrik', 'werk', 'produktion', 'lager', 'logistik']):
            building_typology = "Industrial"
        elif any(word in text for word in ['infrastruktur', 'brücke', 'tunnel', 'straße', 'autobahn', 'schiene', 'bahn', 'verkehr']):
            building_typology = "Infrastructure"
        elif any(word in text for word in ['schule', 'universität', 'bildung', 'education', 'hochschule', 'gymnasium', 'campus']):
            building_typology = "Education"
        elif any(word in text for word in ['sport', 'stadion', 'arena', 'schwimmbad', 'turnhalle']):
            building_typology = "Sports"
        elif any(word in text for word in ['hotel', 'gastro', 'restaurant', 'hospitality']):
            building_typology = "Hospitality"
        
        return {"category": category, "building_typology": building_typology, "is_relevant": is_relevant}
    
    def generate_application_url(self, title: str, platform_source: str, platform_url: str) -> str:
        """Generate a search URL to find the specific tender on the platform"""
        from urllib.parse import quote_plus
        
        # Clean and encode the title for search
        search_title = title[:80]  # Limit length
        encoded_title = quote_plus(search_title)
        
        # Platform-specific search URLs
        if 'Bayern' in platform_source:
            return f"https://www.auftraege.bayern.de/NetServer/PublicationSearchControllerServlet?searchText={encoded_title}"
        elif 'NRW' in platform_source:
            return f"https://www.evergabe.nrw.de/VMPSatellite/public/search?q={encoded_title}"
        elif 'Berlin' in platform_source:
            return f"https://www.berlin.de/vergabeplattform/veroeffentlichungen/bekanntmachungen/?q={encoded_title}"
        elif 'Hamburg' in platform_source:
            return f"https://fbhh-evergabe.web.hamburg.de/evergabe.bieter/eva/supplierportal/fhh/subproject/search?searchText={encoded_title}"
        elif 'Sachsen' in platform_source and 'Anhalt' not in platform_source:
            return f"https://www.sachsen-vergabe.de/vergabe/bekanntmachung/?search={encoded_title}"
        elif 'Baden-Württemberg' in platform_source or 'bw' in platform_source.lower():
            return f"https://vergabe.landbw.de/NetServer/PublicationSearchControllerServlet?searchText={encoded_title}"
        elif 'TED' in platform_source or 'Europa' in platform_source:
            return f"https://ted.europa.eu/de/search/result?q={encoded_title}"
        elif 'Bund' in platform_source:
            return f"https://www.service.bund.de/Content/DE/Ausschreibungen/Suche/Ergebnis.html?searchText={encoded_title}"
        # New platforms from PDF
        elif 'Hessen' in platform_source or 'HAD' in platform_source:
            return f"https://www.had.de/NetServer/PublicationSearchControllerServlet?searchText={encoded_title}"
        elif 'Niedersachsen' in platform_source:
            return f"https://vergabe.niedersachsen.de/NetServer/PublicationSearchControllerServlet?searchText={encoded_title}"
        elif 'Bremen' in platform_source:
            return f"https://www.vergabe.bremen.de/NetServer/PublicationSearchControllerServlet?searchText={encoded_title}"
        elif 'Brandenburg' in platform_source:
            return f"https://vergabemarktplatz.brandenburg.de/VMPSatellite/public/search?q={encoded_title}"
        elif 'Rheinland-Pfalz' in platform_source or 'RLP' in platform_source:
            return f"https://www.vergabe.rlp.de/VMPSatellite/public/search?q={encoded_title}"
        elif 'Saarland' in platform_source:
            return f"https://vergabe.saarland/NetServer/PublicationSearchControllerServlet?searchText={encoded_title}"
        elif 'Sachsen-Anhalt' in platform_source:
            return f"https://www.evergabe.sachsen-anhalt.de/NetServer/PublicationSearchControllerServlet?searchText={encoded_title}"
        elif 'Schleswig-Holstein' in platform_source:
            return f"https://www.e-vergabe-sh.de/NetServer/PublicationSearchControllerServlet?searchText={encoded_title}"
        elif 'Thüringen' in platform_source:
            return f"https://www.portal.thueringen.de/vergabe?search={encoded_title}"
        # National platforms
        elif 'DTVP' in platform_source:
            return f"https://www.dtvp.de/Center/common/project/search.do?search={encoded_title}"
        elif 'eVergabe.de' in platform_source or 'Evergabe.de' in platform_source:
            return f"https://www.evergabe.de/unterlagen?searchText={encoded_title}"
        elif 'Öffentliche Vergabe' in platform_source:
            return f"https://www.oeffentlichevergabe.de/search?q={encoded_title}"
        # Switzerland
        elif 'SIMAP' in platform_source or 'simap.ch' in platform_source.lower():
            return f"https://www.simap.ch/shabforms/COMMON/search/searchresultListAction.do?searchString={encoded_title}"
        # Hospital platforms
        elif 'Charité' in platform_source:
            return f"https://vergabeplattform.charite.de/search?q={encoded_title}"
        elif 'Vivantes' in platform_source:
            return f"https://www.vivantes.de/unternehmen/ausschreibungen?search={encoded_title}"
        elif 'UKE' in platform_source or 'KFE' in platform_source:
            return f"https://www.uke.de/organisationsstruktur/tochtergesellschaften/kfe/ausschreibungen?search={encoded_title}"
        else:
            # Fallback to platform URL
            return platform_url


class BundDeScraper(TenderScraper):
    """Scraper for Bund.de - German Federal Government Tenders"""
    
    BASE_URL = "https://www.service.bund.de"
    SEARCH_URL = "https://www.service.bund.de/Content/DE/Ausschreibungen/Suche/Formular.html"
    
    async def scrape(self, max_results: int = 50) -> List[Dict]:
        """Scrape tenders from Bund.de"""
        tenders = []
        
        try:
            # Note: Bund.de requires specific parameters and may have anti-bot measures
            # This is a simplified implementation
            search_params = {
                'resultsPerPage': str(min(max_results, 100)),
                'sortOrder': 'dateDesc',
            }
            
            async with self.session.get(
                f"{self.BASE_URL}/Content/DE/Ausschreibungen/Suche/Ergebnis.html",
                params=search_params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    # Parse tender listings
                    tender_items = soup.select('.searchresult-item, .result-item, article')
                    
                    for item in tender_items[:max_results]:
                        try:
                            tender = self._parse_tender_item(item)
                            if tender:
                                tenders.append(tender)
                        except Exception as e:
                            logger.warning(f"Error parsing Bund.de tender: {e}")
                            continue
                else:
                    logger.warning(f"Bund.de returned status {response.status}")
                    
        except Exception as e:
            logger.error(f"Error scraping Bund.de: {e}")
        
        return tenders
    
    def _parse_tender_item(self, item) -> Optional[Dict]:
        """Parse a single tender item from Bund.de"""
        title_elem = item.select_one('h2, h3, .title, a')
        if not title_elem:
            return None
        
        title = self.clean_text(title_elem.get_text())
        if not title:
            return None
        
        # Extract other fields
        description = ""
        desc_elem = item.select_one('.description, .abstract, p')
        if desc_elem:
            description = self.clean_text(desc_elem.get_text())
        
        # Extract deadline
        deadline = datetime.now() + timedelta(days=30)  # Default
        deadline_elem = item.select_one('.deadline, .date, time')
        if deadline_elem:
            parsed = self.parse_german_date(deadline_elem.get_text())
            if parsed:
                deadline = parsed
        
        # Extract location
        location = "Deutschland"
        location_elem = item.select_one('.location, .ort')
        if location_elem:
            location = self.clean_text(location_elem.get_text()) or location
        
        # Get links - both detail and application
        detail_link = ""
        application_link = ""
        link_elem = item.select_one('a[href]')
        if link_elem:
            href = link_elem.get('href', '')
            if href.startswith('/'):
                detail_link = f"{self.BASE_URL}{href}"
            elif href.startswith('http'):
                detail_link = href
        
        # Look for specific application link
        apply_elem = item.select_one('a[href*="apply"], a[href*="bewerben"], a[href*="teilnahme"], .apply-link')
        if apply_elem:
            apply_href = apply_elem.get('href', '')
            if apply_href.startswith('/'):
                application_link = f"{self.BASE_URL}{apply_href}"
            elif apply_href.startswith('http'):
                application_link = apply_href
        
        # If no specific application link, use detail link as fallback
        if not application_link:
            application_link = detail_link
        
        # Categorize
        categories = self.categorize_tender(title, description)
        
        return {
            "title": title,
            "description": description or f"Ausschreibung: {title}",
            "budget": None,
            "deadline": deadline,
            "location": location,
            "project_type": "Construction/Services",
            "contracting_authority": "Bundesrepublik Deutschland",
            "participants": [],
            "contact_details": {},
            "tender_date": datetime.now(),
            "category": categories["category"],
            "building_typology": categories["building_typology"],
            "platform_source": "Bund.de",
            "platform_url": detail_link or self.BASE_URL,
            "application_url": application_link,
            "status": "New",
            "is_applied": False,
            "application_status": "Not Applied",
            "linkedin_connections": [],
            "scraped_at": datetime.utcnow(),
            "source_id": self.generate_tender_id(title, "bund.de", str(deadline)),
        }


class TEDEuropaScraper(TenderScraper):
    """Scraper for TED Europa - EU Public Procurement"""
    
    BASE_URL = "https://ted.europa.eu"
    API_URL = "https://ted.europa.eu/api/v3.0/notices/search"
    
    async def scrape(self, max_results: int = 50) -> List[Dict]:
        """Scrape German construction tenders from TED Europa"""
        tenders = []
        
        try:
            # TED has a public API
            params = {
                'q': 'TD=["works","services"] AND CY=[DE]',
                'pageSize': min(max_results, 100),
                'pageNum': 1,
                'sortField': 'PUBLICATION_DATE',
                'sortOrder': 'desc',
            }
            
            async with self.session.get(
                self.API_URL,
                params=params,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    notices = data.get('notices', []) if isinstance(data, dict) else []
                    
                    for notice in notices[:max_results]:
                        try:
                            tender = self._parse_notice(notice)
                            if tender:
                                tenders.append(tender)
                        except Exception as e:
                            logger.warning(f"Error parsing TED notice: {e}")
                            continue
                else:
                    logger.warning(f"TED API returned status {response.status}")
                    # Fallback to HTML scraping
                    tenders = await self._scrape_html(max_results)
                    
        except Exception as e:
            logger.error(f"Error scraping TED: {e}")
            # Fallback
            tenders = await self._scrape_html(max_results)
        
        return tenders
    
    async def _scrape_html(self, max_results: int) -> List[Dict]:
        """Fallback HTML scraping for TED"""
        tenders = []
        
        try:
            search_url = f"{self.BASE_URL}/de/search/result?q=CY%3D%5BDE%5D"
            
            async with self.session.get(
                search_url,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('.notice-item, .search-result, article')
                    
                    for item in items[:max_results]:
                        tender = self._parse_html_item(item)
                        if tender:
                            tenders.append(tender)
                            
        except Exception as e:
            logger.error(f"Error in TED HTML scraping: {e}")
        
        return tenders
    
    def _parse_notice(self, notice: Dict) -> Optional[Dict]:
        """Parse a TED API notice"""
        title = notice.get('title', {}).get('deu', '') or notice.get('title', {}).get('eng', '')
        if not title:
            return None
        
        description = notice.get('summary', {}).get('deu', '') or notice.get('summary', {}).get('eng', '')
        
        # Parse deadline
        deadline_str = notice.get('submissionDeadline', '')
        deadline = self.parse_german_date(deadline_str) or (datetime.now() + timedelta(days=30))
        
        # Get organization
        org = notice.get('buyerName', {}).get('deu', '') or 'EU Contracting Authority'
        
        # Location
        location = notice.get('placeOfPerformance', {}).get('name', 'Deutschland')
        
        # Budget
        budget = None
        if notice.get('estimatedValue'):
            budget = self.parse_budget(str(notice.get('estimatedValue')))
        
        categories = self.categorize_tender(title, description)
        
        # Generate detail and application URLs
        notice_id = notice.get('id', '')
        detail_url = f"{self.BASE_URL}/de/notice/{notice_id}" if notice_id else self.BASE_URL
        # TED application links typically redirect to eSender
        application_url = f"{self.BASE_URL}/de/notice/{notice_id}/submit" if notice_id else detail_url
        
        return {
            "title": title,
            "description": description or f"EU Ausschreibung: {title}",
            "budget": budget,
            "deadline": deadline,
            "location": location,
            "project_type": "EU Procurement",
            "contracting_authority": org,
            "participants": [],
            "contact_details": {},
            "tender_date": datetime.now(),
            "category": categories["category"],
            "building_typology": categories["building_typology"],
            "platform_source": "TED Europa",
            "platform_url": detail_url,
            "application_url": application_url,
            "status": "New",
            "is_applied": False,
            "application_status": "Not Applied",
            "linkedin_connections": [],
            "scraped_at": datetime.utcnow(),
            "source_id": self.generate_tender_id(title, "ted.europa", str(deadline)),
        }
    
    def _parse_html_item(self, item) -> Optional[Dict]:
        """Parse HTML item from TED search results"""
        title_elem = item.select_one('h2, h3, .title, a')
        if not title_elem:
            return None
        
        title = self.clean_text(title_elem.get_text())
        if not title:
            return None
        
        categories = self.categorize_tender(title, "")
        
        return {
            "title": title,
            "description": f"EU Tender: {title}",
            "budget": None,
            "deadline": datetime.now() + timedelta(days=30),
            "location": "Deutschland",
            "project_type": "EU Procurement",
            "contracting_authority": "EU Contracting Authority",
            "participants": [],
            "contact_details": {},
            "tender_date": datetime.now(),
            "category": categories["category"],
            "building_typology": categories["building_typology"],
            "platform_source": "TED Europa",
            "platform_url": self.BASE_URL,
            "status": "New",
            "is_applied": False,
            "application_status": "Not Applied",
            "linkedin_connections": [],
            "scraped_at": datetime.utcnow(),
            "source_id": self.generate_tender_id(title, "ted.europa", ""),
        }


class StateTenderScraper(TenderScraper):
    """Generic scraper for German state tender portals"""
    
    PORTALS = {
        # Bavaria
        "bayern": {
            "name": "Vergabe Bayern",
            "url": "https://www.auftraege.bayern.de",
            "region": "Bayern",
            "application_base": "https://www.auftraege.bayern.de/NetServer/PublicationControllerServlet"
        },
        # North Rhine-Westphalia
        "nrw": {
            "name": "e-Vergabe NRW", 
            "url": "https://www.evergabe.nrw.de",
            "region": "Nordrhein-Westfalen",
            "application_base": "https://www.evergabe.nrw.de/VMPSatellite/public/bekanntmachung"
        },
        # Berlin
        "berlin": {
            "name": "Vergabeplattform Berlin",
            "url": "https://www.berlin.de/vergabeplattform",
            "region": "Berlin",
            "application_base": "https://www.berlin.de/vergabeplattform/veroeffentlichungen/bekanntmachungen/"
        },
        # Hamburg
        "hamburg": {
            "name": "Hamburg Vergabe",
            "url": "https://fbhh-evergabe.web.hamburg.de/evergabe.bieter/eva/supplierportal/fhh/tabs/home",
            "region": "Hamburg",
            "application_base": "https://fbhh-evergabe.web.hamburg.de/evergabe.bieter/eva/supplierportal/fhh/subproject/search"
        },
        # Saxony
        "sachsen": {
            "name": "Sachsen Vergabe",
            "url": "https://www.sachsen-vergabe.de",
            "region": "Sachsen",
            "application_base": "https://www.sachsen-vergabe.de/vergabe/bekanntmachung/"
        },
        # Baden-Württemberg
        "bw": {
            "name": "Vergabe Baden-Württemberg",
            "url": "https://vergabe.landbw.de",
            "region": "Baden-Württemberg",
            "application_base": "https://vergabe.landbw.de/NetServer/PublicationControllerServlet"
        },
        # Hesse
        "hessen": {
            "name": "HAD Hessen",
            "url": "https://www.had.de",
            "region": "Hessen",
            "application_base": "https://www.had.de/NetServer/PublicationSearchControllerServlet"
        },
        # Lower Saxony
        "niedersachsen": {
            "name": "Vergabe Niedersachsen",
            "url": "https://vergabe.niedersachsen.de",
            "region": "Niedersachsen",
            "application_base": "https://vergabe.niedersachsen.de/NetServer/PublicationSearchControllerServlet"
        },
        # Bremen
        "bremen": {
            "name": "Vergabe Bremen",
            "url": "https://www.vergabe.bremen.de",
            "region": "Bremen",
            "application_base": "https://www.vergabe.bremen.de/NetServer/PublicationSearchControllerServlet"
        },
        # Brandenburg
        "brandenburg": {
            "name": "Vergabemarktplatz Brandenburg",
            "url": "https://vergabemarktplatz.brandenburg.de",
            "region": "Brandenburg",
            "application_base": "https://vergabemarktplatz.brandenburg.de/VMPSatellite/public/search"
        },
        # Rhineland-Palatinate
        "rlp": {
            "name": "Vergabe Rheinland-Pfalz",
            "url": "https://www.vergabe.rlp.de",
            "region": "Rheinland-Pfalz",
            "application_base": "https://www.vergabe.rlp.de/VMPSatellite/public/search"
        },
        # Saarland
        "saarland": {
            "name": "Vergabe Saarland",
            "url": "https://vergabe.saarland",
            "region": "Saarland",
            "application_base": "https://vergabe.saarland/NetServer/PublicationSearchControllerServlet"
        },
        # Saxony-Anhalt
        "sachsen_anhalt": {
            "name": "eVergabe Sachsen-Anhalt",
            "url": "https://www.evergabe.sachsen-anhalt.de",
            "region": "Sachsen-Anhalt",
            "application_base": "https://www.evergabe.sachsen-anhalt.de/NetServer/PublicationSearchControllerServlet"
        },
        # Schleswig-Holstein
        "sh": {
            "name": "e-Vergabe Schleswig-Holstein",
            "url": "https://www.e-vergabe-sh.de",
            "region": "Schleswig-Holstein",
            "application_base": "https://www.e-vergabe-sh.de/NetServer/PublicationSearchControllerServlet"
        },
        # Thuringia
        "thueringen": {
            "name": "Vergabe Thüringen",
            "url": "https://www.portal.thueringen.de",
            "region": "Thüringen",
            "application_base": "https://www.portal.thueringen.de/vergabe"
        }
    }
    
    # Additional national platforms
    NATIONAL_PORTALS = {
        "dtvp": {
            "name": "Deutsches Vergabeportal (DTVP)",
            "url": "https://www.dtvp.de",
            "region": "Deutschland",
            "application_base": "https://www.dtvp.de/Center"
        },
        "evergabe": {
            "name": "e-Vergabe",
            "url": "https://www.evergabe.de",
            "region": "Deutschland",
            "application_base": "https://www.evergabe.de/unterlagen"
        },
        "oeffentliche": {
            "name": "Öffentliche Vergabe",
            "url": "https://www.oeffentlichevergabe.de",
            "region": "Deutschland",
            "application_base": "https://www.oeffentlichevergabe.de/search"
        },
        "ausschreibungen_de": {
            "name": "Ausschreibungen Deutschland",
            "url": "https://ausschreibungen-deutschland.de",
            "region": "Deutschland",
            "application_base": "https://ausschreibungen-deutschland.de/search"
        }
    }
    
    # Hospital/Klinikum platforms
    HOSPITAL_PORTALS = {
        "charite": {
            "name": "Charité Vergabeplattform",
            "url": "https://vergabeplattform.charite.de",
            "region": "Berlin",
            "application_base": "https://vergabeplattform.charite.de"
        },
        "vivantes": {
            "name": "Vivantes",
            "url": "https://www.vivantes.de",
            "region": "Berlin",
            "application_base": "https://www.vivantes.de/unternehmen/ausschreibungen"
        },
        "uke": {
            "name": "UKE Hamburg (KFE)",
            "url": "https://www.uke.de/organisationsstruktur/tochtergesellschaften/kfe/ausschreibungen",
            "region": "Hamburg",
            "application_base": "https://www.uke.de/organisationsstruktur/tochtergesellschaften/kfe/ausschreibungen"
        }
    }
    
    # Switzerland platform
    SWISS_PORTALS = {
        "simap": {
            "name": "SIMAP.ch",
            "url": "https://www.simap.ch",
            "region": "Schweiz",
            "application_base": "https://www.simap.ch/shabforms/COMMON/search/searchresultListAction.do"
        }
    }
    
    async def scrape(self, state: str = None, max_results: int = 20) -> List[Dict]:
        """Scrape tenders from state portals"""
        tenders = []
        
        portals = {state: self.PORTALS[state]} if state and state in self.PORTALS else self.PORTALS
        
        for state_key, portal in portals.items():
            try:
                state_tenders = await self._scrape_portal(portal, max_results)
                tenders.extend(state_tenders)
            except Exception as e:
                logger.error(f"Error scraping {portal['name']}: {e}")
        
        return tenders
    
    async def _scrape_portal(self, portal: Dict, max_results: int) -> List[Dict]:
        """Scrape a single state portal"""
        tenders = []
        
        try:
            async with self.session.get(
                portal["url"],
                timeout=aiohttp.ClientTimeout(total=30),
                ssl=False  # Some state portals have certificate issues
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    # Generic selectors for tender listings
                    items = soup.select(
                        '.tender-item, .ausschreibung, .search-result, '
                        '.list-item, article, .entry, tr[class*="tender"]'
                    )
                    
                    for item in items[:max_results]:
                        tender = self._parse_item(item, portal)
                        if tender:
                            tenders.append(tender)
                else:
                    logger.warning(f"{portal['name']} returned status {response.status}")
                    
        except Exception as e:
            logger.warning(f"Could not scrape {portal['name']}: {e}")
        
        return tenders
    
    def _parse_item(self, item, portal: Dict) -> Optional[Dict]:
        """Parse a tender item from state portal"""
        title_elem = item.select_one('h2, h3, h4, .title, a, td:first-child')
        if not title_elem:
            return None
        
        title = self.clean_text(title_elem.get_text())
        if not title or len(title) < 10:
            return None
        
        # Get description
        description = ""
        desc_elem = item.select_one('.description, .abstract, p, td:nth-child(2)')
        if desc_elem:
            description = self.clean_text(desc_elem.get_text())
        
        # Categorize and check relevance
        categories = self.categorize_tender(title, description)
        
        # Skip non-relevant tenders (not construction/project related)
        if not categories.get("is_relevant", False):
            return None
        
        # Deadline
        deadline = datetime.now() + timedelta(days=30)
        deadline_elem = item.select_one('.deadline, .date, time, td:last-child')
        if deadline_elem:
            parsed = self.parse_german_date(deadline_elem.get_text())
            if parsed:
                deadline = parsed
        
        # Extract detail link
        detail_link = portal["url"]
        link_elem = item.select_one('a[href]')
        if link_elem:
            href = link_elem.get('href', '')
            if href.startswith('/'):
                detail_link = f"{portal['url']}{href}"
            elif href.startswith('http'):
                detail_link = href
        
        # Generate search-based application URL for this specific tender
        application_link = self.generate_application_url(title, portal["name"], detail_link)
        
        return {
            "title": title,
            "description": description or f"Ausschreibung {portal['region']}: {title}",
            "budget": None,
            "deadline": deadline,
            "location": portal["region"],
            "project_type": "State Tender",
            "contracting_authority": f"Land {portal['region']}",
            "participants": [],
            "contact_details": {},
            "tender_date": datetime.now(),
            "category": categories["category"],
            "building_typology": categories["building_typology"],
            "platform_source": portal["name"],
            "platform_url": detail_link,
            "application_url": application_link,
            "status": "New",
            "is_applied": False,
            "application_status": "Not Applied",
            "linkedin_connections": [],
            "scraped_at": datetime.utcnow(),
            "source_id": self.generate_tender_id(title, portal["name"], str(deadline)),
        }


async def scrape_all_portals(max_per_portal: int = 20) -> List[Dict]:
    """Scrape all available tender portals"""
    all_tenders = []
    
    # Scrape Bund.de
    try:
        async with BundDeScraper() as scraper:
            tenders = await scraper.scrape(max_per_portal)
            all_tenders.extend(tenders)
            logger.info(f"Scraped {len(tenders)} tenders from Bund.de")
    except Exception as e:
        logger.error(f"Bund.de scraping failed: {e}")
    
    # Scrape TED Europa
    try:
        async with TEDEuropaScraper() as scraper:
            tenders = await scraper.scrape(max_per_portal)
            all_tenders.extend(tenders)
            logger.info(f"Scraped {len(tenders)} tenders from TED Europa")
    except Exception as e:
        logger.error(f"TED scraping failed: {e}")
    
    # Scrape State Portals
    try:
        async with StateTenderScraper() as scraper:
            tenders = await scraper.scrape(max_results=max_per_portal)
            all_tenders.extend(tenders)
            logger.info(f"Scraped {len(tenders)} tenders from state portals")
    except Exception as e:
        logger.error(f"State portal scraping failed: {e}")
    
    # Deduplicate by source_id
    seen = set()
    unique_tenders = []
    for tender in all_tenders:
        source_id = tender.get('source_id', '')
        if source_id and source_id not in seen:
            seen.add(source_id)
            unique_tenders.append(tender)
        elif not source_id:
            unique_tenders.append(tender)
    
    logger.info(f"Total unique tenders scraped: {len(unique_tenders)}")
    return unique_tenders


if __name__ == "__main__":
    # Test scraping
    async def test():
        tenders = await scrape_all_portals(max_per_portal=10)
        for t in tenders[:5]:
            print(f"- {t['title'][:50]}... ({t['platform_source']})")
    
    asyncio.run(test())
