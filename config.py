"""
Configuration file for SEO Scraper
"""
import os
from dataclasses import dataclass
from typing import List

@dataclass
class ScraperConfig:
    """Configuration settings for the SEO scraper"""
    
    # Database settings
    db_path: str = "advanced_seo_data.db"
    
    # Browser settings
    headless: bool = True
    stealth_mode: bool = True
    timeout: int = 15
    
    # Rate limiting
    min_delay: float = 1.0
    max_delay: float = 3.0
    request_delay: float = 2.0
    
    # User agents for rotation
    user_agents: List[str] = None
    
    # Reporting
    report_directory: str = "seo_reports"
    
    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(levelname)s - %(message)s"
    
    def __post_init__(self):
        if self.user_agents is None:
            self.user_agents = [
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ]
        
        # Ensure report directory exists
        if not os.path.exists(self.report_directory):
            os.makedirs(self.report_directory)

# Default configuration instance
config = ScraperConfig()
