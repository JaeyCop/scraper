"""
Tests for utility functions and decorators
"""
import pytest
import time
import requests
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from utils import (
    retry_on_failure, rate_limit, RobustSession, validate_url, 
    safe_extract_text, safe_extract_attribute, normalize_domain,
    is_valid_email, clean_text, calculate_time_difference,
    DataValidator, PerformanceMonitor
)


class TestRetryDecorator:
    """Tests for retry decorator"""
    
    def test_retry_success_on_first_attempt(self):
        """Test successful execution on first attempt"""
        call_count = 0
        
        @retry_on_failure(max_retries=3)
        def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = successful_function()
        assert result == "success"
        assert call_count == 1
    
    def test_retry_success_after_failures(self):
        """Test successful execution after some failures"""
        call_count = 0
        
        @retry_on_failure(max_retries=3, delay=0.1)
        def eventually_successful_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Temporary failure")
            return "success"
        
        result = eventually_successful_function()
        assert result == "success"
        assert call_count == 3
    
    def test_retry_max_retries_exceeded(self):
        """Test when max retries are exceeded"""
        call_count = 0
        
        @retry_on_failure(max_retries=2, delay=0.1)
        def always_failing_function():
            nonlocal call_count
            call_count += 1
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError):
            always_failing_function()
        
        assert call_count == 3  # Initial call + 2 retries
    
    def test_retry_specific_exceptions(self):
        """Test retry with specific exception types"""
        @retry_on_failure(max_retries=2, delay=0.1, exceptions=(ValueError,))
        def specific_exception_function():
            raise TypeError("This should not be retried")
        
        with pytest.raises(TypeError):
            specific_exception_function()


class TestRateLimitDecorator:
    """Tests for rate limit decorator"""
    
    def test_rate_limit_basic(self):
        """Test basic rate limiting functionality"""
        call_times = []
        
        @rate_limit(calls_per_second=5.0)  # 5 calls per second = 0.2s interval
        def limited_function():
            call_times.append(time.time())
            return "called"
        
        # Make multiple calls
        for _ in range(3):
            limited_function()
        
        # Check that calls were spaced appropriately
        assert len(call_times) == 3
        if len(call_times) > 1:
            time_diff = call_times[1] - call_times[0]
            assert time_diff >= 0.15  # Should be at least close to 0.2s
    
    def test_rate_limit_no_delay_first_call(self):
        """Test that first call has no delay"""
        start_time = time.time()
        
        @rate_limit(calls_per_second=1.0)
        def limited_function():
            return time.time()
        
        first_call_time = limited_function()
        assert first_call_time - start_time < 0.1  # Should be immediate


class TestRobustSession:
    """Tests for RobustSession class"""
    
    def test_session_initialization(self):
        """Test session initialization"""
        session = RobustSession(max_retries=3, timeout=30)
        assert session.timeout == 30
        assert session.session is not None
        assert len(session.user_agents) > 0
    
    @patch('requests.Session.get')
    def test_successful_request(self, mock_get):
        """Test successful HTTP request"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "Success"
        mock_get.return_value = mock_response
        
        session = RobustSession()
        response = session.get("https://example.com")
        
        assert response is not None
        assert response.status_code == 200
    
    @patch('requests.Session.get')
    def test_failed_request(self, mock_get):
        """Test failed HTTP request"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        session = RobustSession()
        response = session.get("https://example.com/notfound")
        
        assert response is None
    
    @patch('requests.Session.get')
    def test_timeout_handling(self, mock_get):
        """Test timeout handling"""
        mock_get.side_effect = requests.exceptions.Timeout("Request timeout")
        
        session = RobustSession()
        response = session.get("https://slow-example.com")
        
        assert response is None
    
    @patch('requests.Session.get')
    def test_connection_error_handling(self, mock_get):
        """Test connection error handling"""
        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")
        
        session = RobustSession()
        response = session.get("https://unreachable.com")
        
        assert response is None


class TestValidationFunctions:
    """Tests for validation functions"""
    
    def test_validate_url_valid(self):
        """Test URL validation with valid URLs"""
        valid_urls = [
            "https://example.com",
            "http://test.org",
            "https://subdomain.example.com/path",
            "http://localhost:8000"
        ]
        
        for url in valid_urls:
            assert validate_url(url) is True
    
    def test_validate_url_invalid(self):
        """Test URL validation with invalid URLs"""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",  # Wrong scheme
            "https://",  # No domain
            "example.com",  # No scheme
            ""
        ]
        
        for url in invalid_urls:
            assert validate_url(url) is False
    
    def test_is_valid_email_valid(self):
        """Test email validation with valid emails"""
        valid_emails = [
            "test@example.com",
            "user.name@domain.org",
            "user+tag@example.co.uk",
            "123@numbers.com"
        ]
        
        for email in valid_emails:
            assert is_valid_email(email) is True
    
    def test_is_valid_email_invalid(self):
        """Test email validation with invalid emails"""
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user@.com",
            "user space@example.com",
            ""
        ]
        
        for email in invalid_emails:
            assert is_valid_email(email) is False


