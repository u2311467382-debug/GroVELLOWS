"""
Live News Scraper for German Construction News
Scrapes construction industry news from German news portals and papers
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

class NewsScraperBase:
    """Base scraper class for news portals"""
    
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
    
    def generate_news_id(self, title: str, source: str) -> str:
        """Generate unique ID for news deduplication"""
        unique_string = f"{title}_{source}"
        return hashlib.md5(unique_string.encode()).hexdigest()[:16]
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize text"""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text.strip())
    
    def parse_german_date(self, date_str: str) -> Optional[datetime]:
        """Parse German date formats"""
        if not date_str:
            return datetime.utcnow()
        
        date_str = self.clean_text(date_str)
        
        # German month names
        german_months = {
            'januar': '01', 'februar': '02', 'märz': '03', 'april': '04',
            'mai': '05', 'juni': '06', 'juli': '07', 'august': '08',
            'september': '09', 'oktober': '10', 'november': '11', 'dezember': '12',
            'jan': '01', 'feb': '02', 'mär': '03', 'apr': '04',
            'jun': '06', 'jul': '07', 'aug': '08', 'sep': '09',
            'okt': '10', 'nov': '11', 'dez': '12'
        }
        
        formats = [
            "%d.%m.%Y",
            "%d.%m.%Y %H:%M",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d. %B %Y",
            "%B %d, %Y",
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Try relative dates
        date_lower = date_str.lower()
        if 'heute' in date_lower or 'today' in date_lower:
            return datetime.utcnow()
        elif 'gestern' in date_lower or 'yesterday' in date_lower:
            return datetime.utcnow() - timedelta(days=1)
        elif 'vor' in date_lower:
            # "vor 2 Stunden", "vor 3 Tagen"
            numbers = re.findall(r'\d+', date_str)
            if numbers:
                num = int(numbers[0])
                if 'stunde' in date_lower or 'hour' in date_lower:
                    return datetime.utcnow() - timedelta(hours=num)
                elif 'tag' in date_lower or 'day' in date_lower:
                    return datetime.utcnow() - timedelta(days=num)
        
        return datetime.utcnow()
    
    def calculate_relevance(self, title: str, summary: str) -> int:
        """Calculate relevance score for construction industry"""
        text = f"{title} {summary}".lower()
        score = 50  # Base score
        
        # High relevance keywords
        high_keywords = [
            'bauprojekt', 'construction', 'baubranche', 'bauwirtschaft',
            'immobilien', 'real estate', 'property', 'entwicklung',
            'neubau', 'sanierung', 'renovation', 'umbau',
            'ausschreibung', 'tender', 'vergabe', 'auftrag',
            'krankenhaus', 'hospital', 'klinik', 'healthcare',
            'wohnungsbau', 'residential', 'gewerbebau', 'commercial',
            'infrastruktur', 'infrastructure', 'brücke', 'tunnel'
        ]
        
        # Medium relevance keywords
        medium_keywords = [
            'architektur', 'architecture', 'planung', 'planning',
            'investor', 'investment', 'finanzierung', 'financing',
            'nachhaltigkeit', 'sustainability', 'green building',
            'digitalisierung', 'bim', 'smart building'
        ]
        
        # Check for project delays/stuck projects (important for market intelligence)
        stuck_keywords = [
            'verzögerung', 'delay', 'stillstand', 'stopped',
            'insolvenz', 'insolvency', 'bankrupt', 'pleite',
            'probleme', 'problems', 'krise', 'crisis',
            'stockt', 'stalled', 'gescheitert', 'failed'
        ]
        
        for keyword in high_keywords:
            if keyword in text:
                score += 15
        
        for keyword in medium_keywords:
            if keyword in text:
                score += 8
        
        for keyword in stuck_keywords:
            if keyword in text:
                score += 20  # Higher score for stuck project news
        
        return min(score, 100)
    
    def categorize_news(self, title: str, summary: str) -> str:
        """Categorize news article"""
        text = f"{title} {summary}".lower()
        
        if any(w in text for w in ['verzögerung', 'stillstand', 'insolvenz', 'krise', 'probleme']):
            return "Project Issues"
        elif any(w in text for w in ['neubau', 'grundsteinlegung', 'spatenstich', 'eröffnung']):
            return "New Projects"
        elif any(w in text for w in ['ausschreibung', 'vergabe', 'tender', 'auftrag']):
            return "Tenders & Contracts"
        elif any(w in text for w in ['markt', 'market', 'trend', 'prognose', 'forecast']):
            return "Market Analysis"
        elif any(w in text for w in ['gesetz', 'regulation', 'vorschrift', 'norm']):
            return "Regulations"
        elif any(w in text for w in ['nachhaltig', 'green', 'klimaneutral', 'energieeffizient']):
            return "Sustainability"
        elif any(w in text for w in ['digital', 'bim', 'smart', 'technologie']):
            return "Technology"
        else:
            return "General"


class BauNetzScraper(NewsScraperBase):
    """Scraper for BauNetz - German Architecture/Construction News"""
    
    BASE_URL = "https://www.baunetz.de"
    
    async def scrape(self, max_results: int = 20) -> List[Dict]:
        """Scrape news from BauNetz"""
        news = []
        
        try:
            urls = [
                f"{self.BASE_URL}/meldungen/",
                f"{self.BASE_URL}/architektur-news/",
            ]
            
            for url in urls:
                try:
                    async with self.session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'lxml')
                            
                            articles = soup.select('article, .news-item, .meldung, .teaser')
                            
                            for article in articles[:max_results]:
                                item = self._parse_article(article)
                                if item:
                                    news.append(item)
                except Exception as e:
                    logger.warning(f"Error fetching {url}: {e}")
                    
        except Exception as e:
            logger.error(f"BauNetz scraping error: {e}")
        
        return news[:max_results]
    
    def _parse_article(self, article) -> Optional[Dict]:
        """Parse a single news article"""
        title_elem = article.select_one('h2, h3, h4, .title, a')
        if not title_elem:
            return None
        
        title = self.clean_text(title_elem.get_text())
        if not title or len(title) < 10:
            return None
        
        # Get summary
        summary = ""
        summary_elem = article.select_one('p, .summary, .teaser-text, .abstract')
        if summary_elem:
            summary = self.clean_text(summary_elem.get_text())[:500]
        
        # Get link
        link = ""
        link_elem = article.select_one('a[href]')
        if link_elem:
            href = link_elem.get('href', '')
            if href.startswith('/'):
                link = f"{self.BASE_URL}{href}"
            elif href.startswith('http'):
                link = href
        
        # Get date
        date_elem = article.select_one('time, .date, .datum')
        published_at = self.parse_german_date(date_elem.get_text() if date_elem else "")
        
        relevance = self.calculate_relevance(title, summary)
        category = self.categorize_news(title, summary)
        
        return {
            "title": title,
            "summary": summary or f"Architektur- und Baunachrichten: {title}",
            "source": "BauNetz",
            "url": link or self.BASE_URL,
            "published_at": published_at,
            "category": category,
            "relevance_score": relevance,
            "scraped_at": datetime.utcnow(),
            "source_id": self.generate_news_id(title, "baunetz"),
        }


