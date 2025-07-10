"""
Keyword research and analysis module for SEO Scraper
"""

import urllib.parse
import time
import random
import logging
from typing import List, Optional
from datetime import datetime

from models import KeywordData
from browser_utils import BrowserManager
from database import DatabaseManager
from config import config

logger = logging.getLogger(__name__)


class KeywordScraper:
    """Handles keyword research and SERP analysis"""

    def __init__(self, db_manager: DatabaseManager, browser_manager: BrowserManager = None):
        self.db_manager = db_manager
        self.browser_manager = browser_manager or BrowserManager()

    async def scrape_google_keywords_enhanced(self, keyword: str, location: str = "United States") -> Optional[KeywordData]:
        """Enhanced keyword scraping with comprehensive data points"""
        logger.info(f"Researching keyword: {keyword}")

        # Check cache first
        cached_data = self.db_manager.get_cached_keyword_data(keyword)
        if cached_data:
            logger.info("Using cached keyword data")
            return cached_data

        playwright, browser, context = await self.browser_manager.get_browser_context()
        page = await context.new_page()

        try:
            query = urllib.parse.quote_plus(keyword)
            url = f"https://www.google.com/search?q={query}&gl=us&hl=en"

            if not await self.browser_manager.navigate_safely(page, "https://www.google.com"):
                return None

            if not await self.browser_manager.navigate_safely(page, url):
                return None

            # Extract enhanced data
            related_keywords = await self._extract_related_keywords(page)
            people_also_ask = await self._extract_people_also_ask(page)
            featured_snippet = await self._extract_featured_snippet(page)
            local_pack = await self._extract_local_pack(page)

            search_volume = self._estimate_search_volume(page)
            competition = self._estimate_competition(page)
            difficulty_score = self._calculate_difficulty_score(page, keyword)

            keyword_data = KeywordData(
                keyword=keyword,
                search_volume=search_volume,
                competition=competition,
                difficulty_score=difficulty_score,
                related_keywords=related_keywords,
                people_also_ask=people_also_ask,
                featured_snippet=featured_snippet,
                local_pack=local_pack,
                timestamp=datetime.now().isoformat()
            )

            self.db_manager.save_keyword_data(keyword_data)

            logger.info(f"Found {len(related_keywords)} related keywords and {len(people_also_ask)} PAA questions")
            return keyword_data

        except Exception as e:
            logger.error(f"Error scraping keyword '{keyword}': {e}")
            return None
        finally:
            await self.browser_manager.close_browser_context(playwright, browser)

    async def _extract_related_keywords(self, page) -> List[str]:
        """Extract related keywords with multiple strategies"""
        related_keywords = []

        try:
            await self.browser_manager.scroll_page(page)

            selectors = [
                "div[data-ved] a[href*='search']",
                "div[jsname] a[href*='search']",
                "div[class*='related'] a",
                "table[class*='related'] a",
                "div[class*='brs_col'] a"
            ]

            for selector in selectors:
                try:
                    elements = page.locator(selector)
                    count = min(await elements.count(), 12)
                    for i in range(count):
                        text = (await elements.nth(i).inner_text()).strip()
                        if 3 < len(text) < 50 and text not in related_keywords:
                            related_keywords.append(text)
                    if len(related_keywords) >= 10:
                        break
                except Exception as e:
                    logger.debug(f"Error with selector {selector}: {e}")
        except Exception as e:
            logger.error(f"Error extracting related keywords: {e}")

        return related_keywords[:15]

    async def _extract_people_also_ask(self, page) -> List[str]:
        """Extract People Also Ask questions"""
        people_also_ask = []

        try:
            selectors = [
                "div[data-ved] span[role='button']",
                "div[jsname] span[role='button']",
                "div[data-ved] div[role='button']",
                "div[jsname] div[role='button']",
                "div[data-ved] h3"
            ]

            for selector in selectors:
                try:
                    elements = page.locator(selector)
                    count = min(await elements.count(), 10)
                    for i in range(count):
                        text = (await elements.nth(i).inner_text()).strip()
                        if len(text) > 10 and "?" in text and text not in people_also_ask:
                            people_also_ask.append(text)
                    if len(people_also_ask) >= 8:
                        break
                except Exception as e:
                    logger.debug(f"Error with PAA selector {selector}: {e}")
        except Exception as e:
            logger.error(f"Error extracting People Also Ask: {e}")

        return people_also_ask[:10]

    async def _extract_featured_snippet(self, page) -> str:
        """Extract featured snippet content"""
        try:
            selectors = [
                "div[data-ved] div[class*='hgKElc']",
                "div[data-ved] div[class*='LGOjhe']",
                "div[class*='kno-rdesc'] span",
                "div[data-ved] span[class*='hgKElc']"
            ]

            for selector in selectors:
                try:
                    element = page.locator(selector).first
                    if await element.count() > 0:
                        return (await element.inner_text()).strip()
                except Exception as e:
                    logger.debug(f"Error with snippet selector {selector}: {e}")
        except Exception as e:
            logger.error(f"Error extracting featured snippet: {e}")

        return ""

    async def _extract_local_pack(self, page) -> List[str]:
        """Extract local pack results"""
        local_results = []

        try:
            selectors = [
                "div[data-ved] div[class*='rlfl__tls']",
                "div[class*='VkpGBb']",
                "div[data-ved] span[class*='OSrXXb']"
            ]

            for selector in selectors:
                try:
                    elements = page.locator(selector)
                    count = min(await elements.count(), 5)
                    for i in range(count):
                        text = (await elements.nth(i).inner_text()).strip()
                        if len(text) > 5 and text not in local_results:
                            local_results.append(text)
                except Exception as e:
                    logger.debug(f"Error with local selector {selector}: {e}")
        except Exception as e:
            logger.error(f"Error extracting local pack: {e}")

        return local_results

    def _estimate_search_volume(self, page) -> str:
        """Estimate search volume from result stats"""
        try:
            stats = page.locator("#result-stats")
            if stats.count() > 0:
                return stats.inner_text().split("(")[0].strip()
        except Exception as e:
            logger.debug(f"Error estimating search volume: {e}")
        return "Unknown"

    def _estimate_competition(self, page) -> str:
        """Estimate competition level based on ads"""
        try:
            ads = page.locator("div[data-text-ad], div[class*='uEierd']")
            count = ads.count()

            if count > 4:
                return "High"
            elif count > 2:
                return "Medium"
            else:
                return "Low"
        except Exception as e:
            logger.debug(f"Error estimating competition: {e}")
        return "Unknown"

    def _calculate_difficulty_score(self, page, keyword: str) -> int:
        """Calculate keyword difficulty score (1–100)"""
        try:
            score = 0

            # Factor 1: Number of results
            try:
                stats = page.locator("#result-stats")
                if stats.count() > 0:
                    text = stats.inner_text()
                    import re
                    nums = re.findall(r'[\d,]+', text)
                    if nums:
                        results = int(nums[0].replace(",", ""))
                        if results > 100_000_000:
                            score += 30
                        elif results > 10_000_000:
                            score += 20
                        elif results > 1_000_000:
                            score += 10
                        else:
                            score += 5
            except Exception as e:
                logger.debug(f"Error calculating result count factor: {e}")

            # Factor 2: Ads
            try:
                ads = page.locator("div[data-text-ad], div[class*='uEierd']")
                score += min(ads.count() * 15, 45)
            except Exception as e:
                logger.debug(f"Error calculating ad factor: {e}")

            # Factor 3: High-authority domains
            try:
                h3s = page.locator("h3")
                count = min(h3s.count(), 5)
                for i in range(count):
                    try:
                        h3 = h3s.nth(i)
                        parent = h3.locator("xpath=..")
                        link = parent.get_attribute("href")
                        if link:
                            from urllib.parse import urlparse
                            domain = urlparse(link).netloc
                            if any(d in domain for d in ['wikipedia.org', 'youtube.com', 'amazon.com', 'facebook.com']):
                                score += 5
                    except Exception as e:
                        logger.debug(f"Error analyzing domain at index {i}: {e}")
            except Exception as e:
                logger.debug(f"Error calculating domain authority factor: {e}")

            return min(score, 100)
        except Exception as e:
            logger.error(f"Error calculating difficulty score: {e}")
            return 50  # Fallback difficulty