class TestTextProcessingFunctions:
    """Tests for text processing functions"""
    
    def test_safe_extract_text_valid_element(self):
        """Test safe text extraction from valid element"""
        from bs4 import BeautifulSoup
        
        html = "<p>Test content</p>"
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.find('p')
        
        result = safe_extract_text(element)
        assert result == "Test content"
    
    def test_safe_extract_text_none_element(self):
        """Test safe text extraction from None element"""
        result = safe_extract_text(None, "default")
        assert result == "default"
    
    def test_safe_extract_text_empty_default(self):
        """Test safe text extraction with empty default"""
        result = safe_extract_text(None)
        assert result == ""
    
    def test_safe_extract_attribute_valid(self):
        """Test safe attribute extraction from valid element"""
        from bs4 import BeautifulSoup
        
        html = '<a href="https://example.com">Link</a>'
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.find('a')
        
        result = safe_extract_attribute(element, 'href')
        assert result == "https://example.com"
    
    def test_safe_extract_attribute_missing(self):
        """Test safe attribute extraction from element without attribute"""
        from bs4 import BeautifulSoup
        
        html = '<a>Link without href</a>'
        soup = BeautifulSoup(html, 'html.parser')
        element = soup.find('a')
        
        result = safe_extract_attribute(element, 'href', 'default')
        assert result == "default"
    
    def test_normalize_domain_valid(self):
        """Test domain normalization with valid URLs"""
        test_cases = [
            ("https://www.example.com", "example.com"),
            ("http://example.com", "example.com"),
            ("https://subdomain.example.com", "subdomain.example.com"),
            ("https://WWW.EXAMPLE.COM", "example.com")
        ]
        
        for url, expected in test_cases:
            assert normalize_domain(url) == expected
    
    def test_normalize_domain_invalid(self):
        """Test domain normalization with invalid URLs"""
        assert normalize_domain("not-a-url") == ""
        assert normalize_domain("") == ""
    
    def test_clean_text_basic(self):
        """Test basic text cleaning"""
        dirty_text = "  This   is   some   text   with   extra   spaces  "
        cleaned = clean_text(dirty_text)
        assert cleaned == "This is some text with extra spaces"
    
    def test_clean_text_special_characters(self):
        """Test text cleaning with special characters"""
        dirty_text = "Text with @#$%^&*() special characters!"
        cleaned = clean_text(dirty_text)
        assert "Text with" in cleaned
        assert "special characters!" in cleaned
    
    def test_clean_text_empty(self):
        """Test text cleaning with empty input"""
        assert clean_text("") == ""
        assert clean_text(None) == ""


class TestTimeUtils:
    """Tests for time utility functions"""
    
    def test_calculate_time_difference_recent(self):
        """Test time difference calculation with recent timestamp"""
        recent_time = datetime.now() - timedelta(hours=2)
        timestamp = recent_time.isoformat()
        
        diff = calculate_time_difference(timestamp)
        assert diff.total_seconds() > 7000  # ~2 hours
        assert diff.total_seconds() < 7400  # ~2 hours + buffer
    
    def test_calculate_time_difference_invalid(self):
        """Test time difference calculation with invalid timestamp"""
        diff = calculate_time_difference("invalid-timestamp")
        assert diff.days == 999  # Should return large difference


class TestDataValidator:
    """Tests for data validation"""
    
    def test_validate_keyword_data_valid(self):
        """Test keyword data validation with valid data"""
        valid_data = {
            'keyword': 'test',
            'search_volume': '1000',
            'competition': 'Medium',
            'difficulty_score': 50
        }
        
        assert DataValidator.validate_keyword_data(valid_data) is True
    
    def test_validate_keyword_data_invalid(self):
        """Test keyword data validation with invalid data"""
        invalid_data = {
            'keyword': 'test',
            'search_volume': '1000'
            # Missing required fields
        }
        
        assert DataValidator.validate_keyword_data(invalid_data) is False
    
    def test_validate_content_data_valid(self):
        """Test content data validation with valid data"""
        valid_data = {
            'title': 'Test Page',
            'url': 'https://example.com',
            'word_count': 500
        }
        
        assert DataValidator.validate_content_data(valid_data) is True
    
    def test_validate_technical_seo_data_valid(self):
        """Test technical SEO data validation with valid data"""
        valid_data = {
            'url': 'https://example.com',
            'page_title': 'Test Page',
            'h1_count': 1,
            'page_load_time': 2.5
        }
        
        assert DataValidator.validate_technical_seo_data(valid_data) is True


class TestPerformanceMonitor:
    """Tests for performance monitoring"""
    
    def test_performance_monitor_timing(self):
        """Test performance monitoring timing"""
        monitor = PerformanceMonitor()
        
        monitor.start_timer("test_operation")
        time.sleep(0.1)  # Simulate work
        duration = monitor.end_timer("test_operation")
        
        assert duration >= 0.1
        assert duration < 0.2  # Should be close to 0.1s
    
    def test_performance_monitor_multiple_operations(self):
        """Test monitoring multiple operations"""
        monitor = PerformanceMonitor()
        
        monitor.start_timer("op1")
        time.sleep(0.05)
        monitor.end_timer("op1")
        
        monitor.start_timer("op2")
        time.sleep(0.05)
        monitor.end_timer("op2")
        
        metrics = monitor.get_metrics()
        assert "op1" in metrics
        assert "op2" in metrics
        assert "duration" in metrics["op1"]
        assert "duration" in metrics["op2"]
    
    def test_performance_monitor_invalid_operation(self):
        """Test ending timer for non-existent operation"""
        monitor = PerformanceMonitor()
        
        duration = monitor.end_timer("nonexistent_operation")
        assert duration == 0
