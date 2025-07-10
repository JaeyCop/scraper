"""
Pytest configuration and shared fixtures
"""
import pytest
import os
import tempfile
import sqlite3
from unittest.mock import Mock, patch
import asyncio
from datetime import datetime

# Add project root to path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import ScraperConfig
from database import DatabaseManager
from models import KeywordData, ContentData, TechnicalSEOData


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    yield db_path
    
    # Cleanup
    try:
        os.unlink(db_path)
    except OSError:
        pass


@pytest.fixture
def test_config(temp_db):
    """Test configuration with temporary database"""
    config = ScraperConfig()
    config.db_path = temp_db
    config.headless = True
    config.timeout = 5
    config.min_delay = 0.1
    config.max_delay = 0.2
    return config


@pytest.fixture
def db_manager(temp_db):
    """Database manager with temporary database"""
    return DatabaseManager(temp_db)


@pytest.fixture
def sample_keyword_data():
    """Sample keyword data for testing"""
    return KeywordData(
        keyword="test keyword",
        search_volume="1,000-10,000",
        competition="Medium",
        difficulty_score=65,
        related_keywords=["related1", "related2"],
        people_also_ask=["Question 1?", "Question 2?"],
        featured_snippet="Sample snippet",
        local_pack=["Business 1", "Business 2"],
        timestamp=datetime.now().isoformat()
    )


@pytest.fixture
def sample_content_data():
    """Sample content data for testing"""
    return ContentData(
        title="Test Page Title",
        url="https://example.com",
        meta_description="Test meta description",
        h1_tags=["Main Heading"],
        h2_tags=["Sub Heading 1", "Sub Heading 2"],
        h3_tags=["Sub Sub Heading"],
        word_count=500,
        keyword_density={"test": 2.5, "keyword": 1.8},
        reading_score=75.0,
        internal_links=["https://example.com/page1"],
        external_links=["https://external.com"],
        images=[{"src": "image.jpg", "alt": "Test image", "title": ""}],
        schema_markup=["Article", "Organization"],
        page_speed_score=85.0,
        mobile_friendly=True,
        timestamp=datetime.now().isoformat()
    )


@pytest.fixture
def sample_technical_seo_data():
    """Sample technical SEO data for testing"""
    return TechnicalSEOData(
        url="https://example.com",
        page_title="Test Page",
        meta_description="Test description",
        canonical_url="https://example.com",
        robots_meta="index,follow",
        h1_count=1,
        h2_count=3,
        internal_links_count=5,
        external_links_count=2,
        images_without_alt=0,
        page_load_time=1.5,
        mobile_friendly=True,
        ssl_certificate=True,
        structured_data=["Article"],
        timestamp=datetime.now().isoformat()
    )


@pytest.fixture
def mock_response():
    """Mock HTTP response"""
    mock = Mock()
    mock.status_code = 200
    mock.content = b"""
    <html>
        <head>
            <title>Test Page</title>
            <meta name="description" content="Test description">
            <meta name="viewport" content="width=device-width, initial-scale=1">
        </head>
        <body>
            <h1>Main Heading</h1>
            <h2>Sub Heading</h2>
            <p>Test content with some words for analysis.</p>
            <a href="/internal">Internal Link</a>
            <a href="https://external.com">External Link</a>
            <img src="test.jpg" alt="Test image">
        </body>
    </html>
    """
    return mock


@pytest.fixture
def mock_playwright_page():
    """Mock Playwright page object"""
    page = Mock()
    
    # Mock locator methods
    locator = Mock()
    locator.count.return_value = 2
    locator.nth.return_value.inner_text.return_value = "Test text"
    locator.first.count.return_value = 1
    locator.first.inner_text.return_value = "Featured snippet text"
    
    page.locator.return_value = locator
    page.goto = Mock()
    page.evaluate = Mock()
    
    return page


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


class MockBrowser:
    """Mock browser for testing"""
    def __init__(self):
        self.closed = False
    
    def close(self):
        self.closed = True


class MockPlaywright:
    """Mock playwright for testing"""
    def __init__(self):
        self.stopped = False
    
    def stop(self):
        self.stopped = True


@pytest.fixture
def mock_browser_context():
    """Mock browser context"""
    browser = MockBrowser()
    playwright = MockPlaywright()
    context = Mock()
    
    return playwright, browser, context
