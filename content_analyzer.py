"""
Content analysis module for SEO Scraper
"""
import requests
import time
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

from models import ContentData, TechnicalSEOData
from database import DatabaseManager
from config import config

# Import for reading score calculation
try:
    from textstat import flesch_reading_ease
except ImportError:
    def flesch_reading_ease(text):
        return 0

logger = logging.getLogger(__name__)

class ContentAnalyzer:
    """Handles content analysis and technical SEO audits"""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    def analyze_content_enhanced(self, url: str, target_keywords: List[str] = None) -> Optional[ContentData]:
        """Enhanced content analysis with comprehensive metrics"""
        logger.info(f"Analyzing content: {url}")
        
        # Check cache
        cached_data = self.db_manager.get_cached_content_data(url)
        if cached_data:
            logger.info("Using cached content data")
            return cached_data
        
        try:
            # Measure page load time
            start_time = time.time()
            response = self.session.get(url, timeout=config.timeout)
            load_time = time.time() - start_time
            
            if response.status_code != 200:
                logger.error(f"HTTP {response.status_code} for {url}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract basic data
            title = self._extract_title(soup)
            meta_desc = self._extract_meta_description(soup)
            
            # Extract heading tags
            h1_tags = [h1.get_text().strip() for h1 in soup.find_all('h1')]
            h2_tags = [h2.get_text().strip() for h2 in soup.find_all('h2')]
            h3_tags = [h3.get_text().strip() for h3 in soup.find_all('h3')]
            
            # Extract links
            internal_links, external_links = self._extract_links(soup, url)
            
            # Extract images
            images = self._extract_images(soup)
            
            # Extract schema markup
            schema_markup = self._extract_schema_markup(soup)
            
            # Get clean text for analysis
            clean_text = self._extract_clean_text(soup)
            
            # Calculate metrics
            word_count = len(clean_text.split())
            reading_score = self._calculate_reading_score(clean_text)
            keyword_density = self._calculate_keyword_density(clean_text, target_keywords or [])
            mobile_friendly = self._check_mobile_friendly(soup)
            page_speed_score = self._calculate_page_speed_score(load_time)
            
            content_data = ContentData(
                title=title,
                url=url,
                meta_description=meta_desc,
                h1_tags=h1_tags,
                h2_tags=h2_tags,
                h3_tags=h3_tags,
                word_count=word_count,
                keyword_density=keyword_density,
                reading_score=reading_score,
                internal_links=internal_links,
                external_links=external_links,
                images=images,
                schema_markup=schema_markup,
                page_speed_score=page_speed_score,
                mobile_friendly=mobile_friendly,
                timestamp=datetime.now().isoformat()
            )
            
            # Save to database
            self.db_manager.save_content_data(content_data)
            
            logger.info(f"Analyzed {word_count} words, {len(internal_links)} internal links, {len(external_links)} external links")
            return content_data
            
        except Exception as e:
            logger.error(f"Error analyzing content: {e}")
            return None
    
    def perform_technical_seo_audit(self, url: str) -> Optional[TechnicalSEOData]:
        """Perform comprehensive technical SEO audit"""
        logger.info(f"Performing technical SEO audit: {url}")
        
        try:
            start_time = time.time()
            response = self.session.get(url, timeout=config.timeout)
            load_time = time.time() - start_time
            
            if response.status_code != 200:
                logger.error(f"HTTP {response.status_code} for {url}")
                return None
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Extract technical SEO elements
            page_title = self._extract_title(soup)
            meta_description = self._extract_meta_description(soup)
            canonical_url = self._extract_canonical_url(soup)
            robots_meta = self._extract_robots_meta(soup)
            
            # Count elements
            h1_count = len(soup.find_all('h1'))
            h2_count = len(soup.find_all('h2'))
            
            # Count links
            internal_links_count, external_links_count = self._count_links(soup, url)
            
            # Images without alt text
            images_without_alt = self._count_images_without_alt(soup)
            
            # Technical checks
            mobile_friendly = self._check_mobile_friendly(soup)
            ssl_certificate = url.startswith('https://')
            structured_data = self._extract_structured_data_types(soup)
            
            technical_data = TechnicalSEOData(
                url=url,
                page_title=page_title,
                meta_description=meta_description,
                canonical_url=canonical_url,
                robots_meta=robots_meta,
                h1_count=h1_count,
                h2_count=h2_count,
                internal_links_count=internal_links_count,
                external_links_count=external_links_count,
                images_without_alt=images_without_alt,
                page_load_time=load_time,
                mobile_friendly=mobile_friendly,
                ssl_certificate=ssl_certificate,
                structured_data=structured_data,
                timestamp=datetime.now().isoformat()
            )
            
            # Save to database
            self.db_manager.save_technical_seo_data(technical_data)
            
            logger.info(f"Technical audit completed. Found {h1_count} H1 tags, {images_without_alt} images without alt text")
            return technical_data
            
        except Exception as e:
            logger.error(f"Error performing technical SEO audit: {e}")
            return None
    
    def _extract_title(self, soup) -> str:
        """Extract page title"""
        title = soup.find('title')
        return title.get_text().strip() if title else "No Title"
    
    def _extract_meta_description(self, soup) -> str:
        """Extract meta description"""
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        return meta_desc.get('content', '').strip() if meta_desc else "No Meta Description"
    
    def _extract_canonical_url(self, soup) -> str:
        """Extract canonical URL"""
        canonical = soup.find('link', rel='canonical')
        return canonical.get('href', '') if canonical else ""
    
    def _extract_robots_meta(self, soup) -> str:
        """Extract robots meta tag"""
        robots_meta = soup.find('meta', attrs={'name': 'robots'})
        return robots_meta.get('content', '') if robots_meta else ""
    
    def _extract_links(self, soup, base_url: str) -> tuple:
        """Extract internal and external links"""
        internal_links = []
        external_links = []
        domain = urlparse(base_url).netloc
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('http'):
                if domain in href:
                    internal_links.append(href)
                else:
                    external_links.append(href)
            elif href.startswith('/'):
                internal_links.append(urljoin(base_url, href))
        
        return internal_links, external_links
    
    def _count_links(self, soup, base_url: str) -> tuple:
        """Count internal and external links"""
        internal_count = 0
        external_count = 0
        domain = urlparse(base_url).netloc
        
        for link in soup.find_all('a', href=True):
            href = link['href']
            if href.startswith('http'):
                if domain in href:
                    internal_count += 1
                else:
                    external_count += 1
            elif href.startswith('/'):
                internal_count += 1
        
        return internal_count, external_count
    
    def _extract_images(self, soup) -> List[Dict[str, str]]:
        """Extract image information"""
        images = []
        for img in soup.find_all('img'):
            img_data = {
                'src': img.get('src', ''),
                'alt': img.get('alt', ''),
                'title': img.get('title', '')
            }
            images.append(img_data)
        return images
    
    def _count_images_without_alt(self, soup) -> int:
        """Count images without alt text"""
        return len([img for img in soup.find_all('img') if not img.get('alt')])
    
    def _extract_schema_markup(self, soup) -> List[str]:
        """Extract schema markup types"""
        schema_markup = []
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                schema_data = json.loads(script.string)
                if isinstance(schema_data, dict) and '@type' in schema_data:
                    schema_markup.append(schema_data['@type'])
                elif isinstance(schema_data, list):
                    for item in schema_data:
                        if isinstance(item, dict) and '@type' in item:
                            schema_markup.append(item['@type'])
            except:
                continue
        return schema_markup
    
    def _extract_structured_data_types(self, soup) -> List[str]:
        """Extract structured data types"""
        return self._extract_schema_markup(soup)
    
    def _extract_clean_text(self, soup) -> str:
        """Extract clean text content"""
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        text = soup.get_text()
        
        # Clean text
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = ' '.join(chunk for chunk in chunks if chunk)
        
        return text
    
    def _calculate_reading_score(self, text: str) -> float:
        """Calculate reading ease score"""
        try:
            return flesch_reading_ease(text)
        except:
            return 0.0
    
    def _calculate_keyword_density(self, text: str, keywords: List[str]) -> Dict[str, float]:
        """Calculate keyword density for target keywords"""
        if not keywords or not text:
            return {}
        
        word_count = len(text.split())
        keyword_density = {}
        
        for keyword in keywords:
            keyword_count = text.lower().count(keyword.lower())
            density = (keyword_count / word_count) * 100 if word_count > 0 else 0
            keyword_density[keyword] = round(density, 2)
        
        return keyword_density
    
    def _check_mobile_friendly(self, soup) -> bool:
        """Check if page has viewport meta tag (basic mobile-friendly check)"""
        return bool(soup.find('meta', attrs={'name': 'viewport'}))
    
    def _calculate_page_speed_score(self, load_time: float) -> float:
        """Calculate page speed score based on load time"""
        if load_time < 1:
            return 100.0
        elif load_time < 3:
            return 80.0
        elif load_time < 5:
            return 60.0
        else:
            return 40.0
