"""
Browser utilities for SEO Scraper
"""
import random
import time
import logging
from playwright.async_api import async_playwright
from typing import Tuple, Any
from config import config

logger = logging.getLogger(__name__)

class BrowserManager:
    """Manages browser contexts and stealth features for web scraping"""
    
    def __init__(self, scraper_config=None):
        self.config = scraper_config or config
    
async def get_browser_context(self, stealth_mode: bool = True) -> Tuple[Any, Any, Any]:
        """Create an enhanced browser context with stealth features"""
        
playwright = await async_playwright().start()
browser = await playwright.chromium.launch(
            headless=self.config.headless,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-extensions',
                '--disable-dev-shm-usage',
                '--disable-features=VizDisplayCompositor',
                '--disable-background-networking',
                '--disable-default-apps',
                '--disable-sync',
                '--disable-translate',
                '--hide-scrollbars',
                '--metrics-recording-only',
                '--mute-audio',
                '--no-first-run',
                '--safebrowsing-disable-auto-update',
                '--password-store=basic',
                '--use-mock-keychain'
            ]
        )
        
context = await browser.new_context(
            user_agent=random.choice(self.config.user_agents),
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York',
            geolocation={'longitude': -74.0, 'latitude': 40.7},
            permissions=['geolocation']
        )
        
        if stealth_mode:
            # Add stealth scripts
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined,
                });
                Object.defineProperty(navigator, 'plugins', {
                    get: () => [1, 2, 3, 4, 5],
                });
                Object.defineProperty(navigator, 'languages', {
                    get: () => ['en-US', 'en'],
                });
                window.chrome = {
                    runtime: {},
                };
            """)
        
await context.set_extra_http_headers({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Cache-Control': 'max-age=0'
        })
        
        logger.info("Browser context created successfully")
        return playwright, browser, context
    
    def random_delay(self, min_delay: float = None, max_delay: float = None):
        """Add random delay between requests"""
        min_delay = min_delay or self.config.min_delay
        max_delay = max_delay or self.config.max_delay
        delay = random.uniform(min_delay, max_delay)
        time.sleep(delay)
        logger.debug(f"Added delay of {delay:.2f} seconds")
    
async def navigate_safely(self, page, url: str, wait_for: str = "networkidle"):
        """Navigate to a URL with error handling and delays"""
        try:
            self.random_delay()
await page.goto(url, wait_until=wait_for, timeout=self.config.timeout * 1000)
            self.random_delay(1, 2)  # Additional delay after navigation
            logger.info(f"Successfully navigated to: {url}")
            return True
        except Exception as e:
            logger.error(f"Error navigating to {url}: {e}")
            return False
    
async def scroll_page(self, page, scroll_count: int = 3):
        """Scroll the page to simulate human behavior"""
        try:
            for i in range(scroll_count):
                scroll_position = (i + 1) * (100 / scroll_count)
await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {scroll_position / 100})")
                self.random_delay(0.5, 1.5)
            logger.debug(f"Scrolled page {scroll_count} times")
        except Exception as e:
            logger.error(f"Error scrolling page: {e}")
    
async def close_browser_context(self, playwright, browser):
        """Safely close browser and playwright"""
        try:
await browser.close()
await playwright.stop()
            logger.info("Browser context closed successfully")
        except Exception as e:
            logger.error(f"Error closing browser context: {e}")

# Convenience function for getting browser context
def get_browser_context(stealth_mode: bool = True):
    """Get a browser context with default settings"""
    manager = BrowserManager()
    return manager.get_browser_context(stealth_mode)
