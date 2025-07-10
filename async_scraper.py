"""
Async scraping utilities for improved performance and concurrency
"""
import asyncio
import aiohttp
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import random
import time
from concurrent.futures import ThreadPoolExecutor
from playwright.async_api import async_playwright

from models import ContentData, KeywordData
from utils import retry_on_failure, PerformanceMonitor
from config import config

logger = logging.getLogger(__name__)

class AsyncBrowserManager:
    """Async browser manager for concurrent scraping"""
    
    def __init__(self, max_contexts: int = 5):
        self.max_contexts = max_contexts
        self.playwright = None
        self.browser = None
        self.contexts = []
        self.semaphore = asyncio.Semaphore(max_contexts)
        
    async def __aenter__(self):
        await self.start()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def start(self):
        """Initialize browser and contexts"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=config.headless,
                args=[
                    '--no-sandbox',
                    '--disable-blink-features=AutomationControlled',
                    '--disable-extensions',
                    '--disable-dev-shm-usage'
                ]
            )
            logger.info(f"Async browser manager started with {self.max_contexts} contexts")
        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            raise
    
    async def get_context(self):
        """Get a browser context with semaphore protection"""
        async with self.semaphore:
            try:
                context = await self.browser.new_context(
                    user_agent=random.choice(config.user_agents),
                    viewport={'width': 1920, 'height': 1080}
                )
                
                # Add stealth scripts
                await context.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                """)
                
                return context
            except Exception as e:
                logger.error(f"Failed to create context: {e}")
                return None
    
    async def close(self):
        """Close all contexts and browser"""
        try:
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            logger.info("Async browser manager closed")
        except Exception as e:
            logger.error(f"Error closing browser: {e}")

