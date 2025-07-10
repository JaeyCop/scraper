"""
Tests for content analyzer module
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from content_analyzer import ContentAnalyzer
from models import ContentData, TechnicalSEOData


class TestContentAnalyzer:
    """Tests for ContentAnalyzer class"""
    
    def test_content_analyzer_initialization(self, db_manager):
        """Test content analyzer initialization"""
        analyzer = ContentAnalyzer(db_manager)
        assert analyzer.db_manager == db_manager
        assert analyzer.session is not None
    
    @patch('content_analyzer.ContentAnalyzer._extract_clean_text')
    @patch('content_analyzer.ContentAnalyzer._extract_title')
    @patch('content_analyzer.ContentAnalyzer._extract_meta_description')
    @patch('requests.Session.get')
    def test_analyze_content_enhanced_success(self, mock_get, mock_meta, mock_title, mock_text, db_manager, mock_response):
        """Test successful content analysis"""
        # Setup mocks
        mock_get.return_value = mock_response
        mock_title.return_value = "Test Page Title"
        mock_meta.return_value = "Test meta description"
        mock_text.return_value = "This is test content for analysis"
        
        analyzer = ContentAnalyzer(db_manager)
        
        # Mock other methods
        with patch.object(analyzer, '_extract_links') as mock_links, \
             patch.object(analyzer, '_extract_images') as mock_images, \
             patch.object(analyzer, '_extract_schema_markup') as mock_schema, \
             patch.object(analyzer, '_calculate_keyword_density') as mock_density, \
             patch.object(analyzer, '_calculate_reading_score') as mock_reading:
            
            mock_links.return_value = (["https://example.com/page1"], ["https://external.com"])
            mock_images.return_value = [{"src": "image.jpg", "alt": "Test image"}]
            mock_schema.return_value = ["Article"]
            mock_density.return_value = {"test": 2.5}
            mock_reading.return_value = 75.0
            
            result = analyzer.analyze_content_enhanced("https://example.com", ["test"])
            
            assert result is not None
            assert result.title == "Test Page Title"
            assert result.url == "https://example.com"
            assert result.meta_description == "Test meta description"
            assert result.word_count > 0
            assert result.keyword_density == {"test": 2.5}
            assert result.reading_score == 75.0
    
    @patch('requests.Session.get')
    def test_analyze_content_enhanced_http_error(self, mock_get, db_manager):
        """Test content analysis with HTTP error"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        analyzer = ContentAnalyzer(db_manager)
        result = analyzer.analyze_content_enhanced("https://example.com/notfound")
        
        assert result is None
    
    @patch('requests.Session.get')
    def test_analyze_content_enhanced_exception(self, mock_get, db_manager):
        """Test content analysis with exception"""
        mock_get.side_effect = Exception("Network error")
        
        analyzer = ContentAnalyzer(db_manager)
        result = analyzer.analyze_content_enhanced("https://example.com")
        
        assert result is None
    
    def test_analyze_content_enhanced_cached_data(self, db_manager, sample_content_data):
        """Test content analysis with cached data"""
        # Save data to cache
        db_manager.save_content_data(sample_content_data)
        
        analyzer = ContentAnalyzer(db_manager)
        result = analyzer.analyze_content_enhanced(sample_content_data.url)
        
        assert result is not None
        assert result.title == sample_content_data.title
        assert result.url == sample_content_data.url
    
    @patch('content_analyzer.ContentAnalyzer._extract_title')
    @patch('content_analyzer.ContentAnalyzer._extract_meta_description')
    @patch('requests.Session.get')
    def test_perform_technical_seo_audit_success(self, mock_get, mock_meta, mock_title, db_manager, mock_response):
        """Test successful technical SEO audit"""
        # Setup mocks
        mock_get.return_value = mock_response
        mock_title.return_value = "Test Page"
        mock_meta.return_value = "Test description"
        
        analyzer = ContentAnalyzer(db_manager)
        
        # Mock other methods
        with patch.object(analyzer, '_extract_canonical_url') as mock_canonical, \
             patch.object(analyzer, '_extract_robots_meta') as mock_robots, \
             patch.object(analyzer, '_count_links') as mock_links, \
             patch.object(analyzer, '_count_images_without_alt') as mock_images, \
             patch.object(analyzer, '_extract_structured_data_types') as mock_schema:
            
            mock_canonical.return_value = "https://example.com"
            mock_robots.return_value = "index,follow"
            mock_links.return_value = (5, 2)
            mock_images.return_value = 1
            mock_schema.return_value = ["Article"]
            
            result = analyzer.perform_technical_seo_audit("https://example.com")
            
            assert result is not None
            assert result.url == "https://example.com"
            assert result.page_title == "Test Page"
            assert result.meta_description == "Test description"
            assert result.canonical_url == "https://example.com"
            assert result.robots_meta == "index,follow"
            assert result.internal_links_count == 5
            assert result.external_links_count == 2
            assert result.images_without_alt == 1
            assert result.ssl_certificate is True  # HTTPS URL
    
    def test_extract_title_valid(self, db_manager):
        """Test title extraction from valid HTML"""
        from bs4 import BeautifulSoup
        
        html = "<html><head><title>Test Page Title</title></head></html>"
        soup = BeautifulSoup(html, 'html.parser')
        
        analyzer = ContentAnalyzer(db_manager)
        result = analyzer._extract_title(soup)
        
        assert result == "Test Page Title"
    
    def test_extract_title_missing(self, db_manager):
        """Test title extraction from HTML without title"""
        from bs4 import BeautifulSoup
        
        html = "<html><head></head></html>"
        soup = BeautifulSoup(html, 'html.parser')
        
        analyzer = ContentAnalyzer(db_manager)
        result = analyzer._extract_title(soup)
        
        assert result == "No Title"
    
    def test_extract_meta_description_valid(self, db_manager):
        """Test meta description extraction from valid HTML"""
        from bs4 import BeautifulSoup
        
        html = '<html><head><meta name="description" content="Test description"></head></html>'
        soup = BeautifulSoup(html, 'html.parser')
        
        analyzer = ContentAnalyzer(db_manager)
        result = analyzer._extract_meta_description(soup)
        
        assert result == "Test description"
    
    def test_extract_meta_description_missing(self, db_manager):
        """Test meta description extraction from HTML without meta description"""
        from bs4 import BeautifulSoup
        
        html = "<html><head></head></html>"
        soup = BeautifulSoup(html, 'html.parser')
        
        analyzer = ContentAnalyzer(db_manager)
        result = analyzer._extract_meta_description(soup)
        
        assert result == "No Meta Description"
    
    def test_extract_links_valid(self, db_manager):
        """Test link extraction from valid HTML"""
        from bs4 import BeautifulSoup
        
        html = '''
        <html>
            <body>
                <a href="https://example.com/page1">Internal Link</a>
                <a href="https://external.com">External Link</a>
                <a href="/relative">Relative Link</a>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        analyzer = ContentAnalyzer(db_manager)
        internal, external = analyzer._extract_links(soup, "https://example.com")
        
        assert len(internal) == 2  # Internal link and relative link
        assert len(external) == 1
        assert "https://example.com/page1" in internal
        assert "https://external.com" in external
    
    def test_extract_images_valid(self, db_manager):
        """Test image extraction from valid HTML"""
        from bs4 import BeautifulSoup
        
        html = '''
        <html>
            <body>
                <img src="image1.jpg" alt="Image 1" title="Title 1">
                <img src="image2.jpg" alt="Image 2">
                <img src="image3.jpg">
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        analyzer = ContentAnalyzer(db_manager)
        images = analyzer._extract_images(soup)
        
        assert len(images) == 3
        assert images[0]["src"] == "image1.jpg"
        assert images[0]["alt"] == "Image 1"
        assert images[0]["title"] == "Title 1"
        assert images[2]["alt"] == ""  # Missing alt
    
    def test_count_images_without_alt(self, db_manager):
        """Test counting images without alt text"""
        from bs4 import BeautifulSoup
        
        html = '''
        <html>
            <body>
                <img src="image1.jpg" alt="Image 1">
                <img src="image2.jpg">
                <img src="image3.jpg" alt="">
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        analyzer = ContentAnalyzer(db_manager)
        count = analyzer._count_images_without_alt(soup)
        
        assert count == 2  # One without alt, one with empty alt
    
    def test_extract_schema_markup_valid(self, db_manager):
        """Test schema markup extraction from valid HTML"""
        from bs4 import BeautifulSoup
        
        html = '''
        <html>
            <head>
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org",
                    "@type": "Article",
                    "headline": "Test Article"
                }
                </script>
                <script type="application/ld+json">
                {
                    "@context": "https://schema.org",
                    "@type": "Organization",
                    "name": "Test Org"
                }
                </script>
            </head>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        analyzer = ContentAnalyzer(db_manager)
        schema_types = analyzer._extract_schema_markup(soup)
        
        assert len(schema_types) == 2
        assert "Article" in schema_types
        assert "Organization" in schema_types
    
    def test_extract_schema_markup_invalid_json(self, db_manager):
        """Test schema markup extraction with invalid JSON"""
        from bs4 import BeautifulSoup
        
        html = '''
        <html>
            <head>
                <script type="application/ld+json">
                { invalid json }
                </script>
            </head>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        analyzer = ContentAnalyzer(db_manager)
        schema_types = analyzer._extract_schema_markup(soup)
        
        assert len(schema_types) == 0
    
    def test_calculate_keyword_density_valid(self, db_manager):
        """Test keyword density calculation"""
        analyzer = ContentAnalyzer(db_manager)
        
        text = "This is a test text with test words and more test content"
        keywords = ["test", "content", "missing"]
        
        density = analyzer._calculate_keyword_density(text, keywords)
        
        assert density["test"] > 0
        assert density["content"] > 0
        assert density["missing"] == 0
    
    def test_calculate_keyword_density_empty(self, db_manager):
        """Test keyword density calculation with empty inputs"""
        analyzer = ContentAnalyzer(db_manager)
        
        # Empty text
        density = analyzer._calculate_keyword_density("", ["test"])
        assert density == {}
        
        # Empty keywords
        density = analyzer._calculate_keyword_density("test text", [])
        assert density == {}
    
    def test_check_mobile_friendly_valid(self, db_manager):
        """Test mobile-friendly check with viewport meta tag"""
        from bs4 import BeautifulSoup
        
        html = '''
        <html>
            <head>
                <meta name="viewport" content="width=device-width, initial-scale=1">
            </head>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        analyzer = ContentAnalyzer(db_manager)
        is_mobile_friendly = analyzer._check_mobile_friendly(soup)
        
        assert is_mobile_friendly is True
    
    def test_check_mobile_friendly_invalid(self, db_manager):
        """Test mobile-friendly check without viewport meta tag"""
        from bs4 import BeautifulSoup
        
        html = "<html><head></head></html>"
        soup = BeautifulSoup(html, 'html.parser')
        
        analyzer = ContentAnalyzer(db_manager)
        is_mobile_friendly = analyzer._check_mobile_friendly(soup)
        
        assert is_mobile_friendly is False
    
    def test_calculate_page_speed_score(self, db_manager):
        """Test page speed score calculation"""
        analyzer = ContentAnalyzer(db_manager)
        
        # Test different load times
        assert analyzer._calculate_page_speed_score(0.5) == 100.0
        assert analyzer._calculate_page_speed_score(2.0) == 80.0
        assert analyzer._calculate_page_speed_score(4.0) == 60.0
        assert analyzer._calculate_page_speed_score(6.0) == 40.0
    
    def test_extract_clean_text_valid(self, db_manager):
        """Test clean text extraction"""
        from bs4 import BeautifulSoup
        
        html = '''
        <html>
            <head>
                <script>console.log("script");</script>
                <style>.test { color: red; }</style>
            </head>
            <body>
                <h1>Main Heading</h1>
                <p>This is a paragraph with some text.</p>
                <div>Another div with content.</div>
            </body>
        </html>
        '''
        soup = BeautifulSoup(html, 'html.parser')
        
        analyzer = ContentAnalyzer(db_manager)
        clean_text = analyzer._extract_clean_text(soup)
        
        assert "Main Heading" in clean_text
        assert "This is a paragraph" in clean_text
        assert "Another div with content" in clean_text
        assert "console.log" not in clean_text  # Script should be removed
        assert "color: red" not in clean_text  # Style should be removed
