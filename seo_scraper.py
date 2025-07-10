"""
Main SEO Scraper - Orchestrates all scraping modules
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from urllib.parse import urlparse

from config import config
from database import DatabaseManager
from browser_utils import BrowserManager
from keyword_scraper import KeywordScraper
from content_analyzer import ContentAnalyzer
from competitor_analyzer import CompetitorAnalyzer

# Set up logging
logging.basicConfig(
    level=getattr(logging, config.log_level),
    format=config.log_format
)
logger = logging.getLogger(__name__)

class SEOScraper:
    """Main SEO Scraper class that orchestrates all analysis modules"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or config.db_path
        self.db_manager = DatabaseManager(self.db_path)
        self.browser_manager = BrowserManager()
        
        # Initialize analysis modules
        self.keyword_scraper = KeywordScraper(self.db_manager, self.browser_manager)
        self.content_analyzer = ContentAnalyzer(self.db_manager)
        self.competitor_analyzer = CompetitorAnalyzer(self.db_manager, self.browser_manager)
        
        logger.info("SEO Scraper initialized successfully")
    
    def analyze_comprehensive(self, url: str, primary_keyword: str = None) -> Dict[str, Any]:
        """Perform comprehensive analysis of a website"""
        logger.info(f"Starting comprehensive analysis for {url}")
        
        try:
            result = {
                'content_analysis': None,
                'technical_seo': None,
                'keyword_analysis': None,
                'competitor_analysis': None,
                'timestamp': datetime.now().isoformat()
            }
            
            # Analyze content
            if url:
                result['content_analysis'] = self.content_analyzer.analyze_content_enhanced(url)
            
            # Perform technical SEO audit
            if url:
                result['technical_seo'] = self.content_analyzer.perform_technical_seo_audit(url)
            
            # Analyze primary keyword if provided
            if primary_keyword:
                result['keyword_analysis'] = self.keyword_scraper.scrape_google_keywords_enhanced(primary_keyword)
                if result['content_analysis']:
                    # Re-analyze content with better keyword data
                    target_keywords = [primary_keyword]
                    if result['keyword_analysis']:
                        target_keywords.extend(result['keyword_analysis'].related_keywords[:5])
                    
                    result['content_analysis'] = self.content_analyzer.analyze_content_enhanced(
                        url, target_keywords=target_keywords
                    )
            
            # Analyze competitors if we have basic results
            if url and (result['content_analysis'] or result['technical_seo']):
                domain = urlparse(url).netloc.replace('www.', '')
                result['competitor_analysis'] = self.competitor_analyzer.analyze_competitors(domain)
            
            logger.info("Completed comprehensive analysis")
            return result
            
        except Exception as e:
            logger.error(f"Error in comprehensive analysis: {e}")
            return None
    
    def track_keyword_rankings(self, keywords: List[str]) -> bool:
        """Track keyword rankings over time"""
        logger.info(f"Tracking rankings for {len(keywords)} keywords")
        
        try:
            for keyword in keywords:
                self.keyword_scraper.scrape_google_keywords_enhanced(keyword)
            return True
        except Exception as e:
            logger.error(f"Error tracking keyword rankings: {e}")
            return False
    
    def cleanup_old_data(self, days_to_keep: int = 30):
        """Clean up old data from the database"""
        logger.info(f"Cleaning up data older than {days_to_keep} days")
        self.db_manager.cleanup_old_data(days_to_keep)

def main():
    """Example usage of the SEO Scraper"""
    scraper = SEOScraper()
    
    # Example comprehensive analysis
    url = "https://example.com"
    keyword = "example keyword"
    
    results = scraper.analyze_comprehensive(url, keyword)
    
    if results:
        print(f"Analysis completed for {url}")
        print(f"Content analysis: {'✓' if results['content_analysis'] else '✗'}")
        print(f"Technical SEO: {'✓' if results['technical_seo'] else '✗'}")
        print(f"Keyword analysis: {'✓' if results['keyword_analysis'] else '✗'}")
        print(f"Competitor analysis: {'✓' if results['competitor_analysis'] else '✗'}")

if __name__ == "__main__":
    main()