class ImmobilienZeitungScraper(NewsScraperBase):
    """Scraper for Immobilien Zeitung - Real Estate News"""
    
    BASE_URL = "https://www.iz.de"
    
    async def scrape(self, max_results: int = 20) -> List[Dict]:
        """Scrape news from Immobilien Zeitung"""
        news = []
        
        try:
            urls = [
                f"{self.BASE_URL}/news/",
                f"{self.BASE_URL}/projekte/",
            ]
            
            for url in urls:
                try:
                    async with self.session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'lxml')
                            
                            articles = soup.select('article, .teaser, .news-item, .list-item')
                            
                            for article in articles[:max_results]:
                                item = self._parse_article(article)
                                if item:
                                    news.append(item)
                except Exception as e:
                    logger.warning(f"Error fetching {url}: {e}")
                    
        except Exception as e:
            logger.error(f"Immobilien Zeitung scraping error: {e}")
        
        return news[:max_results]
    
    def _parse_article(self, article) -> Optional[Dict]:
        """Parse a single news article"""
        title_elem = article.select_one('h2, h3, h4, .title, a')
        if not title_elem:
            return None
        
        title = self.clean_text(title_elem.get_text())
        if not title or len(title) < 10:
            return None
        
        summary = ""
        summary_elem = article.select_one('p, .summary, .teaser-text')
        if summary_elem:
            summary = self.clean_text(summary_elem.get_text())[:500]
        
        link = ""
        link_elem = article.select_one('a[href]')
        if link_elem:
            href = link_elem.get('href', '')
            if href.startswith('/'):
                link = f"{self.BASE_URL}{href}"
            elif href.startswith('http'):
                link = href
        
        date_elem = article.select_one('time, .date')
        published_at = self.parse_german_date(date_elem.get_text() if date_elem else "")
        
        relevance = self.calculate_relevance(title, summary)
        category = self.categorize_news(title, summary)
        
        return {
            "title": title,
            "summary": summary or f"Immobilien Nachrichten: {title}",
            "source": "Immobilien Zeitung",
            "url": link or self.BASE_URL,
            "published_at": published_at,
            "category": category,
            "relevance_score": relevance,
            "scraped_at": datetime.utcnow(),
            "source_id": self.generate_news_id(title, "iz"),
        }


