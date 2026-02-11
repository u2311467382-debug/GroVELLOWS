"""
Comprehensive Real Tender Scraper for German Construction Tender Platforms
Filters tenders based on GroVELLOWS company services
"""

import asyncio
import aiohttp
from bs4 import BeautifulSoup
from motor.motor_asyncio import AsyncIOMotorClient
import os
from datetime import datetime, timedelta
from urllib.parse import quote_plus, urljoin
import re
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Company service keywords for filtering
SERVICE_KEYWORDS = {
    'Integrierte Projektabwicklung': ['integrierte projektabwicklung', 'ipa', 'allianzvertrag', 'projektallianzen', 'partnerschaftsmodell'],
    'Integrated Project Management': ['integrated project management', 'integriertes projektmanagement', 'gesamtprojektmanagement'],
    'PMO': ['pmo', 'project management office', 'projektmanagementbüro', 'projektbüro'],
    'Wettbewerbsbegleitung': ['wettbewerbsbegleitung', 'wettbewerb', 'architekturwettbewerb', 'vergabewettbewerb', 'planungswettbewerb'],
    'Finanzcontrolling': ['finanzcontrolling', 'financial controlling', 'finanzsteuerung', 'budgetcontrolling'],
    'Agiles Projektmanagement': ['agil', 'agile', 'scrum', 'kanban', 'agiles projektmanagement'],
    'Projekt Coaching': ['projekt coaching', 'projektcoaching', 'bauherrenberatung', 'projektberatung'],
    'Nutzermanagement': ['nutzermanagement', 'nutzerbetreuung', 'nutzerkoordination', 'stakeholder'],
    'Krisenmanagement': ['krisenmanagement', 'konfliktmanagement', 'claim management', 'claimmanagement', 'mediation'],
    'Vertragsmanagement': ['vertragsmanagement', 'vertragssteuerung', 'nachtragsmanagement', 'vertragscontrolling'],
    'Risikomanagement': ['risikomanagement', 'risk management', 'risikoanalyse', 'risikobewertung'],
    'Lean Management': ['lean', 'lean construction', 'lean management', 'prozessoptimierung'],
    'Bauüberwachung': ['bauüberwachung', 'bauleitung', 'bauaufsicht', 'baubegleitung', 'objektüberwachung', 'bauoberleitung'],
    'Kostenmanagement': ['kostenmanagement', 'kostensteuerung', 'kostenkontrolle', 'kostenberechnung', 'kostenschätzung'],
    'Projektmanagement': ['projektmanagement', 'projektleitung', 'projektsteuerer'],
    'Projektsteuerung': ['projektsteuerung', 'projektsteuerer', 'projektsteuerungsleistung', 'aho'],
    'Projektcontrolling': ['projektcontrolling', 'projekt-controlling', 'projektcontroller', 'baucontrolling'],
    'Beschaffungsmanagement': ['beschaffung', 'procurement', 'vergabemanagement', 'ausschreibung']
}

# Building typology keywords
TYPOLOGY_KEYWORDS = {
    'Healthcare': ['krankenhaus', 'klinik', 'hospital', 'medizin', 'gesundheit', 'pflege', 'arzt', 'charité', 'vivantes'],
    'Education': ['schule', 'universität', 'hochschule', 'gymnasium', 'campus', 'bildung', 'kita', 'kindergarten'],
    'Residential': ['wohn', 'wohnung', 'mehrfamilienhaus', 'einfamilienhaus', 'siedlung', 'quartier'],
    'Commercial': ['büro', 'office', 'gewerbe', 'geschäftshaus', 'verwaltung', 'rathaus'],
    'Infrastructure': ['brücke', 'tunnel', 'straße', 'autobahn', 'schiene', 'bahn', 'kanal', 'kläranlage', 'u-bahn'],
    'Industrial': ['industrie', 'fabrik', 'werk', 'produktion', 'lager', 'logistik'],
    'Data Center': ['rechenzentrum', 'data center', 'datacenter', 'serverraum'],
    'Mixed-Use': ['mixed', 'gemischt', 'quartiersentwicklung'],
    'Sports': ['sport', 'stadion', 'arena', 'schwimmbad', 'turnhalle'],
    'Hospitality': ['hotel', 'gastro', 'restaurant']
}

