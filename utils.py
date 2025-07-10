"""
Utility functions for error handling, retries, and common operations
"""
import time
import random
import logging
import functools
from typing import Callable, Any, Optional, List
from datetime import datetime, timedelta
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0, 
                    exceptions: tuple = (Exception,)):
    """
    Decorator for retrying functions on failure with exponential backoff
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
        exceptions: Tuple of exceptions to catch and retry on
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt == max_retries:
                        logger.error(f"Function {func.__name__} failed after {max_retries} retries: {e}")
                        raise e
                    
                    logger.warning(f"Attempt {attempt + 1} failed for {func.__name__}: {e}. Retrying in {current_delay:.2f}s")
                    time.sleep(current_delay + random.uniform(0, 1))  # Add jitter
                    current_delay *= backoff
            
            raise last_exception
        return wrapper
    return decorator

def rate_limit(calls_per_second: float = 1.0):
    """
    Decorator to rate limit function calls
    
    Args:
        calls_per_second: Maximum number of calls per second
    """
    min_interval = 1.0 / calls_per_second
    last_called = [0.0]
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            left_to_wait = min_interval - elapsed
            if left_to_wait > 0:
                time.sleep(left_to_wait)
            ret = func(*args, **kwargs)
            last_called[0] = time.time()
            return ret
        return wrapper
    return decorator

class RobustSession:
    """Enhanced requests session with retry logic and error handling"""
    
    def __init__(self, max_retries: int = 3, backoff_factor: float = 0.3, 
                 timeout: int = 30, user_agents: List[str] = None):
        self.session = requests.Session()
        self.timeout = timeout
        self.user_agents = user_agents or [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        # Configure retry strategy
        retry_strategy = Retry(
            total=max_retries,
            status_forcelist=[429, 500, 502, 503, 504],
            method_whitelist=["HEAD", "GET", "OPTIONS"],
            backoff_factor=backoff_factor,
            raise_on_status=False
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def get(self, url: str, **kwargs) -> Optional[requests.Response]:
        """Enhanced GET request with error handling"""
        try:
            # Rotate user agent
            self.session.headers['User-Agent'] = random.choice(self.user_agents)
            
            response = self.session.get(url, timeout=self.timeout, **kwargs)
            
            if response.status_code == 200:
                logger.debug(f"Successfully fetched {url}")
                return response
            elif response.status_code == 403:
                logger.warning(f"Access forbidden for {url}")
                return None
            elif response.status_code == 404:
                logger.warning(f"Page not found: {url}")
                return None
            else:
                logger.warning(f"HTTP {response.status_code} for {url}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error(f"Timeout error for {url}")
            return None
        except requests.exceptions.ConnectionError:
            logger.error(f"Connection error for {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {e}")
            return None

def validate_url(url: str) -> bool:
    """Validate if a URL is properly formatted"""
    try:
        from urllib.parse import urlparse
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False

def safe_extract_text(element, default: str = "") -> str:
    """Safely extract text from BeautifulSoup element"""
    try:
        if element:
            return element.get_text().strip()
        return default
    except Exception:
        return default

def safe_extract_attribute(element, attribute: str, default: str = "") -> str:
    """Safely extract attribute from BeautifulSoup element"""
    try:
        if element:
            return element.get(attribute, default)
        return default
    except Exception:
        return default

def normalize_domain(url: str) -> str:
    """Extract and normalize domain from URL"""
    try:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        # Remove www prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except Exception:
        return ""

def is_valid_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def clean_text(text: str) -> str:
    """Clean and normalize text content"""
    if not text:
        return ""
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove special characters but keep basic punctuation
    import re
    text = re.sub(r'[^\w\s\.,!?;:\-()[\]{}"\']', '', text)
    
    return text.strip()

def calculate_time_difference(timestamp: str) -> timedelta:
    """Calculate time difference from ISO timestamp to now"""
    try:
        past_time = datetime.fromisoformat(timestamp)
        return datetime.now() - past_time
    except Exception:
        return timedelta(days=999)  # Return large difference if parsing fails

class DataValidator:
    """Utility class for validating scraped data"""
    
    @staticmethod
    def validate_keyword_data(data: dict) -> bool:
        """Validate keyword data structure"""
        required_fields = ['keyword', 'search_volume', 'competition', 'difficulty_score']
        return all(field in data for field in required_fields)
    
    @staticmethod
    def validate_content_data(data: dict) -> bool:
        """Validate content data structure"""
        required_fields = ['title', 'url', 'word_count']
        return all(field in data for field in required_fields)
    
    @staticmethod
    def validate_technical_seo_data(data: dict) -> bool:
        """Validate technical SEO data structure"""
        required_fields = ['url', 'page_title', 'h1_count', 'page_load_time']
        return all(field in data for field in required_fields)

# Performance monitoring utilities
class PerformanceMonitor:
    """Monitor and log performance metrics"""
    
    def __init__(self):
        self.start_time = None
        self.metrics = {}
    
    def start_timer(self, operation: str):
        """Start timing an operation"""
        self.start_time = time.time()
        self.metrics[operation] = {'start': self.start_time}
    
    def end_timer(self, operation: str):
        """End timing and log results"""
        if operation in self.metrics and self.start_time:
            duration = time.time() - self.start_time
            self.metrics[operation]['duration'] = duration
            logger.info(f"Operation '{operation}' completed in {duration:.2f} seconds")
            return duration
        return 0
    
    def get_metrics(self) -> dict:
        """Get all recorded metrics"""
        return self.metrics.copy()

# Memory usage monitoring
def log_memory_usage(func: Callable) -> Callable:
    """Decorator to log memory usage of a function"""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss / 1024 / 1024  # MB
        
        result = func(*args, **kwargs)
        
        mem_after = process.memory_info().rss / 1024 / 1024  # MB
        mem_diff = mem_after - mem_before
        
        logger.debug(f"Memory usage for {func.__name__}: {mem_before:.1f}MB -> {mem_after:.1f}MB (diff: {mem_diff:+.1f}MB)")
        
        return result
    return wrapper