class DBZScraper(NewsScraperBase):
    """Scraper for DBZ (Deutsche BauZeitschrift)"""
    
    BASE_URL = "https://www.dbz.de"
    
    async def scrape(self, max_results: int = 20) -> List[Dict]:
        """Scrape news from DBZ"""
        news = []
        
        try:
            async with self.session.get(
                f"{self.BASE_URL}/news/",
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    articles = soup.select('article, .news-item, .teaser')
                    
                    for article in articles[:max_results]:
                        item = self._parse_article(article)
                        if item:
                            news.append(item)
                            
        except Exception as e:
            logger.error(f"DBZ scraping error: {e}")
        
        return news
    
    def _parse_article(self, article) -> Optional[Dict]:
        """Parse article from DBZ"""
        title_elem = article.select_one('h2, h3, h4, .title, a')
        if not title_elem:
            return None
        
        title = self.clean_text(title_elem.get_text())
        if not title or len(title) < 10:
            return None
        
        summary = ""
        summary_elem = article.select_one('p, .summary')
        if summary_elem:
            summary = self.clean_text(summary_elem.get_text())[:500]
        
        link = ""
        link_elem = article.select_one('a[href]')
        if link_elem:
            href = link_elem.get('href', '')
            if href.startswith('/'):
                link = f"{self.BASE_URL}{href}"
            elif href.startswith('http'):
                link = href
        
        relevance = self.calculate_relevance(title, summary)
        category = self.categorize_news(title, summary)
        
        return {
            "title": title,
            "summary": summary or f"Bauzeitschrift: {title}",
            "source": "Deutsche BauZeitschrift",
            "url": link or self.BASE_URL,
            "published_at": datetime.utcnow(),
            "category": category,
            "relevance_score": relevance,
            "scraped_at": datetime.utcnow(),
            "source_id": self.generate_news_id(title, "dbz"),
        }


class HandelsblattScraper(NewsScraperBase):
    """Scraper for Handelsblatt Immobilien Section"""
    
    BASE_URL = "https://www.handelsblatt.com"
    
    async def scrape(self, max_results: int = 15) -> List[Dict]:
        """Scrape construction/real estate news from Handelsblatt"""
        news = []
        
        try:
            urls = [
                f"{self.BASE_URL}/finanzen/immobilien/",
                f"{self.BASE_URL}/unternehmen/industrie/bauindustrie/",
            ]
            
            for url in urls:
                try:
                    async with self.session.get(
                        url,
                        timeout=aiohttp.ClientTimeout(total=30)
                    ) as response:
                        if response.status == 200:
                            html = await response.text()
                            soup = BeautifulSoup(html, 'lxml')
                            
                            articles = soup.select('article, .vhb-teaser, .teaser')
                            
                            for article in articles[:max_results]:
                                item = self._parse_article(article)
                                if item:
                                    news.append(item)
                except Exception as e:
                    logger.warning(f"Error fetching {url}: {e}")
                    
        except Exception as e:
            logger.error(f"Handelsblatt scraping error: {e}")
        
        return news[:max_results]
    
    def _parse_article(self, article) -> Optional[Dict]:
        """Parse article from Handelsblatt"""
        title_elem = article.select_one('h2, h3, h4, .vhb-teaser__headline, a')
        if not title_elem:
            return None
        
        title = self.clean_text(title_elem.get_text())
        if not title or len(title) < 10:
            return None
        
        summary = ""
        summary_elem = article.select_one('p, .vhb-teaser__summary')
        if summary_elem:
            summary = self.clean_text(summary_elem.get_text())[:500]
        
        link = ""
        link_elem = article.select_one('a[href]')
        if link_elem:
            href = link_elem.get('href', '')
            if href.startswith('/'):
                link = f"{self.BASE_URL}{href}"
            elif href.startswith('http'):
                link = href
        
        relevance = self.calculate_relevance(title, summary)
        category = self.categorize_news(title, summary)
        
        return {
            "title": title,
            "summary": summary or f"Wirtschaftsnachrichten: {title}",
            "source": "Handelsblatt",
            "url": link or self.BASE_URL,
            "published_at": datetime.utcnow(),
            "category": category,
            "relevance_score": relevance,
            "scraped_at": datetime.utcnow(),
            "source_id": self.generate_news_id(title, "handelsblatt"),
        }


class BaublattScraper(NewsScraperBase):
    """Scraper for Baublatt - Swiss/German Construction News"""
    
    BASE_URL = "https://www.baublatt.de"
    
    async def scrape(self, max_results: int = 15) -> List[Dict]:
        """Scrape news from Baublatt"""
        news = []
        
        try:
            async with self.session.get(
                self.BASE_URL,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    articles = soup.select('article, .news-item, .teaser, .post')
                    
                    for article in articles[:max_results]:
                        item = self._parse_article(article)
                        if item:
                            news.append(item)
                            
        except Exception as e:
            logger.error(f"Baublatt scraping error: {e}")
        
        return news
    
    def _parse_article(self, article) -> Optional[Dict]:
        """Parse article from Baublatt"""
        title_elem = article.select_one('h2, h3, h4, .title, a')
        if not title_elem:
            return None
        
        title = self.clean_text(title_elem.get_text())
        if not title or len(title) < 10:
            return None
        
        summary = ""
        summary_elem = article.select_one('p, .excerpt, .summary')
        if summary_elem:
            summary = self.clean_text(summary_elem.get_text())[:500]
        
        link = ""
        link_elem = article.select_one('a[href]')
        if link_elem:
            href = link_elem.get('href', '')
            if href.startswith('/'):
                link = f"{self.BASE_URL}{href}"
            elif href.startswith('http'):
                link = href
        
        relevance = self.calculate_relevance(title, summary)
        category = self.categorize_news(title, summary)
        
        return {
            "title": title,
            "summary": summary or f"Baunachrichten: {title}",
            "source": "Baublatt",
            "url": link or self.BASE_URL,
            "published_at": datetime.utcnow(),
            "category": category,
            "relevance_score": relevance,
            "scraped_at": datetime.utcnow(),
            "source_id": self.generate_news_id(title, "baublatt"),
        }


class PropertyMagazineScraper(NewsScraperBase):
    """Scraper for Property Magazine"""
    
    BASE_URL = "https://www.property-magazine.de"
    
    async def scrape(self, max_results: int = 15) -> List[Dict]:
        """Scrape news from Property Magazine"""
        news = []
        
        try:
            async with self.session.get(
                f"{self.BASE_URL}/news/",
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status == 200:
                    html = await response.text()
                    soup = BeautifulSoup(html, 'lxml')
                    
                    articles = soup.select('article, .news-item, .teaser')
                    
                    for article in articles[:max_results]:
                        item = self._parse_article(article)
                        if item:
                            news.append(item)
                            
        except Exception as e:
            logger.error(f"Property Magazine scraping error: {e}")
        
        return news
    
    def _parse_article(self, article) -> Optional[Dict]:
        """Parse article"""
        title_elem = article.select_one('h2, h3, h4, .title, a')
        if not title_elem:
            return None
        
        title = self.clean_text(title_elem.get_text())
        if not title or len(title) < 10:
            return None
        
        summary = ""
        summary_elem = article.select_one('p, .summary')
        if summary_elem:
            summary = self.clean_text(summary_elem.get_text())[:500]
        
        link = ""
        link_elem = article.select_one('a[href]')
        if link_elem:
            href = link_elem.get('href', '')
            if href.startswith('/'):
                link = f"{self.BASE_URL}{href}"
            elif href.startswith('http'):
                link = href
        
        relevance = self.calculate_relevance(title, summary)
        category = self.categorize_news(title, summary)
        
        return {
            "title": title,
            "summary": summary or f"Immobilien News: {title}",
            "source": "Property Magazine",
            "url": link or self.BASE_URL,
            "published_at": datetime.utcnow(),
            "category": category,
            "relevance_score": relevance,
            "scraped_at": datetime.utcnow(),
            "source_id": self.generate_news_id(title, "propertymag"),
        }


async def scrape_all_news(max_per_source: int = 15) -> List[Dict]:
    """Scrape news from all available sources"""
    all_news = []
    
    scrapers = [
        ("BauNetz", BauNetzScraper),
        ("Immobilien Zeitung", ImmobilienZeitungScraper),
        ("Deutsche BauZeitschrift", DBZScraper),
        ("Handelsblatt", HandelsblattScraper),
        ("Baublatt", BaublattScraper),
        ("Property Magazine", PropertyMagazineScraper),
    ]
    
    for name, ScraperClass in scrapers:
        try:
            async with ScraperClass() as scraper:
                news = await scraper.scrape(max_per_source)
                all_news.extend(news)
                logger.info(f"Scraped {len(news)} articles from {name}")
        except Exception as e:
            logger.error(f"{name} scraping failed: {e}")
    
    # Deduplicate by source_id
    seen = set()
    unique_news = []
    for article in all_news:
        source_id = article.get('source_id', '')
        if source_id and source_id not in seen:
            seen.add(source_id)
            unique_news.append(article)
        elif not source_id:
            unique_news.append(article)
    
    # Sort by relevance score
    unique_news.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    logger.info(f"Total unique news articles scraped: {len(unique_news)}")
    return unique_news


if __name__ == "__main__":
    # Test scraping
    async def test():
        news = await scrape_all_news(max_per_source=5)
        for n in news[:10]:
            print(f"- [{n['source']}] {n['title'][:50]}... (relevance: {n['relevance_score']})")
    
    asyncio.run(test())