class ComprehensiveScraper:
    def __init__(self, db):
        self.db = db
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8'
        }
    
    def categorize_tender(self, title: str, description: str = "") -> dict:
        """Categorize tender based on company services"""
        text = f"{title} {description}".lower()
        
        # Find matching category
        category = None
        for cat_name, keywords in SERVICE_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                category = cat_name
                break
        
        # Find building typology
        building_typology = None
        for typ_name, keywords in TYPOLOGY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                building_typology = typ_name
                break
        
        return {'category': category, 'building_typology': building_typology}
    
    def extract_budget(self, text: str) -> str:
        """Extract budget/cost from text"""
        # Look for Euro amounts
        patterns = [
            r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*(?:EUR|Euro|€))',
            r'(€\s*\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*Mio\.?\s*(?:EUR|Euro|€)?)',
            r'(Auftragswert[:\s]*\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*(?:EUR|Euro|€)?)',
            r'(geschätzter?\s*(?:Wert|Auftragswert)[:\s]*\d{1,3}(?:[.,]\d+)*\s*(?:EUR|Euro|€)?)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_deadline(self, text: str) -> datetime:
        """Extract deadline from text"""
        # German date patterns
        patterns = [
            r'(\d{1,2}\.\d{1,2}\.\d{4})',
            r'(\d{1,2}\.\d{1,2}\.\d{2})',
            r'(bis\s+\d{1,2}\.\d{1,2}\.\d{4})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1).replace('bis ', '')
                try:
                    if len(date_str.split('.')[-1]) == 2:
                        return datetime.strptime(date_str, '%d.%m.%y')
                    else:
                        return datetime.strptime(date_str, '%d.%m.%Y')
                except:
                    pass
        
        return datetime.utcnow() + timedelta(days=30)
    
    def is_relevant_tender(self, title: str, description: str = "") -> bool:
        """Check if tender matches company services"""
        text = f"{title} {description}".lower()
        
        # Must match at least one service category
        for keywords in SERVICE_KEYWORDS.values():
            if any(kw in text for kw in keywords):
                return True
        
        # Also check for general construction project management terms
        general_terms = ['projektsteuerung', 'baumanagement', 'generalplanung', 'objektplanung',
                        'fachplanung', 'technische ausrüstung', 'tragwerksplanung', 'bauphysik']
        if any(term in text for term in general_terms):
            return True
        
        return False
    
    def generate_application_url(self, title: str, platform_name: str, base_url: str) -> str:
        """Generate search URL for the specific tender"""
        encoded_title = quote_plus(title[:80])
        
        url_templates = {
            'Vergabe Bayern': f"https://www.auftraege.bayern.de/NetServer/PublicationSearchControllerServlet?searchText={encoded_title}",
            'e-Vergabe NRW': f"https://www.evergabe.nrw.de/VMPSatellite/public/search?q={encoded_title}",
            'Vergabeplattform Berlin': f"https://www.berlin.de/vergabeplattform/veroeffentlichungen/bekanntmachungen/?q={encoded_title}",
            'Hamburg Vergabe': f"https://fbhh-evergabe.web.hamburg.de/evergabe.bieter/eva/supplierportal/fhh/subproject/search?searchText={encoded_title}",
            'Sachsen Vergabe': f"https://www.sachsen-vergabe.de/vergabe/bekanntmachung/?search={encoded_title}",
            'Vergabe Baden-Württemberg': f"https://vergabe.landbw.de/NetServer/PublicationSearchControllerServlet?searchText={encoded_title}",
            'HAD Hessen': f"https://www.had.de/NetServer/PublicationSearchControllerServlet?searchText={encoded_title}",
            'Vergabe Niedersachsen': f"https://vergabe.niedersachsen.de/NetServer/PublicationSearchControllerServlet?searchText={encoded_title}",
            'Vergabe Bremen': f"https://www.vergabe.bremen.de/NetServer/PublicationSearchControllerServlet?searchText={encoded_title}",
            'Vergabemarktplatz Brandenburg': f"https://vergabemarktplatz.brandenburg.de/VMPSatellite/public/search?q={encoded_title}",
            'Vergabe Rheinland-Pfalz': f"https://www.vergabe.rlp.de/VMPSatellite/public/search?q={encoded_title}",
            'Vergabe Saarland': f"https://vergabe.saarland/NetServer/PublicationSearchControllerServlet?searchText={encoded_title}",
            'eVergabe Sachsen-Anhalt': f"https://www.evergabe.sachsen-anhalt.de/NetServer/PublicationSearchControllerServlet?searchText={encoded_title}",
            'e-Vergabe Schleswig-Holstein': f"https://www.e-vergabe-sh.de/NetServer/PublicationSearchControllerServlet?searchText={encoded_title}",
            'Vergabe Thüringen': f"https://www.portal.thueringen.de/vergabe?search={encoded_title}",
            'Bund.de': f"https://www.service.bund.de/Content/DE/Ausschreibungen/Suche/Ergebnis.html?searchText={encoded_title}",
            'TED Europa': f"https://ted.europa.eu/de/search/result?q={encoded_title}",
            'DTVP': f"https://www.dtvp.de/Center/common/project/search.do?search={encoded_title}",
            'Charité': f"https://vergabeplattform.charite.de/search?q={encoded_title}",
            'Vivantes': f"https://www.vivantes.de/unternehmen/ausschreibungen?search={encoded_title}",
            'UKE Hamburg': f"https://www.uke.de/organisationsstruktur/tochtergesellschaften/kfe/ausschreibungen?search={encoded_title}",
        }
        
        return url_templates.get(platform_name, base_url)
    
    async def scrape_bayern(self) -> list:
        """Scrape Vergabe Bayern"""
        tenders = []
        try:
            async with self.session.get(
                "https://www.auftraege.bayern.de",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    # Extract from ticker
                    tickers = soup.select('#webTicker li.itemTicker')
                    logger.info(f"Bayern: Found {len(tickers)} items in ticker")
                    
                    for ticker in tickers:
                        text = ticker.get_text(strip=True)
                        match = re.match(r'(.+?)\s*\(([^)]+)\)$', text)
                        if match:
                            title = match.group(1).strip()
                            authority = match.group(2).strip()
                            
                            if self.is_relevant_tender(title):
                                cat_info = self.categorize_tender(title)
                                budget = self.extract_budget(text)
                                
                                tenders.append({
                                    'title': title,
                                    'description': f"Ausschreibung: {title} - Auftraggeber: {authority}",
                                    'budget': budget,
                                    'deadline': self.extract_deadline(text),
                                    'location': 'Bayern',
                                    'project_type': 'Public Tender',
                                    'contracting_authority': authority,
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'Vergabe Bayern',
                                    'platform_url': 'https://www.auftraege.bayern.de',
                                })
        except Exception as e:
            logger.error(f"Error scraping Bayern: {e}")
        
        return tenders
    
    async def scrape_nrw(self) -> list:
        """Scrape e-Vergabe NRW"""
        tenders = []
        try:
            async with self.session.get(
                "https://www.evergabe.nrw.de/VMPSatellite/public/search",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    # Find tender listings
                    items = soup.select('table.searchResults tr, .publication-item, .tender-row')
                    logger.info(f"NRW: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('a, .title, td:first-child a')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 20 and self.is_relevant_tender(title):
                                # Try to get more details
                                desc_elem = item.select_one('.description, td:nth-child(2)')
                                description = desc_elem.get_text(strip=True) if desc_elem else ""
                                
                                full_text = f"{title} {description}"
                                cat_info = self.categorize_tender(title, description)
                                budget = self.extract_budget(full_text)
                                
                                tenders.append({
                                    'title': title,
                                    'description': description or f"Ausschreibung NRW: {title}",
                                    'budget': budget,
                                    'deadline': self.extract_deadline(full_text),
                                    'location': 'Nordrhein-Westfalen',
                                    'project_type': 'Public Tender',
                                    'contracting_authority': 'Land NRW',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'e-Vergabe NRW',
                                    'platform_url': 'https://www.evergabe.nrw.de',
                                })
        except Exception as e:
            logger.error(f"Error scraping NRW: {e}")
        
        return tenders
    
    async def scrape_berlin(self) -> list:
        """Scrape Vergabeplattform Berlin"""
        tenders = []
        try:
            async with self.session.get(
                "https://www.berlin.de/vergabeplattform/veroeffentlichungen/bekanntmachungen/",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    # Find tender listings
                    items = soup.select('article, .list-item, table tr, .modul-teaser')
                    logger.info(f"Berlin: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('h2 a, h3 a, .title a, a.link')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                desc_elem = item.select_one('p, .description, .text')
                                description = desc_elem.get_text(strip=True) if desc_elem else ""
                                
                                full_text = f"{title} {description}"
                                cat_info = self.categorize_tender(title, description)
                                budget = self.extract_budget(full_text)
                                
                                tenders.append({
                                    'title': title,
                                    'description': description or f"Ausschreibung Berlin: {title}",
                                    'budget': budget,
                                    'deadline': self.extract_deadline(full_text),
                                    'location': 'Berlin',
                                    'project_type': 'Public Tender',
                                    'contracting_authority': 'Land Berlin',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'Vergabeplattform Berlin',
                                    'platform_url': 'https://www.berlin.de/vergabeplattform',
                                })
        except Exception as e:
            logger.error(f"Error scraping Berlin: {e}")
        
        return tenders
    
    async def scrape_hamburg(self) -> list:
        """Scrape Hamburg Vergabe"""
        tenders = []
        try:
            async with self.session.get(
                "https://fbhh-evergabe.web.hamburg.de/evergabe.bieter/eva/supplierportal/fhh/tabs/home",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('table tr, .tender-item, .publication')
                    logger.info(f"Hamburg: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('a, .title, td a')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                cat_info = self.categorize_tender(title)
                                
                                tenders.append({
                                    'title': title,
                                    'description': f"Ausschreibung Hamburg: {title}",
                                    'budget': None,
                                    'deadline': datetime.utcnow() + timedelta(days=30),
                                    'location': 'Hamburg',
                                    'project_type': 'Public Tender',
                                    'contracting_authority': 'Freie und Hansestadt Hamburg',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'Hamburg Vergabe',
                                    'platform_url': 'https://fbhh-evergabe.web.hamburg.de',
                                })
        except Exception as e:
            logger.error(f"Error scraping Hamburg: {e}")
        
        return tenders
    
    async def scrape_bund(self) -> list:
        """Scrape Bund.de federal tenders"""
        tenders = []
        try:
            # Try the search results page
            async with self.session.get(
                "https://www.service.bund.de/Content/DE/Ausschreibungen/Suche/Formular.html",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('.searchResult, .result-item, article')
                    logger.info(f"Bund.de: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('h2 a, h3 a, .title a')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                desc_elem = item.select_one('.description, p')
                                description = desc_elem.get_text(strip=True) if desc_elem else ""
                                
                                full_text = f"{title} {description}"
                                cat_info = self.categorize_tender(title, description)
                                budget = self.extract_budget(full_text)
                                
                                tenders.append({
                                    'title': title,
                                    'description': description or f"Bundesausschreibung: {title}",
                                    'budget': budget,
                                    'deadline': self.extract_deadline(full_text),
                                    'location': 'Deutschland',
                                    'project_type': 'Federal Tender',
                                    'contracting_authority': 'Bundesrepublik Deutschland',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'Bund.de',
                                    'platform_url': 'https://www.service.bund.de',
                                })
        except Exception as e:
            logger.error(f"Error scraping Bund.de: {e}")
        
        return tenders
    
    async def scrape_ted(self) -> list:
        """Scrape TED Europa"""
        tenders = []
        try:
            # TED search for German construction tenders
            search_url = "https://ted.europa.eu/de/search/result?q=projektmanagement%20bau%20deutschland"
            async with self.session.get(
                search_url,
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('.notice-item, .search-result, article')
                    logger.info(f"TED: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('h2, h3, .title, a.notice-title')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                desc_elem = item.select_one('.description, .summary, p')
                                description = desc_elem.get_text(strip=True) if desc_elem else ""
                                
                                full_text = f"{title} {description}"
                                cat_info = self.categorize_tender(title, description)
                                budget = self.extract_budget(full_text)
                                
                                tenders.append({
                                    'title': title,
                                    'description': description or f"EU Ausschreibung: {title}",
                                    'budget': budget,
                                    'deadline': self.extract_deadline(full_text),
                                    'location': 'EU/Deutschland',
                                    'project_type': 'EU Tender',
                                    'contracting_authority': 'EU Contracting Authority',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'TED Europa',
                                    'platform_url': 'https://ted.europa.eu',
                                })
        except Exception as e:
            logger.error(f"Error scraping TED: {e}")
        
        return tenders
    
    async def scrape_hospital_charite(self) -> list:
        """Scrape Charité hospital tenders"""
        tenders = []
        try:
            async with self.session.get(
                "https://vergabeplattform.charite.de",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('table tr, .tender-item, article')
                    logger.info(f"Charité: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('a, .title')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                cat_info = self.categorize_tender(title)
                                
                                tenders.append({
                                    'title': title,
                                    'description': f"Charité Ausschreibung: {title}",
                                    'budget': None,
                                    'deadline': datetime.utcnow() + timedelta(days=30),
                                    'location': 'Berlin',
                                    'project_type': 'Hospital Tender',
                                    'contracting_authority': 'Charité - Universitätsmedizin Berlin',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': 'Healthcare',
                                    'platform_source': 'Charité',
                                    'platform_url': 'https://vergabeplattform.charite.de',
                                })
        except Exception as e:
            logger.error(f"Error scraping Charité: {e}")
        
        return tenders
    
    async def scrape_simap_switzerland(self) -> list:
        """Scrape simap.ch Switzerland tender platform using their archive"""
        tenders = []
        try:
            # Search for construction-related tenders in archive
            search_terms = ['projektsteuerung', 'projektmanagement', 'bauleitung', 'baumanagement']
            
            for term in search_terms:
                url = f"https://archiv.simap.ch/shabforms/COMMON/search/searchresultDetail.jsf?searchText={term}"
                
                async with self.session.get(
                    url,
                    headers=self.headers,
                    ssl=False,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        soup = BeautifulSoup(html, 'lxml')
                        
                        # Find result items
                        items = soup.select('table.resultTable tr, .searchResultItem, .tender-row, tr[data-ri]')
                        logger.info(f"simap.ch ({term}): Found {len(items)} items")
                        
                        for item in items:
                            title_elem = item.select_one('a, .title, td:first-child a, td a')
                            if title_elem:
                                title = title_elem.get_text(strip=True)
                                if len(title) > 15 and self.is_relevant_tender(title):
                                    # Get link
                                    link = title_elem.get('href', '')
                                    if link and not link.startswith('http'):
                                        link = f"https://archiv.simap.ch{link}"
                                    
                                    cat_info = self.categorize_tender(title)
                                    
                                    tenders.append({
                                        'title': title,
                                        'description': f"Schweizer Ausschreibung: {title}",
                                        'budget': None,
                                        'deadline': datetime.utcnow() + timedelta(days=30),
                                        'location': 'Schweiz',
                                        'project_type': 'Public Tender',
                                        'contracting_authority': 'Schweizer Öffentlicher Auftraggeber',
                                        'category': cat_info['category'] or 'Projektmanagement',
                                        'building_typology': cat_info['building_typology'],
                                        'platform_source': 'simap.ch (Schweiz)',
                                        'platform_url': 'https://www.simap.ch',
                                        'country': 'Switzerland',
                                    })
                                    
                await asyncio.sleep(1)  # Rate limiting
                
        except Exception as e:
            logger.error(f"Error scraping simap.ch: {e}")
        
        return tenders
    
    async def scrape_niedersachsen(self) -> list:
        """Scrape Niedersachsen (Lower Saxony) tender platform"""
        tenders = []
        try:
            async with self.session.get(
                "https://vergabe.niedersachsen.de/NetServer/PublicationSearchControllerServlet",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('table tr, .publication-item, article')
                    logger.info(f"Niedersachsen: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('a, .title')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                cat_info = self.categorize_tender(title)
                                
                                tenders.append({
                                    'title': title,
                                    'description': f"Ausschreibung Niedersachsen: {title}",
                                    'budget': None,
                                    'deadline': datetime.utcnow() + timedelta(days=30),
                                    'location': 'Niedersachsen',
                                    'project_type': 'Public Tender',
                                    'contracting_authority': 'Land Niedersachsen',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'Vergabe Niedersachsen',
                                    'platform_url': 'https://vergabe.niedersachsen.de',
                                    'country': 'Germany',
                                })
        except Exception as e:
            logger.error(f"Error scraping Niedersachsen: {e}")
        
        return tenders
    
    async def scrape_hessen(self) -> list:
        """Scrape Hessen (HAD) tender platform"""
        tenders = []
        try:
            async with self.session.get(
                "https://www.had.de/NetServer/PublicationSearchControllerServlet",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('table tr, .publication-item')
                    logger.info(f"Hessen HAD: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('a, .title')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                cat_info = self.categorize_tender(title)
                                
                                tenders.append({
                                    'title': title,
                                    'description': f"Ausschreibung Hessen: {title}",
                                    'budget': None,
                                    'deadline': datetime.utcnow() + timedelta(days=30),
                                    'location': 'Hessen',
                                    'project_type': 'Public Tender',
                                    'contracting_authority': 'Land Hessen',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'HAD Hessen',
                                    'platform_url': 'https://www.had.de',
                                    'country': 'Germany',
                                })
        except Exception as e:
            logger.error(f"Error scraping Hessen: {e}")
        
        return tenders
    
    async def scrape_brandenburg(self) -> list:
        """Scrape Brandenburg tender platform"""
        tenders = []
        try:
            async with self.session.get(
                "https://vergabemarktplatz.brandenburg.de/VMPSatellite/public/search",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('table tr, .publication-item, .searchResult')
                    logger.info(f"Brandenburg: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('a, .title')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                cat_info = self.categorize_tender(title)
                                
                                tenders.append({
                                    'title': title,
                                    'description': f"Ausschreibung Brandenburg: {title}",
                                    'budget': None,
                                    'deadline': datetime.utcnow() + timedelta(days=30),
                                    'location': 'Brandenburg',
                                    'project_type': 'Public Tender',
                                    'contracting_authority': 'Land Brandenburg',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'Vergabemarktplatz Brandenburg',
                                    'platform_url': 'https://vergabemarktplatz.brandenburg.de',
                                    'country': 'Germany',
                                })
        except Exception as e:
            logger.error(f"Error scraping Brandenburg: {e}")
        
        return tenders
    
    async def scrape_saarland(self) -> list:
        """Scrape Saarland tender platform"""
        tenders = []
        try:
            async with self.session.get(
                "https://vergabe.saarland/NetServer/PublicationSearchControllerServlet",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('table tr, .publication-item')
                    logger.info(f"Saarland: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('a, .title')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                cat_info = self.categorize_tender(title)
                                
                                tenders.append({
                                    'title': title,
                                    'description': f"Ausschreibung Saarland: {title}",
                                    'budget': None,
                                    'deadline': datetime.utcnow() + timedelta(days=30),
                                    'location': 'Saarland',
                                    'project_type': 'Public Tender',
                                    'contracting_authority': 'Land Saarland',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'Vergabe Saarland',
                                    'platform_url': 'https://vergabe.saarland',
                                    'country': 'Germany',
                                })
        except Exception as e:
            logger.error(f"Error scraping Saarland: {e}")
        
        return tenders
    
    async def scrape_sachsen_anhalt(self) -> list:
        """Scrape Sachsen-Anhalt tender platform"""
        tenders = []
        try:
            async with self.session.get(
                "https://www.evergabe.sachsen-anhalt.de/NetServer/PublicationSearchControllerServlet",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('table tr, .publication-item')
                    logger.info(f"Sachsen-Anhalt: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('a, .title')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                cat_info = self.categorize_tender(title)
                                
                                tenders.append({
                                    'title': title,
                                    'description': f"Ausschreibung Sachsen-Anhalt: {title}",
                                    'budget': None,
                                    'deadline': datetime.utcnow() + timedelta(days=30),
                                    'location': 'Sachsen-Anhalt',
                                    'project_type': 'Public Tender',
                                    'contracting_authority': 'Land Sachsen-Anhalt',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'eVergabe Sachsen-Anhalt',
                                    'platform_url': 'https://www.evergabe.sachsen-anhalt.de',
                                    'country': 'Germany',
                                })
        except Exception as e:
            logger.error(f"Error scraping Sachsen-Anhalt: {e}")
        
        return tenders
    
    async def scrape_schleswig_holstein(self) -> list:
        """Scrape Schleswig-Holstein tender platform"""
        tenders = []
        try:
            async with self.session.get(
                "https://www.e-vergabe-sh.de/NetServer/PublicationSearchControllerServlet",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('table tr, .publication-item')
                    logger.info(f"Schleswig-Holstein: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('a, .title')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                cat_info = self.categorize_tender(title)
                                
                                tenders.append({
                                    'title': title,
                                    'description': f"Ausschreibung Schleswig-Holstein: {title}",
                                    'budget': None,
                                    'deadline': datetime.utcnow() + timedelta(days=30),
                                    'location': 'Schleswig-Holstein',
                                    'project_type': 'Public Tender',
                                    'contracting_authority': 'Land Schleswig-Holstein',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'e-Vergabe Schleswig-Holstein',
                                    'platform_url': 'https://www.e-vergabe-sh.de',
                                    'country': 'Germany',
                                })
        except Exception as e:
            logger.error(f"Error scraping Schleswig-Holstein: {e}")
        
        return tenders
    
    async def scrape_rheinland_pfalz(self) -> list:
        """Scrape Rheinland-Pfalz tender platform"""
        tenders = []
        try:
            async with self.session.get(
                "https://www.vergabe.rlp.de/VMPSatellite/public/search",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('table tr, .publication-item, .searchResult')
                    logger.info(f"Rheinland-Pfalz: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('a, .title')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                cat_info = self.categorize_tender(title)
                                
                                tenders.append({
                                    'title': title,
                                    'description': f"Ausschreibung Rheinland-Pfalz: {title}",
                                    'budget': None,
                                    'deadline': datetime.utcnow() + timedelta(days=30),
                                    'location': 'Rheinland-Pfalz',
                                    'project_type': 'Public Tender',
                                    'contracting_authority': 'Land Rheinland-Pfalz',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'Vergabe Rheinland-Pfalz',
                                    'platform_url': 'https://www.vergabe.rlp.de',
                                    'country': 'Germany',
                                })
        except Exception as e:
            logger.error(f"Error scraping Rheinland-Pfalz: {e}")
        
        return tenders
    
    async def scrape_baden_wuerttemberg(self) -> list:
        """Scrape Baden-Württemberg tender platform"""
        tenders = []
        try:
            async with self.session.get(
                "https://vergabe.landbw.de/NetServer/PublicationSearchControllerServlet",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('table tr, .publication-item')
                    logger.info(f"Baden-Württemberg: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('a, .title')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                cat_info = self.categorize_tender(title)
                                
                                tenders.append({
                                    'title': title,
                                    'description': f"Ausschreibung Baden-Württemberg: {title}",
                                    'budget': None,
                                    'deadline': datetime.utcnow() + timedelta(days=30),
                                    'location': 'Baden-Württemberg',
                                    'project_type': 'Public Tender',
                                    'contracting_authority': 'Land Baden-Württemberg',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'Vergabe Baden-Württemberg',
                                    'platform_url': 'https://vergabe.landbw.de',
                                    'country': 'Germany',
                                })
        except Exception as e:
            logger.error(f"Error scraping Baden-Württemberg: {e}")
        
        return tenders
    
    async def scrape_sachsen(self) -> list:
        """Scrape Sachsen tender platform"""
        tenders = []
        try:
            async with self.session.get(
                "https://www.sachsen-vergabe.de/vergabe/bekanntmachung/",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('table tr, .publication-item, article')
                    logger.info(f"Sachsen: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('a, .title')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                cat_info = self.categorize_tender(title)
                                
                                tenders.append({
                                    'title': title,
                                    'description': f"Ausschreibung Sachsen: {title}",
                                    'budget': None,
                                    'deadline': datetime.utcnow() + timedelta(days=30),
                                    'location': 'Sachsen',
                                    'project_type': 'Public Tender',
                                    'contracting_authority': 'Freistaat Sachsen',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'Sachsen Vergabe',
                                    'platform_url': 'https://www.sachsen-vergabe.de',
                                    'country': 'Germany',
                                })
        except Exception as e:
            logger.error(f"Error scraping Sachsen: {e}")
        
        return tenders
    
    async def scrape_bremen(self) -> list:
        """Scrape Bremen tender platform"""
        tenders = []
        try:
            async with self.session.get(
                "https://www.vergabe.bremen.de/NetServer/PublicationSearchControllerServlet",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('table tr, .publication-item')
                    logger.info(f"Bremen: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('a, .title')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                cat_info = self.categorize_tender(title)
                                
                                tenders.append({
                                    'title': title,
                                    'description': f"Ausschreibung Bremen: {title}",
                                    'budget': None,
                                    'deadline': datetime.utcnow() + timedelta(days=30),
                                    'location': 'Bremen',
                                    'project_type': 'Public Tender',
                                    'contracting_authority': 'Freie Hansestadt Bremen',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'Vergabe Bremen',
                                    'platform_url': 'https://www.vergabe.bremen.de',
                                    'country': 'Germany',
                                })
        except Exception as e:
            logger.error(f"Error scraping Bremen: {e}")
        
        return tenders
    
    async def scrape_thuringia(self) -> list:
        """Scrape Thuringia tender platform"""
        tenders = []
        try:
            async with self.session.get(
                "https://www.thueringen.de/vergabe/",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('table tr, .publication-item, article')
                    logger.info(f"Thüringen: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('a, .title')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                cat_info = self.categorize_tender(title)
                                
                                tenders.append({
                                    'title': title,
                                    'description': f"Ausschreibung Thüringen: {title}",
                                    'budget': None,
                                    'deadline': datetime.utcnow() + timedelta(days=30),
                                    'location': 'Thüringen',
                                    'project_type': 'Public Tender',
                                    'contracting_authority': 'Freistaat Thüringen',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'Vergabe Thüringen',
                                    'platform_url': 'https://www.thueringen.de/vergabe',
                                    'country': 'Germany',
                                })
        except Exception as e:
            logger.error(f"Error scraping Thüringen: {e}")
        
        return tenders
    
    async def scrape_ausschreibungen_deutschland(self) -> list:
        """Scrape ausschreibungen-deutschland.de"""
        tenders = []
        try:
            async with self.session.get(
                "https://ausschreibungen-deutschland.de/",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('.tender-item, article, .publication, table tr')
                    logger.info(f"Ausschreibungen-Deutschland.de: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('a, h2, .title')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                cat_info = self.categorize_tender(title)
                                
                                tenders.append({
                                    'title': title,
                                    'description': f"Ausschreibung: {title}",
                                    'budget': None,
                                    'deadline': datetime.utcnow() + timedelta(days=30),
                                    'location': 'Deutschland',
                                    'project_type': 'Public Tender',
                                    'contracting_authority': 'Öffentlicher Auftraggeber',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'Ausschreibungen Deutschland',
                                    'platform_url': 'https://ausschreibungen-deutschland.de/',
                                    'country': 'Germany',
                                })
        except Exception as e:
            logger.error(f"Error scraping Ausschreibungen-Deutschland.de: {e}")
        
        return tenders
    
    async def scrape_evergabe_online(self) -> list:
        """Scrape e-Vergabe Online (Federal)"""
        tenders = []
        try:
            async with self.session.get(
                "https://www.evergabe-online.de/",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('.tender-item, article, .publication, table tr')
                    logger.info(f"e-Vergabe Online: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('a, h2, .title')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                cat_info = self.categorize_tender(title)
                                
                                tenders.append({
                                    'title': title,
                                    'description': f"Bundesausschreibung: {title}",
                                    'budget': None,
                                    'deadline': datetime.utcnow() + timedelta(days=30),
                                    'location': 'Deutschland',
                                    'project_type': 'Federal Tender',
                                    'contracting_authority': 'Bundesauftraggeber',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'e-Vergabe Online',
                                    'platform_url': 'https://www.evergabe-online.de',
                                    'country': 'Germany',
                                })
        except Exception as e:
            logger.error(f"Error scraping e-Vergabe Online: {e}")
        
        return tenders
    
    async def scrape_dtvp(self) -> list:
        """Scrape Deutsches Vergabeportal (DTVP)"""
        tenders = []
        try:
            async with self.session.get(
                "https://www.dtvp.de/Center/common/project/search.do",
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    items = soup.select('.searchResult, article, .tender-item, table tr')
                    logger.info(f"DTVP: Found {len(items)} items")
                    
                    for item in items:
                        title_elem = item.select_one('a, h2, .title')
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            if len(title) > 15 and self.is_relevant_tender(title):
                                cat_info = self.categorize_tender(title)
                                
                                tenders.append({
                                    'title': title,
                                    'description': f"DTVP Ausschreibung: {title}",
                                    'budget': None,
                                    'deadline': datetime.utcnow() + timedelta(days=30),
                                    'location': 'Deutschland',
                                    'project_type': 'Public Tender',
                                    'contracting_authority': 'Öffentlicher Auftraggeber',
                                    'category': cat_info['category'] or 'Projektmanagement',
                                    'building_typology': cat_info['building_typology'],
                                    'platform_source': 'DTVP',
                                    'platform_url': 'https://www.dtvp.de',
                                    'country': 'Germany',
                                })
        except Exception as e:
            logger.error(f"Error scraping DTVP: {e}")
        
        return tenders
    
    async def scrape_all(self) -> int:
        """Scrape all platforms and save to database"""
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            all_tenders = []
            
            # Scrape all platforms
            logger.info("Starting comprehensive scrape of all platforms...")
            
            bayern_tenders = await self.scrape_bayern()
            all_tenders.extend(bayern_tenders)
            logger.info(f"Bayern: {len(bayern_tenders)} relevant tenders")
            
            nrw_tenders = await self.scrape_nrw()
            all_tenders.extend(nrw_tenders)
            logger.info(f"NRW: {len(nrw_tenders)} relevant tenders")
            
            berlin_tenders = await self.scrape_berlin()
            all_tenders.extend(berlin_tenders)
            logger.info(f"Berlin: {len(berlin_tenders)} relevant tenders")
            
            hamburg_tenders = await self.scrape_hamburg()
            all_tenders.extend(hamburg_tenders)
            logger.info(f"Hamburg: {len(hamburg_tenders)} relevant tenders")
            
            bund_tenders = await self.scrape_bund()
            all_tenders.extend(bund_tenders)
            logger.info(f"Bund.de: {len(bund_tenders)} relevant tenders")
            
            ted_tenders = await self.scrape_ted()
            all_tenders.extend(ted_tenders)
            logger.info(f"TED Europa: {len(ted_tenders)} relevant tenders")
            
            charite_tenders = await self.scrape_hospital_charite()
            all_tenders.extend(charite_tenders)
            logger.info(f"Charité: {len(charite_tenders)} relevant tenders")
            
            # Save to database
            added_count = 0
            for tender in all_tenders:
                # Check for duplicates
                existing = await self.db.tenders.find_one({'title': tender['title']})
                if not existing:
                    # Add common fields
                    tender['application_url'] = self.generate_application_url(
                        tender['title'], 
                        tender['platform_source'],
                        tender['platform_url']
                    )
                    tender['participants'] = []
                    tender['contact_details'] = {}
                    tender['tender_date'] = datetime.utcnow()
                    tender['status'] = 'New'
                    tender['is_applied'] = False
                    tender['application_status'] = 'Not Applied'
                    tender['linkedin_connections'] = []
                    tender['scraped_at'] = datetime.utcnow()
                    tender['created_at'] = datetime.utcnow()
                    tender['updated_at'] = datetime.utcnow()
                    tender['source_id'] = f"{tender['platform_source']}_{hash(tender['title'])}"
                    
                    await self.db.tenders.insert_one(tender)
                    added_count += 1
                    logger.info(f"Added: {tender['title'][:50]}...")
            
            logger.info(f"\n✅ Total new tenders added: {added_count}")
            return added_count


async def main():
    """Run the comprehensive scraper"""
    from dotenv import load_dotenv
    load_dotenv()
    
    client = AsyncIOMotorClient(os.environ.get('MONGO_URL', 'mongodb://localhost:27017'))
    db = client[os.environ.get('DB_NAME', 'grovellows')]
    
    scraper = ComprehensiveScraper(db)
    added = await scraper.scrape_all()
    
    total = await db.tenders.count_documents({})
    print(f"\n📊 Total tenders in database: {total}")
    
    # Show category distribution
    print("\n=== Category Distribution ===")
    async for doc in db.tenders.aggregate([
        {'$group': {'_id': '$category', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]):
        print(f"  {doc['_id']}: {doc['count']}")
    
    # Show platform distribution
    print("\n=== Platform Distribution ===")
    async for doc in db.tenders.aggregate([
        {'$group': {'_id': '$platform_source', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]):
        print(f"  {doc['_id']}: {doc['count']}")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
