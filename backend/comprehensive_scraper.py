"""
Comprehensive Real Tender Scraper for German & Swiss Construction Tender Platforms
Filters tenders based on GroVELLOWS company services
Includes deduplication logic to show each tender only once with best access link
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
import hashlib
from difflib import SequenceMatcher

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
    'Projektsteuerung': ['projektsteuerung', 'projektsteuerer', 'projektsteuerungsleistung', 'projektsteuerungsleistungen', 'aho'],
    'Projektcontrolling': ['projektcontrolling', 'projekt-controlling', 'projektcontroller', 'baucontrolling'],
    'Beschaffungsmanagement': ['beschaffung', 'procurement', 'vergabemanagement', 'ausschreibung'],
    # New categories for construction industry
    'Bauwesen': ['bauwesen', 'bauleistung', 'bauleistungen', 'bauarbeiten', 'bauauftrag', 'bauwerk', 'bauvorhaben', 'bauprojekt'],
    'Building Construction': ['building construction', 'hochbau', 'tiefbau', 'rohbau', 'ausbau', 'neubau', 'umbau', 'anbau', 'erweiterungsbau'],
}

# Building typology keywords
TYPOLOGY_KEYWORDS = {
    'Healthcare': ['krankenhaus', 'klinik', 'hospital', 'medizin', 'gesundheit', 'pflege', 'arzt', 'charité', 'vivantes', 'asklepios', 'helios', 'sana'],
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

# Platform priority for deduplication (higher = better source)
PLATFORM_PRIORITY = {
    'Bund.de': 100,
    'TED Europa': 95,
    'DTVP': 90,
    'e-Vergabe Online': 88,
    'Öffentliche Vergabe': 85,
    'Vergabe Bayern': 80,
    'e-Vergabe NRW': 80,
    'Vergabeplattform Berlin': 80,
    'Berlin Procurement Cooperation': 78,
    'Hamburg Vergabe': 80,
    'Vergabe Baden-Württemberg': 80,
    'HAD Hessen': 80,
    'Vergabe Niedersachsen': 80,
    'Vergabemarktplatz Brandenburg': 80,
    'Vergabe Rheinland-Pfalz': 80,
    'Vergabe Saarland': 80,
    'eVergabe Sachsen-Anhalt': 80,
    'e-Vergabe Schleswig-Holstein': 80,
    'Sachsen Vergabe': 80,
    'Vergabe Bremen': 80,
    'Vergabe Thüringen': 80,
    'Ausschreibungen Deutschland': 75,
    'ibau': 70,
    'eVergabe.de': 75,
    'vergabe24': 73,
    'DTAD': 72,
    'Tender Impulse': 70,
    'CWC Tenders': 68,
    'BiddingSource': 68,
    'A24 Sales Cloud': 68,
    'AUMASS': 70,
    'LZBW': 75,
    'D&E BauNetzwerk': 72,
    'Global Tenders Germany': 65,
    'Charité': 85,
    'Vivantes': 85,
    'UKE Hamburg': 85,
    'Fraunhofer': 85,
    'Ammerland Klinik': 80,
    'Pfalzklinikum': 80,
    'KMG Kliniken': 80,
    'Klinikverbund Südwest': 80,
    'Sana Kliniken': 80,
    'Helios Kliniken': 80,
    'Asklepios Kliniken': 80,
    'simap.ch (Schweiz)': 90,
}

class ComprehensiveScraper:
    # Minimum publication date - only tenders published on or after this date will be saved
    MIN_PUBLICATION_DATE = datetime(2025, 1, 1)
    
    # Number of pages to scrape per platform
    PAGES_TO_SCRAPE = 5
    
    def __init__(self, db):
        self.db = db
        self.session = None
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'de-DE,de;q=0.9,en;q=0.8'
        }
        self.seen_tenders = {}  # For deduplication
    
    def is_tender_in_date_range(self, publication_date: datetime) -> bool:
        """Check if tender publication date is >= MIN_PUBLICATION_DATE (Jan 1, 2025)"""
        if publication_date is None:
            # If no date available, assume it's recent and include it
            return True
        return publication_date >= self.MIN_PUBLICATION_DATE
    
    def extract_publication_date(self, text: str) -> datetime:
        """Extract publication date from text. Returns None if not found."""
        # Common date patterns in German tender portals
        patterns = [
            r'(\d{1,2}\.\d{1,2}\.20[2-9]\d)',  # DD.MM.YYYY format with year 2020+
            r'(\d{1,2}\.\d{1,2}\.20[2-9]\d)',  # Similar
            r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})',  # YYYY-MM-DD format
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                try:
                    if '.' in date_str:
                        return datetime.strptime(date_str, '%d.%m.%Y')
                    elif '-' in date_str:
                        return datetime.strptime(date_str, '%Y-%m-%d')
                    elif '/' in date_str:
                        return datetime.strptime(date_str, '%Y/%m/%d')
                except:
                    pass
        
        return None
    
    def normalize_title(self, title: str) -> str:
        """Normalize title for deduplication"""
        # Remove special characters, lowercase, remove extra spaces
        normalized = re.sub(r'[^\w\s]', '', title.lower())
        normalized = ' '.join(normalized.split())
        return normalized
    
    def get_title_hash(self, title: str) -> str:
        """Create hash of normalized title for fast lookup"""
        normalized = self.normalize_title(title)
        return hashlib.md5(normalized.encode()).hexdigest()[:16]
    
    def is_similar_title(self, title1: str, title2: str, threshold: float = 0.85) -> bool:
        """Check if two titles are similar enough to be considered duplicates"""
        norm1 = self.normalize_title(title1)
        norm2 = self.normalize_title(title2)
        return SequenceMatcher(None, norm1, norm2).ratio() >= threshold
    
    def categorize_tender(self, title: str, description: str = "") -> dict:
        """Categorize tender based on company services"""
        text = f"{title} {description}".lower()
        
        category = None
        for cat_name, keywords in SERVICE_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                category = cat_name
                break
        
        building_typology = None
        for typ_name, keywords in TYPOLOGY_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                building_typology = typ_name
                break
        
        return {'category': category, 'building_typology': building_typology}
    
    def extract_budget(self, text: str) -> str:
        """Extract budget/cost from text"""
        patterns = [
            r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*(?:EUR|Euro|€))',
            r'(€\s*\d{1,3}(?:\.\d{3})*(?:,\d{2})?)',
            r'(\d{1,3}(?:\.\d{3})*(?:,\d{2})?\s*Mio\.?\s*(?:EUR|Euro|€)?)',
            r'(CHF\s*\d{1,3}(?:[\',]\d{3})*(?:\.\d{2})?)',
            r'(\d{1,3}(?:[\',]\d{3})*(?:\.\d{2})?\s*CHF)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def extract_deadline(self, text: str) -> datetime:
        """Extract deadline from text"""
        patterns = [
            r'(\d{1,2}\.\d{1,2}\.\d{4})',
            r'(\d{1,2}\.\d{1,2}\.\d{2})',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                date_str = match.group(1)
                try:
                    if len(date_str.split('.')[-1]) == 2:
                        return datetime.strptime(date_str, '%d.%m.%y')
                    else:
                        return datetime.strptime(date_str, '%d.%m.%Y')
                except:
                    pass
        
        return datetime.utcnow() + timedelta(days=30)
    
    def is_relevant_tender(self, title: str, description: str = "") -> bool:
        """Check if tender matches company services - more permissive to capture more tenders"""
        text = f"{title} {description}".lower()
        
        # Check service keywords
        for keywords in SERVICE_KEYWORDS.values():
            if any(kw in text for kw in keywords):
                return True
        
        # General construction and public tender terms - expanded list
        general_terms = [
            'projektsteuerung', 'projektsteuerungsleistung', 'projektsteuerungsleistungen',
            'baumanagement', 'generalplanung', 'objektplanung',
            'fachplanung', 'technische ausrüstung', 'tragwerksplanung', 'bauphysik',
            'architekten', 'ingenieur', 'planung', 'bau', 'neubau', 'sanierung',
            'modernisierung', 'erweiterung', 'umbau', 'hochbau', 'tiefbau',
            'dienstleistung', 'beratung', 'consulting', 'management',
            # Bauwesen and Building Construction terms
            'bauwesen', 'bauleistung', 'bauleistungen', 'bauarbeiten', 'bauauftrag',
            'bauwerk', 'bauvorhaben', 'bauprojekt', 'building construction',
            'rohbau', 'ausbau', 'anbau', 'erweiterungsbau',
            # Additional broad terms to capture more relevant tenders
            'ausschreibung', 'vergabe', 'auftrag', 'lieferung', 'leistung',
            'deutschland', 'öffentlich', 'beschaffung', 'rahmenvertrag',
            'infrastruktur', 'gebäude',
            'krankenhaus', 'klinik', 'schule', 'universität', 'rathaus',
            'renovierung', 'instandsetzung', 'wartung', 'installation',
            'elektro', 'heizung', 'lüftung', 'sanitär', 'dach', 'fassade',
            'architekturbüro', 'planungsbüro', 'ingenieurbüro',
            # Messe/Exhibition specific
            'messe', 'messebau', 'messegelände', 'exhibition', 'kongresszentrum'
        ]
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
            'Vergabe Thüringen': f"https://www.thueringen.de/vergabe?search={encoded_title}",
            'Bund.de': f"https://www.service.bund.de/Content/DE/Ausschreibungen/Suche/Ergebnis.html?searchText={encoded_title}",
            'TED Europa': f"https://ted.europa.eu/de/search/result?q={encoded_title}",
            'DTVP': f"https://www.dtvp.de/Center/common/project/search.do?search={encoded_title}",
            'Öffentliche Vergabe': f"https://www.oeffentlichevergabe.de/search?q={encoded_title}",
            'Ausschreibungen Deutschland': f"https://ausschreibungen-deutschland.de/?search={encoded_title}",
            'e-Vergabe Online': f"https://www.evergabe-online.de/search?q={encoded_title}",
            'ibau': f"https://www.ibau.de/ausschreibungen/?q={encoded_title}",
            'Charité': f"https://vergabeplattform.charite.de/search?q={encoded_title}",
            'Vivantes': f"https://www.vivantes.de/unternehmen/ausschreibungen?search={encoded_title}",
            'UKE Hamburg': f"https://www.uke.de/organisationsstruktur/tochtergesellschaften/kfe/ausschreibungen?search={encoded_title}",
            'Fraunhofer': f"https://vergabe.fraunhofer.de/?search={encoded_title}",
            'simap.ch (Schweiz)': f"https://www.simap.ch/en/search?q={encoded_title}",
        }
        
        return url_templates.get(platform_name, base_url)

    async def fetch_page(self, url: str, timeout: int = 30) -> str:
        """Fetch a page with error handling"""
        try:
            async with self.session.get(
                url,
                headers=self.headers,
                ssl=False,
                timeout=aiohttp.ClientTimeout(total=timeout)
            ) as resp:
                if resp.status == 200:
                    return await resp.text()
                else:
                    logger.warning(f"Status {resp.status} for {url}")
                    return ""
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return ""

    # ==================== GERMAN FEDERAL PLATFORMS ====================
    
    async def scrape_bund_de(self) -> list:
        """Scrape SERVICE.BUND.DE - Federal tenders"""
        tenders = []
        urls = [
            "https://www.service.bund.de/Content/DE/Ausschreibungen/Suche/Formular.html?nn=4641514&cl2Categories_Typ=vergabe",
            "https://www.service.bund.de/Content/DE/Ausschreibungen/Suche/Ergebnis.html"
        ]
        
        for url in urls:
            html = await self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'lxml')
                items = soup.select('.searchResult, .result-item, article, .c-teaser')
                logger.info(f"Bund.de: Found {len(items)} items")
                
                for item in items:
                    title_elem = item.select_one('h2 a, h3 a, .title a, a.c-teaser__headline')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if len(title) > 15 and self.is_relevant_tender(title):
                            link = title_elem.get('href', '')
                            if link and not link.startswith('http'):
                                link = f"https://www.service.bund.de{link}"
                            
                            desc_elem = item.select_one('.description, p, .c-teaser__text')
                            description = desc_elem.get_text(strip=True) if desc_elem else ""
                            
                            cat_info = self.categorize_tender(title, description)
                            budget = self.extract_budget(f"{title} {description}")
                            
                            tenders.append({
                                'title': title,
                                'description': description or f"Bundesausschreibung: {title}",
                                'budget': budget,
                                'deadline': self.extract_deadline(f"{title} {description}"),
                                'location': 'Deutschland',
                                'project_type': 'Federal Tender',
                                'contracting_authority': 'Bundesrepublik Deutschland',
                                'category': cat_info['category'] or 'Projektmanagement',
                                'building_typology': cat_info['building_typology'],
                                'platform_source': 'Bund.de',
                                'platform_url': 'https://www.service.bund.de',
                                'direct_link': link,
                                'country': 'Germany',
                            })
        
        return tenders

    async def scrape_evergabe_online(self) -> list:
        """Scrape e-Vergabe Online - Federal e-procurement"""
        tenders = []
        url = "https://www.evergabe-online.de/"
        
        html = await self.fetch_page(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            items = soup.select('.tender-item, article, .publication, table tr, .search-result')
            logger.info(f"e-Vergabe Online: Found {len(items)} items")
            
            for item in items:
                title_elem = item.select_one('a, h2, h3, .title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 15 and self.is_relevant_tender(title):
                        link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                        if link and not link.startswith('http'):
                            link = f"https://www.evergabe-online.de{link}"
                        
                        cat_info = self.categorize_tender(title)
                        
                        tenders.append({
                            'title': title,
                            'description': f"e-Vergabe Ausschreibung: {title}",
                            'budget': None,
                            'deadline': datetime.utcnow() + timedelta(days=30),
                            'location': 'Deutschland',
                            'project_type': 'Federal Tender',
                            'contracting_authority': 'Bundesauftraggeber',
                            'category': cat_info['category'] or 'Projektmanagement',
                            'building_typology': cat_info['building_typology'],
                            'platform_source': 'e-Vergabe Online',
                            'platform_url': 'https://www.evergabe-online.de',
                            'direct_link': link,
                            'country': 'Germany',
                        })
        
        return tenders

    async def scrape_dtvp(self) -> list:
        """Scrape Deutsches Vergabeportal (DTVP) with pagination"""
        tenders = []
        seen_tender_ids = set()
        
        # Scrape multiple pages
        for page_num in range(1, self.PAGES_TO_SCRAPE + 1):
            if page_num == 1:
                url = "https://www.dtvp.de/Center/common/project/search.do"
            else:
                url = f"https://www.dtvp.de/Center/common/project/search.do?page={page_num}"
            
            html = await self.fetch_page(url)
            if not html:
                break
                
            soup = BeautifulSoup(html, 'lxml')
            items = soup.select('.searchResult, article, .tender-item, table tr, .project-row')
            
            if len(items) == 0:
                break
            
            logger.info(f"DTVP (page {page_num}): Found {len(items)} items")
            
            for item in items:
                title_elem = item.select_one('a, h2, .title, td a')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 15 and self.is_relevant_tender(title):
                        link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                        if link and not link.startswith('http'):
                            link = f"https://www.dtvp.de{link}"
                        
                        # Extract tender ID from link (e.g., /project/12345)
                        tender_id = None
                        id_match = re.search(r'/(\d{5,8})(?:/|$|\?)', link)
                        if id_match:
                            tender_id = id_match.group(1)
                        
                        # Skip duplicates
                        if tender_id and tender_id in seen_tender_ids:
                            continue
                        if tender_id:
                            seen_tender_ids.add(tender_id)
                        
                        cat_info = self.categorize_tender(title)
                        
                        # Build description with Tender ID
                        description = f"DTVP-ID: {tender_id} | {title}" if tender_id else f"DTVP Ausschreibung: {title}"
                        
                        tenders.append({
                            'title': title,
                            'description': description,
                            'tender_id': tender_id,
                            'budget': None,
                            'deadline': datetime.utcnow() + timedelta(days=30),
                            'location': 'Deutschland',
                            'project_type': 'Public Tender',
                            'contracting_authority': 'Öffentlicher Auftraggeber',
                            'category': cat_info['category'] or 'Projektmanagement',
                            'building_typology': cat_info['building_typology'],
                            'platform_source': 'DTVP',
                            'platform_url': 'https://www.dtvp.de',
                            'direct_link': link,
                            'country': 'Germany',
                        })
            
            await asyncio.sleep(0.3)
        
        logger.info(f"DTVP TOTAL: {len(tenders)} tenders (from {self.PAGES_TO_SCRAPE} pages)")
        return tenders

    async def scrape_oeffentliche_vergabe(self) -> list:
        """Scrape oeffentlichevergabe.de"""
        tenders = []
        url = "https://www.oeffentlichevergabe.de/"
        
        html = await self.fetch_page(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            items = soup.select('.tender-item, article, .publication, table tr, .search-result, .vergabe-item')
            logger.info(f"Öffentliche Vergabe: Found {len(items)} items")
            
            for item in items:
                title_elem = item.select_one('a, h2, h3, .title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 15 and self.is_relevant_tender(title):
                        link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                        if link and not link.startswith('http'):
                            link = f"https://www.oeffentlichevergabe.de{link}"
                        
                        cat_info = self.categorize_tender(title)
                        
                        tenders.append({
                            'title': title,
                            'description': f"Öffentliche Vergabe: {title}",
                            'budget': None,
                            'deadline': datetime.utcnow() + timedelta(days=30),
                            'location': 'Deutschland',
                            'project_type': 'Public Tender',
                            'contracting_authority': 'Öffentlicher Auftraggeber',
                            'category': cat_info['category'] or 'Projektmanagement',
                            'building_typology': cat_info['building_typology'],
                            'platform_source': 'Öffentliche Vergabe',
                            'platform_url': 'https://www.oeffentlichevergabe.de',
                            'direct_link': link,
                            'country': 'Germany',
                        })
        
        return tenders

    async def scrape_ausschreibungen_deutschland(self) -> list:
        """Scrape ausschreibungen-deutschland.de - All German States with PAGINATION (5 pages)"""
        tenders = []
        
        # State-specific base URLs
        state_base_urls = [
            "https://ausschreibungen-deutschland.de/",
            "https://ausschreibungen-deutschland.de/Baden-Wuerttemberg",
            "https://ausschreibungen-deutschland.de/Bayern",
            "https://ausschreibungen-deutschland.de/Berlin",
            "https://ausschreibungen-deutschland.de/Brandenburg",
            "https://ausschreibungen-deutschland.de/Hamburg",
            "https://ausschreibungen-deutschland.de/Hessen",
            "https://ausschreibungen-deutschland.de/Niedersachsen",
            "https://ausschreibungen-deutschland.de/Nordrhein-Westfalen",
            "https://ausschreibungen-deutschland.de/Sachsen",
            "https://ausschreibungen-deutschland.de/Rheinland-Pfalz",
            "https://ausschreibungen-deutschland.de/Bremen",
            "https://ausschreibungen-deutschland.de/Saarland",
            "https://ausschreibungen-deutschland.de/Schleswig-Holstein",
            "https://ausschreibungen-deutschland.de/Thueringen",
            "https://ausschreibungen-deutschland.de/Sachsen-Anhalt",
            "https://ausschreibungen-deutschland.de/Mecklenburg-Vorpommern",
        ]
        
        seen_tender_ids = set()  # Track seen tender IDs to avoid duplicates across pages
        
        for base_url in state_base_urls:
            # Scrape multiple pages (pagination)
            for page_num in range(1, self.PAGES_TO_SCRAPE + 1):
                # Build paginated URL - ausschreibungen-deutschland.de uses /seite/N pattern
                if page_num == 1:
                    url = base_url
                else:
                    url = f"{base_url}/seite/{page_num}" if not base_url.endswith('/') else f"{base_url}seite/{page_num}"
                
                html = await self.fetch_page(url)
                if not html:
                    break  # No more pages or error
                    
                soup = BeautifulSoup(html, 'lxml')
                
                # Find ALL links on the page
                all_links = soup.find_all('a', href=True)
                items = []
                
                for link in all_links:
                    href = link.get('href', '')
                    # Match tender URLs like /2439380_Deutschland__... or /2444419_Deutschland__...
                    if href and re.match(r'^/2[0-9]{6}_', href):
                        items.append(link)
                
                if len(items) == 0:
                    break  # No tenders found, stop pagination for this state
                
                logger.info(f"Ausschreibungen-Deutschland ({base_url} page {page_num}): Found {len(items)} tender links")
                
                # Process all found tenders
                for item in items:
                    # Get the EXACT original title from the portal - no modifications
                    original_title = item.get_text(strip=True)
                    link_href = item.get('href', '')
                    
                    # Skip if title is too short or empty
                    if len(original_title) < 10:
                        continue
                    
                    if link_href and not link_href.startswith('http'):
                        link_href = f"https://ausschreibungen-deutschland.de{link_href}"
                    
                    # Extract Tender ID from URL (e.g., /2439380_Deutschland__...)
                    tender_id = None
                    id_match = re.search(r'/(\d{7})_', link_href)
                    if id_match:
                        tender_id = id_match.group(1)
                    
                    # Skip if we've already seen this tender (avoid duplicates across pages/states)
                    if tender_id and tender_id in seen_tender_ids:
                        continue
                    if tender_id:
                        seen_tender_ids.add(tender_id)
                    
                    # More permissive filter - accept all construction-related tenders
                    if self.is_relevant_tender(original_title):
                        # Extract year from URL to check publication date (format: _2025_Berlin or _2026_Berlin)
                        year_match = re.search(r'_(\d{4})_([A-Za-z-]+)$', link_href)
                        publication_year = None
                        location = 'Deutschland'
                        if year_match:
                            try:
                                publication_year = int(year_match.group(1))
                            except:
                                pass
                            location = year_match.group(2).replace('_', ' ').replace('-', ' ')
                        
                        # Filter by publication year - only 2025 and later
                        if publication_year and publication_year < 2025:
                            continue  # Skip old tenders
                        
                        # Extract contracting authority from title if available
                        authority = 'Öffentlicher Auftraggeber'
                        if 'Messe Berlin' in original_title:
                            authority = 'Messe Berlin GmbH'
                        elif 'Charité' in original_title:
                            authority = 'Charité – Universitätsmedizin Berlin'
                        
                        cat_info = self.categorize_tender(original_title)
                        budget = self.extract_budget(original_title)
                        
                        # Build description with Tender ID for easy verification
                        description = f"Ausschreibungs-ID: {tender_id} | {original_title}" if tender_id else original_title
                        
                        tenders.append({
                            'title': original_title,  # EXACT title from portal
                            'description': description,  # Includes Tender ID
                            'tender_id': tender_id,  # Store ID separately too
                            'budget': budget,
                            'deadline': self.extract_deadline(original_title),
                            'location': location,
                            'project_type': 'Public Tender',
                            'contracting_authority': authority,
                            'category': cat_info['category'] or 'Projektmanagement',
                            'building_typology': cat_info['building_typology'],
                            'platform_source': 'Ausschreibungen Deutschland',
                            'platform_url': 'https://ausschreibungen-deutschland.de/',
                            'direct_link': link_href,
                            'country': 'Germany',
                        })
                
                await asyncio.sleep(0.3)  # Rate limiting between pages
            
            await asyncio.sleep(0.2)  # Rate limiting between states
        
        logger.info(f"Ausschreibungen-Deutschland TOTAL: {len(tenders)} tenders (from {self.PAGES_TO_SCRAPE} pages per state)")
        return tenders

    async def scrape_ted_europa(self) -> list:
        """Scrape TED Europa - EU tenders"""
        tenders = []
        urls = [
            "https://ted.europa.eu/de/search/result?q=projektmanagement%20deutschland",
            "https://ted.europa.eu/de/search/result?q=baumanagement%20deutschland",
            "https://ted.europa.eu/de/search/result?q=bauleitung%20deutschland"
        ]
        
        for url in urls:
            html = await self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'lxml')
                items = soup.select('.notice-item, .search-result, article, .ted-result')
                logger.info(f"TED Europa: Found {len(items)} items")
                
                for item in items:
                    title_elem = item.select_one('h2, h3, .title, a.notice-title')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if len(title) > 15 and self.is_relevant_tender(title):
                            link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                            if link and not link.startswith('http'):
                                link = f"https://ted.europa.eu{link}"
                            
                            desc_elem = item.select_one('.description, .summary, p')
                            description = desc_elem.get_text(strip=True) if desc_elem else ""
                            
                            cat_info = self.categorize_tender(title, description)
                            budget = self.extract_budget(f"{title} {description}")
                            
                            tenders.append({
                                'title': title,
                                'description': description or f"EU Ausschreibung: {title}",
                                'budget': budget,
                                'deadline': self.extract_deadline(f"{title} {description}"),
                                'location': 'EU/Deutschland',
                                'project_type': 'EU Tender',
                                'contracting_authority': 'EU Contracting Authority',
                                'category': cat_info['category'] or 'Projektmanagement',
                                'building_typology': cat_info['building_typology'],
                                'platform_source': 'TED Europa',
                                'platform_url': 'https://ted.europa.eu',
                                'direct_link': link,
                                'country': 'Germany',
                            })
            
            await asyncio.sleep(0.5)
        
        return tenders

    async def scrape_ibau(self) -> list:
        """Scrape ibau.de"""
        tenders = []
        url = "https://www.ibau.de/ausschreibungen/"
        
        html = await self.fetch_page(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            items = soup.select('.tender-item, article, .ausschreibung, table tr, .search-result')
            logger.info(f"ibau: Found {len(items)} items")
            
            for item in items:
                title_elem = item.select_one('a, h2, h3, .title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 15 and self.is_relevant_tender(title):
                        link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                        if link and not link.startswith('http'):
                            link = f"https://www.ibau.de{link}"
                        
                        cat_info = self.categorize_tender(title)
                        
                        tenders.append({
                            'title': title,
                            'description': f"ibau Ausschreibung: {title}",
                            'budget': None,
                            'deadline': datetime.utcnow() + timedelta(days=30),
                            'location': 'Deutschland',
                            'project_type': 'Public Tender',
                            'contracting_authority': 'Öffentlicher Auftraggeber',
                            'category': cat_info['category'] or 'Projektmanagement',
                            'building_typology': cat_info['building_typology'],
                            'platform_source': 'ibau',
                            'platform_url': 'https://www.ibau.de',
                            'direct_link': link,
                            'country': 'Germany',
                        })
        
        return tenders

    async def scrape_evergabe_de(self) -> list:
        """Scrape evergabe.de"""
        tenders = []
        url = "https://www.evergabe.de/"
        
        html = await self.fetch_page(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            items = soup.select('.tender-item, article, .publication, table tr, .search-result')
            logger.info(f"evergabe.de: Found {len(items)} items")
            
            for item in items:
                title_elem = item.select_one('a, h2, h3, .title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 15 and self.is_relevant_tender(title):
                        link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                        
                        cat_info = self.categorize_tender(title)
                        
                        tenders.append({
                            'title': title,
                            'description': f"eVergabe Ausschreibung: {title}",
                            'budget': None,
                            'deadline': datetime.utcnow() + timedelta(days=30),
                            'location': 'Deutschland',
                            'project_type': 'Public Tender',
                            'contracting_authority': 'Öffentlicher Auftraggeber',
                            'category': cat_info['category'] or 'Projektmanagement',
                            'building_typology': cat_info['building_typology'],
                            'platform_source': 'eVergabe.de',
                            'platform_url': 'https://www.evergabe.de',
                            'direct_link': link,
                            'country': 'Germany',
                        })
        
        return tenders

    # ==================== GERMAN STATE PLATFORMS ====================

    async def scrape_bayern(self) -> list:
        """Scrape Vergabe Bayern - multiple URLs"""
        tenders = []
        urls = [
            "https://www.auftraege.bayern.de",
            "https://www.vergabe.bayern.de",
            "https://www.bayvebe.bayern.de"
        ]
        
        for url in urls:
            html = await self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'lxml')
                
                # Try multiple selectors
                items = soup.select('#webTicker li.itemTicker, .tender-item, table tr, .publication, article')
                logger.info(f"Bayern ({url}): Found {len(items)} items")
                
                for item in items:
                    if item.name == 'li':
                        text = item.get_text(strip=True)
                        match = re.match(r'(.+?)\s*\(([^)]+)\)$', text)
                        if match:
                            title = match.group(1).strip()
                            authority = match.group(2).strip()
                        else:
                            title = text
                            authority = 'Bayern'
                    else:
                        title_elem = item.select_one('a, .title, td:first-child a')
                        title = title_elem.get_text(strip=True) if title_elem else ""
                        authority = 'Bayern'
                    
                    if len(title) > 15 and self.is_relevant_tender(title):
                        cat_info = self.categorize_tender(title)
                        budget = self.extract_budget(title)
                        
                        tenders.append({
                            'title': title,
                            'description': f"Ausschreibung Bayern: {title}",
                            'budget': budget,
                            'deadline': self.extract_deadline(title),
                            'location': 'Bayern',
                            'project_type': 'Public Tender',
                            'contracting_authority': authority,
                            'category': cat_info['category'] or 'Projektmanagement',
                            'building_typology': cat_info['building_typology'],
                            'platform_source': 'Vergabe Bayern',
                            'platform_url': url,
                            'country': 'Germany',
                        })
            
            await asyncio.sleep(0.5)
        
        return tenders

    async def scrape_nrw(self) -> list:
        """Scrape e-Vergabe NRW"""
        tenders = []
        url = "https://www.evergabe.nrw.de/VMPSatellite/public/search"
        
        html = await self.fetch_page(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            items = soup.select('table.searchResults tr, .publication-item, .tender-row, article')
            logger.info(f"NRW: Found {len(items)} items")
            
            for item in items:
                title_elem = item.select_one('a, .title, td:first-child a')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 20 and self.is_relevant_tender(title):
                        link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                        if link and not link.startswith('http'):
                            link = f"https://www.evergabe.nrw.de{link}"
                        
                        desc_elem = item.select_one('.description, td:nth-child(2)')
                        description = desc_elem.get_text(strip=True) if desc_elem else ""
                        
                        cat_info = self.categorize_tender(title, description)
                        budget = self.extract_budget(f"{title} {description}")
                        
                        tenders.append({
                            'title': title,
                            'description': description or f"Ausschreibung NRW: {title}",
                            'budget': budget,
                            'deadline': self.extract_deadline(f"{title} {description}"),
                            'location': 'Nordrhein-Westfalen',
                            'project_type': 'Public Tender',
                            'contracting_authority': 'Land NRW',
                            'category': cat_info['category'] or 'Projektmanagement',
                            'building_typology': cat_info['building_typology'],
                            'platform_source': 'e-Vergabe NRW',
                            'platform_url': 'https://www.evergabe.nrw.de',
                            'direct_link': link,
                            'country': 'Germany',
                        })
        
        return tenders

    async def scrape_berlin(self) -> list:
        """Scrape Vergabeplattform Berlin - multiple sources"""
        tenders = []
        urls = [
            "https://www.berlin.de/vergabeplattform/veroeffentlichungen/bekanntmachungen/",
            "https://my.vergabeplattform.berlin.de/"
        ]
        
        for url in urls:
            html = await self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'lxml')
                items = soup.select('article, .list-item, table tr, .modul-teaser, .tender-item')
                logger.info(f"Berlin ({url}): Found {len(items)} items")
                
                for item in items:
                    title_elem = item.select_one('h2 a, h3 a, .title a, a.link')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if len(title) > 15 and self.is_relevant_tender(title):
                            link = title_elem.get('href', '')
                            if link and not link.startswith('http'):
                                link = f"https://www.berlin.de{link}"
                            
                            desc_elem = item.select_one('p, .description, .text')
                            description = desc_elem.get_text(strip=True) if desc_elem else ""
                            
                            cat_info = self.categorize_tender(title, description)
                            budget = self.extract_budget(f"{title} {description}")
                            
                            tenders.append({
                                'title': title,
                                'description': description or f"Ausschreibung Berlin: {title}",
                                'budget': budget,
                                'deadline': self.extract_deadline(f"{title} {description}"),
                                'location': 'Berlin',
                                'project_type': 'Public Tender',
                                'contracting_authority': 'Land Berlin',
                                'category': cat_info['category'] or 'Projektmanagement',
                                'building_typology': cat_info['building_typology'],
                                'platform_source': 'Vergabeplattform Berlin',
                                'platform_url': 'https://www.berlin.de/vergabeplattform',
                                'direct_link': link,
                                'country': 'Germany',
                            })
            
            await asyncio.sleep(0.5)
        
        return tenders

    async def scrape_hamburg(self) -> list:
        """Scrape Hamburg Vergabe - multiple sources"""
        tenders = []
        urls = [
            "https://fbhh-evergabe.web.hamburg.de/evergabe.bieter/eva/supplierportal/fhh/tabs/home",
            "https://www.hamburg.de/wirtschaft/ausschreibungen-wirtschaft/"
        ]
        
        for url in urls:
            html = await self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'lxml')
                items = soup.select('table tr, .tender-item, .publication, article, .search-result')
                logger.info(f"Hamburg ({url}): Found {len(items)} items")
                
                for item in items:
                    title_elem = item.select_one('a, .title, td a')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if len(title) > 15 and self.is_relevant_tender(title):
                            link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                            
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
                                'platform_url': url,
                                'direct_link': link,
                                'country': 'Germany',
                            })
            
            await asyncio.sleep(0.5)
        
        return tenders

    async def scrape_baden_wuerttemberg(self) -> list:
        """Scrape Baden-Württemberg - multiple sources"""
        tenders = []
        urls = [
            "https://vergabe.landbw.de/NetServer/PublicationSearchControllerServlet",
            "https://www.service-bw.de/web/guest/suche/-/leistungen/category/1005"
        ]
        
        for url in urls:
            html = await self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'lxml')
                items = soup.select('table tr, .publication-item, article, .search-result')
                logger.info(f"Baden-Württemberg ({url}): Found {len(items)} items")
                
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
                                'platform_url': url,
                                'country': 'Germany',
                            })
            
            await asyncio.sleep(0.5)
        
        return tenders

    async def scrape_hessen(self) -> list:
        """Scrape HAD Hessen"""
        tenders = []
        url = "https://www.had.de/NetServer/PublicationSearchControllerServlet"
        
        html = await self.fetch_page(url)
        if html:
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
        
        return tenders

    async def scrape_brandenburg(self) -> list:
        """Scrape Brandenburg - multiple sources"""
        tenders = []
        urls = [
            "https://vergabemarktplatz.brandenburg.de/VMPSatellite/public/search",
            "https://www.aumass.de/ausschreibungen/brandenburg"
        ]
        
        for url in urls:
            html = await self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'lxml')
                items = soup.select('table tr, .publication-item, .searchResult, article')
                logger.info(f"Brandenburg ({url}): Found {len(items)} items")
                
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
                                'platform_url': url,
                                'country': 'Germany',
                            })
            
            await asyncio.sleep(0.5)
        
        return tenders

    async def scrape_niedersachsen(self) -> list:
        """Scrape Niedersachsen"""
        tenders = []
        url = "https://vergabe.niedersachsen.de/NetServer/PublicationSearchControllerServlet"
        
        html = await self.fetch_page(url)
        if html:
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
        
        return tenders

    async def scrape_rheinland_pfalz(self) -> list:
        """Scrape Rheinland-Pfalz - multiple sources"""
        tenders = []
        urls = [
            "https://www.vergabe.rlp.de/VMPSatellite/public/search",
            "https://www.rlp.vergabekommunal.de/"
        ]
        
        for url in urls:
            html = await self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'lxml')
                items = soup.select('table tr, .publication-item, .searchResult, article')
                logger.info(f"Rheinland-Pfalz ({url}): Found {len(items)} items")
                
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
                                'platform_url': url,
                                'country': 'Germany',
                            })
            
            await asyncio.sleep(0.5)
        
        return tenders

    async def scrape_other_states(self) -> list:
        """Scrape other German states"""
        tenders = []
        state_urls = {
            'Saarland': 'https://vergabe.saarland/NetServer/PublicationSearchControllerServlet',
            'Sachsen-Anhalt': 'https://www.evergabe.sachsen-anhalt.de/NetServer/PublicationSearchControllerServlet',
            'Schleswig-Holstein': 'https://www.e-vergabe-sh.de/NetServer/PublicationSearchControllerServlet',
            'Sachsen': 'https://www.sachsen-vergabe.de/vergabe/bekanntmachung/',
            'Bremen': 'https://www.vergabe.bremen.de/NetServer/PublicationSearchControllerServlet',
            'Thüringen': 'https://www.thueringen.de/vergabe/',
        }
        
        for state, url in state_urls.items():
            html = await self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'lxml')
                items = soup.select('table tr, .publication-item, article')
                logger.info(f"{state}: Found {len(items)} items")
                
                for item in items:
                    title_elem = item.select_one('a, .title')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if len(title) > 15 and self.is_relevant_tender(title):
                            cat_info = self.categorize_tender(title)
                            
                            tenders.append({
                                'title': title,
                                'description': f"Ausschreibung {state}: {title}",
                                'budget': None,
                                'deadline': datetime.utcnow() + timedelta(days=30),
                                'location': state,
                                'project_type': 'Public Tender',
                                'contracting_authority': f'Land {state}',
                                'category': cat_info['category'] or 'Projektmanagement',
                                'building_typology': cat_info['building_typology'],
                                'platform_source': f'Vergabe {state}',
                                'platform_url': url,
                                'country': 'Germany',
                            })
            
            await asyncio.sleep(0.5)
        
        return tenders

    # ==================== HOSPITAL/KLINIK PLATFORMS ====================

    async def scrape_hospitals(self) -> list:
        """Scrape hospital tender platforms"""
        tenders = []
        hospital_urls = {
            'Charité': 'https://vergabeplattform.charite.de',
            'Vivantes': 'https://www.vivantes.de/unternehmen/ausschreibungen',
            'UKE Hamburg': 'https://www.uke.de/organisationsstruktur/tochtergesellschaften/kfe/ausschreibungen',
            'Pfalzklinikum': 'https://www.pfalzklinikum.de/ueber-uns/ausschreibungen',
            'KMG Kliniken': 'https://kmg-kliniken.de/ausschreibungen-und-vergaben',
            'Klinikverbund Südwest': 'https://www.klinikverbund-suedwest.de/der-klinikverbund-suedwest/ansprechpartner/gebaeudemanagement-technische-infrastruktur/ausschreibungen',
            'Sana Kliniken': 'https://www.sana.de/',
            'Helios Kliniken': 'https://www.helios-gesundheit.de/',
            'Asklepios Kliniken': 'https://www.asklepios.com',
        }
        
        for hospital, url in hospital_urls.items():
            html = await self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'lxml')
                items = soup.select('table tr, .tender-item, article, .ausschreibung, .search-result')
                logger.info(f"{hospital}: Found {len(items)} items")
                
                for item in items:
                    title_elem = item.select_one('a, .title, h2, h3')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if len(title) > 15 and self.is_relevant_tender(title):
                            link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                            if link and not link.startswith('http'):
                                link = f"{url.rstrip('/')}/{link.lstrip('/')}"
                            
                            cat_info = self.categorize_tender(title)
                            
                            tenders.append({
                                'title': title,
                                'description': f"{hospital} Ausschreibung: {title}",
                                'budget': None,
                                'deadline': datetime.utcnow() + timedelta(days=30),
                                'location': 'Deutschland',
                                'project_type': 'Hospital Tender',
                                'contracting_authority': hospital,
                                'category': cat_info['category'] or 'Projektmanagement',
                                'building_typology': 'Healthcare',
                                'platform_source': hospital,
                                'platform_url': url,
                                'direct_link': link,
                                'country': 'Germany',
                            })
            
            await asyncio.sleep(0.5)
        
        return tenders

    async def scrape_fraunhofer(self) -> list:
        """Scrape Fraunhofer Gesellschaft"""
        tenders = []
        url = "https://vergabe.fraunhofer.de/"
        
        html = await self.fetch_page(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            items = soup.select('table tr, .tender-item, article, .ausschreibung')
            logger.info(f"Fraunhofer: Found {len(items)} items")
            
            for item in items:
                title_elem = item.select_one('a, .title, h2, h3')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 15 and self.is_relevant_tender(title):
                        link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                        
                        cat_info = self.categorize_tender(title)
                        
                        tenders.append({
                            'title': title,
                            'description': f"Fraunhofer Ausschreibung: {title}",
                            'budget': None,
                            'deadline': datetime.utcnow() + timedelta(days=30),
                            'location': 'Deutschland',
                            'project_type': 'Research Institution Tender',
                            'contracting_authority': 'Fraunhofer Gesellschaft',
                            'category': cat_info['category'] or 'Projektmanagement',
                            'building_typology': cat_info['building_typology'],
                            'platform_source': 'Fraunhofer',
                            'platform_url': url,
                            'direct_link': link,
                            'country': 'Germany',
                        })
        
        return tenders

    # ==================== ADDITIONAL GERMAN PLATFORMS (USER REQUESTED) ====================

    async def scrape_tender_impulse(self) -> list:
        """Scrape Tender Impulse - Germany Tenders Public Projects"""
        tenders = []
        urls = [
            "https://www.tenderimpulse.com/germany-tenders",
            "https://www.tenderimpulse.com/germany-public-projects"
        ]
        
        for url in urls:
            html = await self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'lxml')
                items = soup.select('.tender-item, .project-item, article, table tr, .search-result, .card')
                logger.info(f"Tender Impulse ({url}): Found {len(items)} items")
                
                for item in items:
                    title_elem = item.select_one('a, h2, h3, .title, .tender-title')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if len(title) > 15 and self.is_relevant_tender(title):
                            link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                            if link and not link.startswith('http'):
                                link = f"https://www.tenderimpulse.com{link}"
                            
                            desc_elem = item.select_one('.description, p, .summary')
                            description = desc_elem.get_text(strip=True) if desc_elem else ""
                            
                            cat_info = self.categorize_tender(title, description)
                            budget = self.extract_budget(f"{title} {description}")
                            
                            tenders.append({
                                'title': title,
                                'description': description or f"Tender Impulse: {title}",
                                'budget': budget,
                                'deadline': self.extract_deadline(f"{title} {description}"),
                                'location': 'Deutschland',
                                'project_type': 'Public Project',
                                'contracting_authority': 'Public Authority Germany',
                                'category': cat_info['category'] or 'Projektmanagement',
                                'building_typology': cat_info['building_typology'],
                                'platform_source': 'Tender Impulse',
                                'platform_url': 'https://www.tenderimpulse.com',
                                'direct_link': link,
                                'country': 'Germany',
                            })
            
            await asyncio.sleep(0.5)
        
        return tenders

    async def scrape_vergabe24(self) -> list:
        """Scrape vergabe24.de"""
        tenders = []
        url = "https://www.vergabe24.de/"
        
        html = await self.fetch_page(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            items = soup.select('.tender-item, .vergabe-item, article, table tr, .search-result, .ausschreibung')
            logger.info(f"vergabe24.de: Found {len(items)} items")
            
            for item in items:
                title_elem = item.select_one('a, h2, h3, .title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 15 and self.is_relevant_tender(title):
                        link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                        if link and not link.startswith('http'):
                            link = f"https://www.vergabe24.de{link}"
                        
                        cat_info = self.categorize_tender(title)
                        
                        tenders.append({
                            'title': title,
                            'description': f"vergabe24 Ausschreibung: {title}",
                            'budget': None,
                            'deadline': datetime.utcnow() + timedelta(days=30),
                            'location': 'Deutschland',
                            'project_type': 'Public Tender',
                            'contracting_authority': 'Öffentlicher Auftraggeber',
                            'category': cat_info['category'] or 'Projektmanagement',
                            'building_typology': cat_info['building_typology'],
                            'platform_source': 'vergabe24',
                            'platform_url': 'https://www.vergabe24.de',
                            'direct_link': link,
                            'country': 'Germany',
                        })
        
        return tenders

    async def scrape_dtad(self) -> list:
        """Scrape dtad.de - Deutscher Tender-Ausschreibungsdienst"""
        tenders = []
        url = "https://www.dtad.de/"
        
        html = await self.fetch_page(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            items = soup.select('.tender-item, .ausschreibung, article, table tr, .search-result, .project-card')
            logger.info(f"DTAD: Found {len(items)} items")
            
            for item in items:
                title_elem = item.select_one('a, h2, h3, .title, .tender-title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 15 and self.is_relevant_tender(title):
                        link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                        if link and not link.startswith('http'):
                            link = f"https://www.dtad.de{link}"
                        
                        cat_info = self.categorize_tender(title)
                        
                        tenders.append({
                            'title': title,
                            'description': f"DTAD Ausschreibung: {title}",
                            'budget': None,
                            'deadline': datetime.utcnow() + timedelta(days=30),
                            'location': 'Deutschland',
                            'project_type': 'Public Tender',
                            'contracting_authority': 'Öffentlicher Auftraggeber',
                            'category': cat_info['category'] or 'Projektmanagement',
                            'building_typology': cat_info['building_typology'],
                            'platform_source': 'DTAD',
                            'platform_url': 'https://www.dtad.de',
                            'direct_link': link,
                            'country': 'Germany',
                        })
        
        return tenders

    async def scrape_cwc_tenders(self) -> list:
        """Scrape CWC Tenders Germany"""
        tenders = []
        url = "https://www.cwctenders.com/de/index.php"
        
        html = await self.fetch_page(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            items = soup.select('.tender-item, article, table tr, .search-result, .tender-row')
            logger.info(f"CWC Tenders: Found {len(items)} items")
            
            for item in items:
                title_elem = item.select_one('a, h2, h3, .title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 15 and self.is_relevant_tender(title):
                        link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                        if link and not link.startswith('http'):
                            link = f"https://www.cwctenders.com{link}"
                        
                        cat_info = self.categorize_tender(title)
                        
                        tenders.append({
                            'title': title,
                            'description': f"CWC Tender: {title}",
                            'budget': None,
                            'deadline': datetime.utcnow() + timedelta(days=30),
                            'location': 'Deutschland',
                            'project_type': 'Public Tender',
                            'contracting_authority': 'Public Authority',
                            'category': cat_info['category'] or 'Projektmanagement',
                            'building_typology': cat_info['building_typology'],
                            'platform_source': 'CWC Tenders',
                            'platform_url': 'https://www.cwctenders.com',
                            'direct_link': link,
                            'country': 'Germany',
                        })
        
        return tenders

    async def scrape_bidding_source(self) -> list:
        """Scrape BiddingSource Germany"""
        tenders = []
        url = "https://www.biddingsource.com/tenders/"
        
        html = await self.fetch_page(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            items = soup.select('.tender-item, article, table tr, .search-result, .card, .tender-card')
            logger.info(f"BiddingSource: Found {len(items)} items")
            
            for item in items:
                title_elem = item.select_one('a, h2, h3, .title, .tender-title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 15 and self.is_relevant_tender(title):
                        link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                        if link and not link.startswith('http'):
                            link = f"https://www.biddingsource.com{link}"
                        
                        cat_info = self.categorize_tender(title)
                        
                        tenders.append({
                            'title': title,
                            'description': f"BiddingSource: {title}",
                            'budget': None,
                            'deadline': datetime.utcnow() + timedelta(days=30),
                            'location': 'Deutschland',
                            'project_type': 'Public Tender',
                            'contracting_authority': 'Public Authority',
                            'category': cat_info['category'] or 'Projektmanagement',
                            'building_typology': cat_info['building_typology'],
                            'platform_source': 'BiddingSource',
                            'platform_url': 'https://www.biddingsource.com',
                            'direct_link': link,
                            'country': 'Germany',
                        })
        
        return tenders

    async def scrape_a24_salescloud(self) -> list:
        """Scrape A24 Sales Cloud"""
        tenders = []
        url = "https://a24salescloud.de/"
        
        html = await self.fetch_page(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            items = soup.select('.tender-item, article, table tr, .search-result, .project-card, .ausschreibung')
            logger.info(f"A24 Sales Cloud: Found {len(items)} items")
            
            for item in items:
                title_elem = item.select_one('a, h2, h3, .title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 15 and self.is_relevant_tender(title):
                        link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                        if link and not link.startswith('http'):
                            link = f"https://a24salescloud.de{link}"
                        
                        cat_info = self.categorize_tender(title)
                        
                        tenders.append({
                            'title': title,
                            'description': f"A24 Sales Cloud: {title}",
                            'budget': None,
                            'deadline': datetime.utcnow() + timedelta(days=30),
                            'location': 'Deutschland',
                            'project_type': 'Public Tender',
                            'contracting_authority': 'Öffentlicher Auftraggeber',
                            'category': cat_info['category'] or 'Projektmanagement',
                            'building_typology': cat_info['building_typology'],
                            'platform_source': 'A24 Sales Cloud',
                            'platform_url': 'https://a24salescloud.de',
                            'direct_link': link,
                            'country': 'Germany',
                        })
        
        return tenders

    async def scrape_berlin_procurement(self) -> list:
        """Scrape Berlin Procurement Cooperation platforms"""
        tenders = []
        urls = [
            "https://my.vergabeplattform.berlin.de/",
            "https://www.berlin.de/vergabeplattform/"
        ]
        
        for url in urls:
            html = await self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'lxml')
                items = soup.select('.tender-item, article, table tr, .search-result, .vergabe-item, .modul-teaser')
                logger.info(f"Berlin Procurement ({url}): Found {len(items)} items")
                
                for item in items:
                    title_elem = item.select_one('a, h2, h3, .title')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if len(title) > 15 and self.is_relevant_tender(title):
                            link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                            if link and not link.startswith('http'):
                                link = f"https://www.berlin.de{link}"
                            
                            cat_info = self.categorize_tender(title)
                            
                            tenders.append({
                                'title': title,
                                'description': f"Berlin Procurement: {title}",
                                'budget': None,
                                'deadline': datetime.utcnow() + timedelta(days=30),
                                'location': 'Berlin',
                                'project_type': 'Public Tender',
                                'contracting_authority': 'Land Berlin',
                                'category': cat_info['category'] or 'Projektmanagement',
                                'building_typology': cat_info['building_typology'],
                                'platform_source': 'Berlin Procurement Cooperation',
                                'platform_url': url,
                                'direct_link': link,
                                'country': 'Germany',
                            })
            
            await asyncio.sleep(0.5)
        
        return tenders

    async def scrape_lzbw(self) -> list:
        """Scrape LZBW - Logistikzentrum Baden-Württemberg"""
        tenders = []
        url = "https://www.lzbw.de/ausschreibungen"
        
        html = await self.fetch_page(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            items = soup.select('.tender-item, article, table tr, .search-result, .ausschreibung, .content-item')
            logger.info(f"LZBW: Found {len(items)} items")
            
            for item in items:
                title_elem = item.select_one('a, h2, h3, .title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 15 and self.is_relevant_tender(title):
                        link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                        if link and not link.startswith('http'):
                            link = f"https://www.lzbw.de{link}"
                        
                        cat_info = self.categorize_tender(title)
                        
                        tenders.append({
                            'title': title,
                            'description': f"LZBW Ausschreibung: {title}",
                            'budget': None,
                            'deadline': datetime.utcnow() + timedelta(days=30),
                            'location': 'Baden-Württemberg',
                            'project_type': 'State Tender',
                            'contracting_authority': 'Logistikzentrum Baden-Württemberg',
                            'category': cat_info['category'] or 'Projektmanagement',
                            'building_typology': cat_info['building_typology'],
                            'platform_source': 'LZBW',
                            'platform_url': 'https://www.lzbw.de',
                            'direct_link': link,
                            'country': 'Germany',
                        })
        
        return tenders

    async def scrape_de_baunetzwerk(self) -> list:
        """Scrape D&E BauNetzwerk"""
        tenders = []
        url = "https://www.de-baunetzwerk.de/"
        
        html = await self.fetch_page(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            items = soup.select('.tender-item, .project-item, article, table tr, .search-result, .bauvorhaben')
            logger.info(f"D&E BauNetzwerk: Found {len(items)} items")
            
            for item in items:
                title_elem = item.select_one('a, h2, h3, .title, .project-title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 15 and self.is_relevant_tender(title):
                        link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                        if link and not link.startswith('http'):
                            link = f"https://www.de-baunetzwerk.de{link}"
                        
                        desc_elem = item.select_one('.description, p, .summary')
                        description = desc_elem.get_text(strip=True) if desc_elem else ""
                        
                        cat_info = self.categorize_tender(title, description)
                        budget = self.extract_budget(f"{title} {description}")
                        
                        tenders.append({
                            'title': title,
                            'description': description or f"D&E BauNetzwerk: {title}",
                            'budget': budget,
                            'deadline': self.extract_deadline(f"{title} {description}"),
                            'location': 'Deutschland',
                            'project_type': 'Construction Project',
                            'contracting_authority': 'Bauherr',
                            'category': cat_info['category'] or 'Projektmanagement',
                            'building_typology': cat_info['building_typology'],
                            'platform_source': 'D&E BauNetzwerk',
                            'platform_url': 'https://www.de-baunetzwerk.de',
                            'direct_link': link,
                            'country': 'Germany',
                        })
        
        return tenders

    async def scrape_global_tenders_germany(self) -> list:
        """Scrape Global Tenders - Germany section"""
        tenders = []
        url = "https://www.globaltenders.com/tenders-by-country/germany-tenders/"
        
        html = await self.fetch_page(url)
        if html:
            soup = BeautifulSoup(html, 'lxml')
            items = soup.select('.tender-item, article, table tr, .search-result, .tender-row, .card')
            logger.info(f"Global Tenders Germany: Found {len(items)} items")
            
            for item in items:
                title_elem = item.select_one('a, h2, h3, .title, .tender-title')
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    if len(title) > 15 and self.is_relevant_tender(title):
                        link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                        if link and not link.startswith('http'):
                            link = f"https://www.globaltenders.com{link}"
                        
                        cat_info = self.categorize_tender(title)
                        
                        tenders.append({
                            'title': title,
                            'description': f"Global Tenders: {title}",
                            'budget': None,
                            'deadline': datetime.utcnow() + timedelta(days=30),
                            'location': 'Deutschland',
                            'project_type': 'Public Tender',
                            'contracting_authority': 'Public Authority Germany',
                            'category': cat_info['category'] or 'Projektmanagement',
                            'building_typology': cat_info['building_typology'],
                            'platform_source': 'Global Tenders Germany',
                            'platform_url': 'https://www.globaltenders.com',
                            'direct_link': link,
                            'country': 'Germany',
                        })
        
        return tenders

    async def scrape_aumass(self) -> list:
        """Scrape AUMASS Ausschreibungen"""
        tenders = []
        urls = [
            "https://www.aumass.de/ausschreibungen/",
            "https://www.aumass.de/ausschreibungen/brandenburg"
        ]
        
        for url in urls:
            html = await self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'lxml')
                items = soup.select('.tender-item, article, table tr, .search-result, .ausschreibung-item')
                logger.info(f"AUMASS ({url}): Found {len(items)} items")
                
                for item in items:
                    title_elem = item.select_one('a, h2, h3, .title')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if len(title) > 15 and self.is_relevant_tender(title):
                            link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                            if link and not link.startswith('http'):
                                link = f"https://www.aumass.de{link}"
                            
                            cat_info = self.categorize_tender(title)
                            
                            tenders.append({
                                'title': title,
                                'description': f"AUMASS Ausschreibung: {title}",
                                'budget': None,
                                'deadline': datetime.utcnow() + timedelta(days=30),
                                'location': 'Deutschland',
                                'project_type': 'Public Tender',
                                'contracting_authority': 'Öffentlicher Auftraggeber',
                                'category': cat_info['category'] or 'Projektmanagement',
                                'building_typology': cat_info['building_typology'],
                                'platform_source': 'AUMASS',
                                'platform_url': 'https://www.aumass.de',
                                'direct_link': link,
                                'country': 'Germany',
                            })
            
            await asyncio.sleep(0.5)
        
        return tenders

    async def scrape_additional_hospitals(self) -> list:
        """Scrape additional hospital platforms from user's list"""
        tenders = []
        additional_hospital_urls = {
            'Ammerland Klinik': 'https://www.ammerland-klinik.de/ausschreibungen',
        }
        
        for hospital, url in additional_hospital_urls.items():
            html = await self.fetch_page(url)
            if html:
                soup = BeautifulSoup(html, 'lxml')
                items = soup.select('table tr, .tender-item, article, .ausschreibung, .search-result')
                logger.info(f"{hospital}: Found {len(items)} items")
                
                for item in items:
                    title_elem = item.select_one('a, .title, h2, h3')
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        if len(title) > 15 and self.is_relevant_tender(title):
                            link = title_elem.get('href', '') if title_elem.name == 'a' else ''
                            if link and not link.startswith('http'):
                                link = f"{url.rstrip('/')}/{link.lstrip('/')}"
                            
                            cat_info = self.categorize_tender(title)
                            
                            tenders.append({
                                'title': title,
                                'description': f"{hospital} Ausschreibung: {title}",
                                'budget': None,
                                'deadline': datetime.utcnow() + timedelta(days=30),
                                'location': 'Deutschland',
                                'project_type': 'Hospital Tender',
                                'contracting_authority': hospital,
                                'category': cat_info['category'] or 'Projektmanagement',
                                'building_typology': 'Healthcare',
                                'platform_source': hospital,
                                'platform_url': url,
                                'direct_link': link,
                                'country': 'Germany',
                            })
            
            await asyncio.sleep(0.5)
        
        return tenders

    # ==================== SWISS PLATFORM ====================

    async def scrape_simap_switzerland(self) -> list:
        """Scrape simap.ch Switzerland using Playwright browser automation for REAL data from archive
        Includes pagination (5 pages) and Tender ID (Meldungsnummer) in descriptions
        Only returns tenders from 2025 onwards"""
        tenders = []
        seen_tender_ids = set()  # Track seen tender IDs to avoid duplicates
        
        try:
            from playwright.async_api import async_playwright
            
            logger.info("simap.ch: Starting Playwright browser automation for REAL Swiss tenders from archive...")
            
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page(viewport={'width': 1920, 'height': 1080})
                
                # Search for multiple construction-related terms
                search_terms = ['Projektsteuerung', 'Bauleitung', 'Baumanagement', 'Hochbau', 'Architektur', 'Planung', 'Sanierung']
                
                for term in search_terms:
                    try:
                        # Navigate to archive search
                        await page.goto('https://archiv.simap.ch', wait_until='networkidle', timeout=30000)
                        await page.wait_for_timeout(2000)
                        
                        # Fill in search keyword
                        keyword_input = page.locator('input').first
                        await keyword_input.fill(term)
                        await page.wait_for_timeout(500)
                        
                        # Click search button
                        search_btn = page.locator('button:has-text("Suchen")').first
                        await search_btn.click()
                        await page.wait_for_timeout(4000)
                        
                        # Paginate through results (up to PAGES_TO_SCRAPE pages)
                        for page_num in range(1, self.PAGES_TO_SCRAPE + 1):
                            if page_num > 1:
                                # Try to click "Next" or navigate to next page
                                try:
                                    next_btn = page.locator('button:has-text("Weiter"), a:has-text("Weiter"), .pagination a.next, a[rel="next"]').first
                                    if await next_btn.count() > 0:
                                        await next_btn.click()
                                        await page.wait_for_timeout(3000)
                                    else:
                                        break  # No more pages
                                except:
                                    break  # No pagination available
                            
                            # Get the table rows with results
                            rows = await page.locator('table tbody tr, tr').all()
                            logger.info(f"simap.ch ({term}, page {page_num}): Found {len(rows)} result rows")
                            
                            if len(rows) == 0:
                                break  # No more results
                            
                            for row in rows[:20]:  # Limit per page
                                try:
                                    text = await row.inner_text()
                                    text = text.strip()
                                    
                                    # Skip header rows or empty rows
                                    if len(text) < 30 or ('Datum' in text and 'Nr.' in text):
                                        continue
                                    
                                    # Parse the tender info from row text
                                    lines = text.split('\n')
                                    
                                    # Extract Meldungsnummer (Tender ID) - usually a number at start of row
                                    tender_id = None
                                    for line in lines:
                                        line = line.strip()
                                        # Match patterns like "1234567" or "Meldungsnummer: 1234567"
                                        id_match = re.search(r'(\d{6,8})', line)
                                        if id_match and len(line) < 20:
                                            tender_id = id_match.group(1)
                                            break
                                    
                                    # Skip if we've already seen this tender
                                    if tender_id and tender_id in seen_tender_ids:
                                        continue
                                    if tender_id:
                                        seen_tender_ids.add(tender_id)
                                    
                                    # Get the tender title
                                    title = None
                                    for line in lines:
                                        line = line.strip()
                                        if len(line) > 30 and not line[0].isdigit() and 'CPV:' not in line and 'Gesamtansicht' not in line:
                                            title = line
                                            break
                                    
                                    if title and self.is_relevant_tender(title):
                                        # Check publication date - extract year from text
                                        pub_date = self.extract_publication_date(text)
                                        if pub_date and pub_date.year < 2025:
                                            continue  # Skip old tenders
                                        
                                        # Get link if available
                                        link_elem = row.locator('a').first
                                        link = 'https://archiv.simap.ch/result'
                                        if await link_elem.count() > 0:
                                            href = await link_elem.get_attribute('href') or ''
                                            if href:
                                                link = f'https://archiv.simap.ch{href}' if not href.startswith('http') else href
                                        
                                        # Extract authority from text
                                        authority = 'Schweizer Öffentlicher Auftraggeber'
                                        for line in lines:
                                            line = line.strip()
                                            if any(kw in line for kw in ['Bundesamt', 'Kanton', 'Stadt', 'Gemeinde', 'SBB', 'ETH', 'Universität']):
                                                authority = line
                                                break
                                        
                                        cat_info = self.categorize_tender(title)
                                        
                                        # Build description with Tender ID (Meldungsnummer) for verification
                                        description = f"Meldungsnummer: {tender_id} | {title}" if tender_id else title
                                        
                                        # Check if this tender already exists (dedup by title)
                                        if not any(t['title'] == title for t in tenders):
                                            tenders.append({
                                                'title': title,  # EXACT title from portal
                                                'description': description,  # Includes Meldungsnummer
                                                'tender_id': tender_id,  # Store ID separately
                                                'budget': self.extract_budget(text),
                                                'deadline': self.extract_deadline(text),
                                                'location': 'Schweiz',
                                                'project_type': 'Public Tender',
                                                'contracting_authority': authority,
                                                'category': cat_info['category'] or 'Projektmanagement',
                                                'building_typology': cat_info['building_typology'],
                                                'platform_source': 'simap.ch (Schweiz)',
                                                'platform_url': 'https://archiv.simap.ch',
                                                'direct_link': link,
                                                'country': 'Switzerland',
                                            })
                                except Exception as e:
                                    logger.debug(f"Error parsing row: {e}")
                                    continue
                        
                    except Exception as e:
                        logger.warning(f"simap.ch search error for '{term}': {e}")
                        continue
                
                await browser.close()
                
        except ImportError:
            logger.warning("Playwright not installed - cannot scrape simap.ch")
        except Exception as e:
            logger.error(f"simap.ch Playwright error: {e}")
        
        logger.info(f"simap.ch: Found {len(tenders)} REAL Swiss tenders (from {self.PAGES_TO_SCRAPE} pages per search term)")
        return tenders

    # ==================== DEDUPLICATION ====================

    def deduplicate_tenders(self, all_tenders: list) -> list:
        """Remove duplicate tenders, keeping the one from the best source"""
        unique_tenders = {}
        
        for tender in all_tenders:
            title_hash = self.get_title_hash(tender['title'])
            
            # Check if we've seen a similar tender
            found_duplicate = False
            for existing_hash, existing_tender in list(unique_tenders.items()):
                if self.is_similar_title(tender['title'], existing_tender['title']):
                    # Keep the one with higher priority platform
                    current_priority = PLATFORM_PRIORITY.get(tender['platform_source'], 50)
                    existing_priority = PLATFORM_PRIORITY.get(existing_tender['platform_source'], 50)
                    
                    if current_priority > existing_priority:
                        # Replace with higher priority source
                        # But track that it exists on multiple platforms
                        tender['duplicate_sources'] = existing_tender.get('duplicate_sources', []) + [existing_tender['platform_source']]
                        unique_tenders[existing_hash] = tender
                    else:
                        # Keep existing but note the duplicate
                        existing_tender['duplicate_sources'] = existing_tender.get('duplicate_sources', []) + [tender['platform_source']]
                    
                    found_duplicate = True
                    break
            
            if not found_duplicate:
                unique_tenders[title_hash] = tender
        
        logger.info(f"Deduplication: {len(all_tenders)} -> {len(unique_tenders)} unique tenders")
        return list(unique_tenders.values())

    # ==================== MAIN SCRAPE ====================

    async def scrape_all(self) -> int:
        """Scrape all platforms and save to database with deduplication"""
        async with aiohttp.ClientSession() as session:
            self.session = session
            
            all_tenders = []
            
            logger.info("Starting comprehensive scrape of ALL platforms...")
            
            # ========== GERMAN FEDERAL PLATFORMS ==========
            logger.info("\n=== German Federal Platforms ===")
            
            bund_tenders = await self.scrape_bund_de()
            all_tenders.extend(bund_tenders)
            logger.info(f"Bund.de: {len(bund_tenders)} tenders")
            
            evergabe_tenders = await self.scrape_evergabe_online()
            all_tenders.extend(evergabe_tenders)
            logger.info(f"e-Vergabe Online: {len(evergabe_tenders)} tenders")
            
            dtvp_tenders = await self.scrape_dtvp()
            all_tenders.extend(dtvp_tenders)
            logger.info(f"DTVP: {len(dtvp_tenders)} tenders")
            
            oeff_tenders = await self.scrape_oeffentliche_vergabe()
            all_tenders.extend(oeff_tenders)
            logger.info(f"Öffentliche Vergabe: {len(oeff_tenders)} tenders")
            
            ausch_de_tenders = await self.scrape_ausschreibungen_deutschland()
            all_tenders.extend(ausch_de_tenders)
            logger.info(f"Ausschreibungen Deutschland: {len(ausch_de_tenders)} tenders")
            
            ted_tenders = await self.scrape_ted_europa()
            all_tenders.extend(ted_tenders)
            logger.info(f"TED Europa: {len(ted_tenders)} tenders")
            
            ibau_tenders = await self.scrape_ibau()
            all_tenders.extend(ibau_tenders)
            logger.info(f"ibau: {len(ibau_tenders)} tenders")
            
            evergabe_de_tenders = await self.scrape_evergabe_de()
            all_tenders.extend(evergabe_de_tenders)
            logger.info(f"evergabe.de: {len(evergabe_de_tenders)} tenders")
            
            # ========== GERMAN STATE PLATFORMS ==========
            logger.info("\n=== German State Platforms ===")
            
            bayern_tenders = await self.scrape_bayern()
            all_tenders.extend(bayern_tenders)
            logger.info(f"Bayern: {len(bayern_tenders)} tenders")
            
            nrw_tenders = await self.scrape_nrw()
            all_tenders.extend(nrw_tenders)
            logger.info(f"NRW: {len(nrw_tenders)} tenders")
            
            berlin_tenders = await self.scrape_berlin()
            all_tenders.extend(berlin_tenders)
            logger.info(f"Berlin: {len(berlin_tenders)} tenders")
            
            hamburg_tenders = await self.scrape_hamburg()
            all_tenders.extend(hamburg_tenders)
            logger.info(f"Hamburg: {len(hamburg_tenders)} tenders")
            
            bw_tenders = await self.scrape_baden_wuerttemberg()
            all_tenders.extend(bw_tenders)
            logger.info(f"Baden-Württemberg: {len(bw_tenders)} tenders")
            
            hessen_tenders = await self.scrape_hessen()
            all_tenders.extend(hessen_tenders)
            logger.info(f"Hessen: {len(hessen_tenders)} tenders")
            
            brandenburg_tenders = await self.scrape_brandenburg()
            all_tenders.extend(brandenburg_tenders)
            logger.info(f"Brandenburg: {len(brandenburg_tenders)} tenders")
            
            niedersachsen_tenders = await self.scrape_niedersachsen()
            all_tenders.extend(niedersachsen_tenders)
            logger.info(f"Niedersachsen: {len(niedersachsen_tenders)} tenders")
            
            rlp_tenders = await self.scrape_rheinland_pfalz()
            all_tenders.extend(rlp_tenders)
            logger.info(f"Rheinland-Pfalz: {len(rlp_tenders)} tenders")
            
            other_state_tenders = await self.scrape_other_states()
            all_tenders.extend(other_state_tenders)
            logger.info(f"Other States: {len(other_state_tenders)} tenders")
            
            # ========== HOSPITAL PLATFORMS ==========
            logger.info("\n=== Hospital Platforms ===")
            
            hospital_tenders = await self.scrape_hospitals()
            all_tenders.extend(hospital_tenders)
            logger.info(f"Hospitals: {len(hospital_tenders)} tenders")
            
            fraunhofer_tenders = await self.scrape_fraunhofer()
            all_tenders.extend(fraunhofer_tenders)
            logger.info(f"Fraunhofer: {len(fraunhofer_tenders)} tenders")
            
            # ========== ADDITIONAL USER-REQUESTED PLATFORMS ==========
            logger.info("\n=== Additional German Platforms (User Requested) ===")
            
            tender_impulse_tenders = await self.scrape_tender_impulse()
            all_tenders.extend(tender_impulse_tenders)
            logger.info(f"Tender Impulse: {len(tender_impulse_tenders)} tenders")
            
            vergabe24_tenders = await self.scrape_vergabe24()
            all_tenders.extend(vergabe24_tenders)
            logger.info(f"vergabe24: {len(vergabe24_tenders)} tenders")
            
            dtad_tenders = await self.scrape_dtad()
            all_tenders.extend(dtad_tenders)
            logger.info(f"DTAD: {len(dtad_tenders)} tenders")
            
            cwc_tenders = await self.scrape_cwc_tenders()
            all_tenders.extend(cwc_tenders)
            logger.info(f"CWC Tenders: {len(cwc_tenders)} tenders")
            
            bidding_source_tenders = await self.scrape_bidding_source()
            all_tenders.extend(bidding_source_tenders)
            logger.info(f"BiddingSource: {len(bidding_source_tenders)} tenders")
            
            a24_tenders = await self.scrape_a24_salescloud()
            all_tenders.extend(a24_tenders)
            logger.info(f"A24 Sales Cloud: {len(a24_tenders)} tenders")
            
            berlin_procurement_tenders = await self.scrape_berlin_procurement()
            all_tenders.extend(berlin_procurement_tenders)
            logger.info(f"Berlin Procurement: {len(berlin_procurement_tenders)} tenders")
            
            lzbw_tenders = await self.scrape_lzbw()
            all_tenders.extend(lzbw_tenders)
            logger.info(f"LZBW: {len(lzbw_tenders)} tenders")
            
            baunetzwerk_tenders = await self.scrape_de_baunetzwerk()
            all_tenders.extend(baunetzwerk_tenders)
            logger.info(f"D&E BauNetzwerk: {len(baunetzwerk_tenders)} tenders")
            
            global_tenders = await self.scrape_global_tenders_germany()
            all_tenders.extend(global_tenders)
            logger.info(f"Global Tenders Germany: {len(global_tenders)} tenders")
            
            aumass_tenders = await self.scrape_aumass()
            all_tenders.extend(aumass_tenders)
            logger.info(f"AUMASS: {len(aumass_tenders)} tenders")
            
            additional_hospital_tenders = await self.scrape_additional_hospitals()
            all_tenders.extend(additional_hospital_tenders)
            logger.info(f"Additional Hospitals: {len(additional_hospital_tenders)} tenders")
            
            # ========== SWISS PLATFORM ==========
            logger.info("\n=== Swiss Platforms ===")
            
            simap_tenders = await self.scrape_simap_switzerland()
            all_tenders.extend(simap_tenders)
            logger.info(f"simap.ch: {len(simap_tenders)} tenders")
            
            # ========== DEDUPLICATION ==========
            logger.info(f"\n=== Deduplication ===")
            logger.info(f"Total scraped before deduplication: {len(all_tenders)}")
            
            unique_tenders = self.deduplicate_tenders(all_tenders)
            logger.info(f"After deduplication: {len(unique_tenders)} unique tenders")
            
            # ========== SAVE TO DATABASE ==========
            added_count = 0
            for tender in unique_tenders:
                # Check for existing in database
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
                    
                    # Ensure country field
                    if 'country' not in tender:
                        tender['country'] = 'Germany'
                    
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
    
    # Show country distribution
    print("\n=== Country Distribution ===")
    async for doc in db.tenders.aggregate([
        {'$group': {'_id': '$country', 'count': {'$sum': 1}}},
        {'$sort': {'count': -1}}
    ]):
        print(f"  {doc['_id']}: {doc['count']}")
    
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