class AsyncHTTPClient:
    """Async HTTP client with enhanced error handling and rate limiting"""
    
    def __init__(self, max_concurrent: int = 10, rate_limit: float = 1.0):
        self.max_concurrent = max_concurrent
        self.rate_limit = rate_limit
        self.session = None
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.last_request_time = 0
        
    async def __aenter__(self):
        connector = aiohttp.TCPConnector(
            limit=self.max_concurrent,
            limit_per_host=5,
            ttl_dns_cache=300,
            use_dns_cache=True
        )
        
        timeout = aiohttp.ClientTimeout(total=config.timeout)
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                'User-Agent': random.choice(config.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get(self, url: str, **kwargs) -> Optional[aiohttp.ClientResponse]:
        """Rate-limited async GET request"""
        async with self.semaphore:
            # Rate limiting
            current_time = time.time()
            time_since_last = current_time - self.last_request_time
            if time_since_last < self.rate_limit:
                await asyncio.sleep(self.rate_limit - time_since_last)
            
            try:
                async with self.session.get(url, **kwargs) as response:
                    self.last_request_time = time.time()
                    if response.status == 200:
                        return response
                    else:
                        logger.warning(f"HTTP {response.status} for {url}")
                        return None
            except asyncio.TimeoutError:
                logger.error(f"Timeout for {url}")
                return None
            except Exception as e:
                logger.error(f"Request error for {url}: {e}")
                return None

class AsyncContentAnalyzer:
    """Async content analyzer for concurrent content processing"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.performance_monitor = PerformanceMonitor()
    
    async def analyze_multiple_urls(self, urls: List[str], 
                                  target_keywords: List[str] = None) -> List[Optional[ContentData]]:
        """Analyze multiple URLs concurrently"""
        self.performance_monitor.start_timer("bulk_content_analysis")
        
        async with AsyncHTTPClient() as client:
            tasks = [
                self._analyze_single_url(client, url, target_keywords) 
                for url in urls
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and None results
        valid_results = [r for r in results if isinstance(r, ContentData)]
        
        self.performance_monitor.end_timer("bulk_content_analysis")
        logger.info(f"Analyzed {len(valid_results)} out of {len(urls)} URLs successfully")
        
        return valid_results
    
    async def _analyze_single_url(self, client: AsyncHTTPClient, url: str, 
                                target_keywords: List[str] = None) -> Optional[ContentData]:
        """Analyze a single URL asynchronously"""
        try:
            # Check cache first
            cached_data = self.db_manager.get_cached_content_data(url)
            if cached_data:
                return cached_data
            
            response = await client.get(url)
            if not response:
                return None
            
            content = await response.text()
            
            # Process content in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                content_data = await loop.run_in_executor(
                    executor, 
                    self._process_content_sync, 
                    content, url, target_keywords
                )
            
            if content_data:
                # Save to database in thread pool
                await loop.run_in_executor(
                    executor,
                    self.db_manager.save_content_data,
                    content_data
                )
            
            return content_data
            
        except Exception as e:
            logger.error(f"Error analyzing {url}: {e}")
            return None
    
    def _process_content_sync(self, content: str, url: str, 
                            target_keywords: List[str] = None) -> Optional[ContentData]:
        """Process content synchronously (runs in thread pool)"""
        try:
            from bs4 import BeautifulSoup
            from utils import safe_extract_text, clean_text
            
            soup = BeautifulSoup(content, 'html.parser')
            
            # Extract basic data
            title = safe_extract_text(soup.find('title'), "No Title")
            meta_desc = safe_extract_text(
                soup.find('meta', attrs={'name': 'description'}), 
                "No Meta Description"
            )
            
            # Extract headings
            h1_tags = [safe_extract_text(h1) for h1 in soup.find_all('h1')]
            h2_tags = [safe_extract_text(h2) for h2 in soup.find_all('h2')]
            h3_tags = [safe_extract_text(h3) for h3 in soup.find_all('h3')]
            
            # Get clean text
            for script in soup(["script", "style"]):
                script.decompose()
            
            text = soup.get_text()
            clean_content = clean_text(text)
            word_count = len(clean_content.split())
            
            # Calculate keyword density
            keyword_density = {}
            if target_keywords:
                for keyword in target_keywords:
                    keyword_count = clean_content.lower().count(keyword.lower())
                    density = (keyword_count / word_count) * 100 if word_count > 0 else 0
                    keyword_density[keyword] = round(density, 2)
            
            # Basic mobile-friendly check
            mobile_friendly = bool(soup.find('meta', attrs={'name': 'viewport'}))
            
            return ContentData(
                title=title,
                url=url,
                meta_description=meta_desc,
                h1_tags=h1_tags,
                h2_tags=h2_tags,
                h3_tags=h3_tags,
                word_count=word_count,
                keyword_density=keyword_density,
                reading_score=0.0,  # Calculate separately if needed
                internal_links=[],  # Extract separately if needed
                external_links=[],  # Extract separately if needed
                images=[],  # Extract separately if needed
                schema_markup=[],  # Extract separately if needed
                page_speed_score=80.0,  # Default value
                mobile_friendly=mobile_friendly,
                timestamp=datetime.now().isoformat()
            )
            
        except Exception as e:
            logger.error(f"Error processing content for {url}: {e}")
            return None

class AsyncKeywordAnalyzer:
    """Async keyword analyzer for bulk keyword research"""
    
    def __init__(self, db_manager, browser_manager: AsyncBrowserManager):
        self.db_manager = db_manager
        self.browser_manager = browser_manager
        self.performance_monitor = PerformanceMonitor()
    
    async def analyze_multiple_keywords(self, keywords: List[str]) -> List[Optional[KeywordData]]:
        """Analyze multiple keywords concurrently"""
        self.performance_monitor.start_timer("bulk_keyword_analysis")
        
        # Limit concurrent browser operations
        semaphore = asyncio.Semaphore(3)  # Max 3 concurrent browser operations
        
        tasks = [
            self._analyze_single_keyword_with_semaphore(semaphore, keyword) 
            for keyword in keywords
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and None results
        valid_results = [r for r in results if isinstance(r, KeywordData)]
        
        self.performance_monitor.end_timer("bulk_keyword_analysis")
        logger.info(f"Analyzed {len(valid_results)} out of {len(keywords)} keywords successfully")
        
        return valid_results
    
    async def _analyze_single_keyword_with_semaphore(self, semaphore: asyncio.Semaphore, 
                                                   keyword: str) -> Optional[KeywordData]:
        """Analyze a single keyword with semaphore protection"""
        async with semaphore:
            return await self._analyze_single_keyword(keyword)
    
    async def _analyze_single_keyword(self, keyword: str) -> Optional[KeywordData]:
        """Analyze a single keyword asynchronously"""
        try:
            # Check cache first
            cached_data = self.db_manager.get_cached_keyword_data(keyword)
            if cached_data:
                return cached_data
            
            context = await self.browser_manager.get_context()
            if not context:
                return None
            
            try:
                page = await context.new_page()
                
                # Navigate to Google search
                search_url = f"https://www.google.com/search?q={keyword.replace(' ', '+')}&gl=us&hl=en"
                await page.goto(search_url, wait_until="networkidle")
                
                # Extract data (simplified for async example)
                related_keywords = await self._extract_related_keywords_async(page)
                search_volume = await self._estimate_search_volume_async(page)
                competition = await self._estimate_competition_async(page)
                
                keyword_data = KeywordData(
                    keyword=keyword,
                    search_volume=search_volume,
                    competition=competition,
                    difficulty_score=50,  # Calculate separately
                    related_keywords=related_keywords,
                    people_also_ask=[],  # Extract separately
                    featured_snippet="",  # Extract separately
                    local_pack=[],  # Extract separately
                    timestamp=datetime.now().isoformat()
                )
                
                # Save to database in thread pool
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor() as executor:
                    await loop.run_in_executor(
                        executor,
                        self.db_manager.save_keyword_data,
                        keyword_data
                    )
                
                return keyword_data
                
            finally:
                await context.close()
                
        except Exception as e:
            logger.error(f"Error analyzing keyword '{keyword}': {e}")
            return None
    
    async def _extract_related_keywords_async(self, page) -> List[str]:
        """Extract related keywords asynchronously"""
        try:
            # Simplified extraction for demo
            elements = await page.query_selector_all("div[data-ved] a[href*='search']")
            keywords = []
            
            for element in elements[:10]:  # Limit to first 10
                text = await element.inner_text()
                if text and len(text) > 3:
                    keywords.append(text.strip())
            
            return keywords
        except Exception as e:
            logger.debug(f"Error extracting related keywords: {e}")
            return []
    
    async def _estimate_search_volume_async(self, page) -> str:
        """Estimate search volume asynchronously"""
        try:
            stats_element = await page.query_selector("#result-stats")
            if stats_element:
                stats_text = await stats_element.inner_text()
                return stats_text.split("(")[0].strip() if "results" in stats_text.lower() else "Unknown"
            return "Unknown"
        except Exception:
            return "Unknown"
    
    async def _estimate_competition_async(self, page) -> str:
        """Estimate competition asynchronously"""
        try:
            ads = await page.query_selector_all("div[data-text-ad]")
            ad_count = len(ads)
            
            if ad_count > 4:
                return "High"
            elif ad_count > 2:
                return "Medium"
            else:
                return "Low"
        except Exception:
            return "Unknown"

# Batch processing utilities
class BatchProcessor:
    """Utility class for processing large datasets in batches"""
    
    @staticmethod
    async def process_in_batches(items: List[Any], batch_size: int, 
                               processor_func, *args, **kwargs) -> List[Any]:
        """Process items in batches to manage memory and rate limits"""
        results = []
        
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            logger.info(f"Processing batch {i//batch_size + 1} of {(len(items)-1)//batch_size + 1}")
            
            batch_results = await processor_func(batch, *args, **kwargs)
            results.extend(batch_results)
            
            # Small delay between batches
            await asyncio.sleep(1)
        
        return results

# Example usage function
async def example_async_scraping():
    """Example of how to use async scraping capabilities"""
    from database import DatabaseManager
    
    db_manager = DatabaseManager("async_test.db")
    
    # Example: Analyze multiple URLs concurrently
    urls = [
        "https://example.com",
        "https://httpbin.org/html",
        "https://httpbin.org/json"
    ]
    
    content_analyzer = AsyncContentAnalyzer(db_manager)
    content_results = await content_analyzer.analyze_multiple_urls(urls)
    
    print(f"Analyzed {len(content_results)} URLs")
    
    # Example: Analyze multiple keywords concurrently
    async with AsyncBrowserManager() as browser_manager:
        keyword_analyzer = AsyncKeywordAnalyzer(db_manager, browser_manager)
        keywords = ["python programming", "web scraping", "seo tools"]
        
        keyword_results = await keyword_analyzer.analyze_multiple_keywords(keywords)
        print(f"Analyzed {len(keyword_results)} keywords")

if __name__ == "__main__":
    asyncio.run(example_async_scraping())
