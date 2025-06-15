"""Tests for the web scraper module"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
import time
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.scraper import WebScraper, WebScraperError


class TestWebScraperError:
    """Test custom WebScraperError exception"""
    
    def test_error_creation(self):
        """Test creating WebScraperError with all parameters"""
        error = WebScraperError(
            "Test error",
            error_type="test_error",
            details={"key": "value"}
        )
        assert str(error) == "Test error"
        assert error.error_type == "test_error"
        assert error.details == {"key": "value"}
    
    def test_error_default_values(self):
        """Test WebScraperError with default values"""
        error = WebScraperError("Simple error")
        assert str(error) == "Simple error"
        assert error.error_type == "scraping_error"
        assert error.details == {}


class TestWebScraper:
    """Test WebScraper class functionality"""
    
    @pytest.fixture
    def scraper(self):
        """Create a WebScraper instance for testing"""
        return WebScraper(use_cache=False, timeout=30)
    
    @pytest.fixture
    def scraper_with_cache(self):
        """Create a WebScraper instance with caching enabled"""
        return WebScraper(use_cache=True, timeout=30)
    
    def test_init(self):
        """Test WebScraper initialization"""
        scraper = WebScraper(use_cache=True, timeout=60)
        assert scraper.use_cache is True
        assert scraper.timeout == 60
        assert scraper._stats == {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "failures": 0,
            "total_time": 0.0
        }
    
    def test_validate_url_valid(self, scraper):
        """Test URL validation with valid URLs"""
        valid_urls = [
            "https://example.com",
            "http://test.com/page",
            "https://subdomain.example.com/path/to/page"
        ]
        for url in valid_urls:
            assert scraper._validate_url(url) is True
    
    def test_validate_url_invalid(self, scraper):
        """Test URL validation with invalid URLs"""
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "javascript:alert('xss')",
            "",
            None
        ]
        for url in invalid_urls:
            if url is None:
                with pytest.raises(AttributeError):
                    scraper._validate_url(url)
            else:
                assert scraper._validate_url(url) is False
    
    @patch('core.scraper.AsyncWebCrawler')
    def test_scrape_page_success(self, mock_crawler_class, scraper):
        """Test successful page scraping"""
        mock_crawler = AsyncMock()
        mock_result = Mock()
        mock_result.html = "<html><body>Test content</body></html>"
        mock_result.success = True
        mock_crawler.arun.return_value = mock_result
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
        
        result = scraper.scrape_page("https://example.com")
        
        assert result['success'] is True
        assert result['html'] == "<html><body>Test content</body></html>"
        assert 'url' in result
        assert 'scraped_at' in result
        assert scraper._stats['total_requests'] == 1
        assert scraper._stats['cache_misses'] == 1
    
    @patch('core.scraper.AsyncWebCrawler')
    def test_scrape_page_with_cache_hit(self, mock_crawler_class, scraper_with_cache):
        """Test scraping with cache hit"""
        url = "https://example.com"
        cached_html = "<html><body>Cached content</body></html>"
        
        # Pre-populate cache
        from utils import cache_set
        cache_set(f"scrape:{url}", cached_html, ttl=300)
        
        result = scraper_with_cache.scrape_page(url)
        
        assert result['success'] is True
        assert result['html'] == cached_html
        assert result['from_cache'] is True
        assert scraper_with_cache._stats['cache_hits'] == 1
        assert scraper_with_cache._stats['total_requests'] == 1
        
        # Crawler should not be called
        mock_crawler_class.assert_not_called()
    
    @patch('core.scraper.AsyncWebCrawler')
    def test_scrape_page_failure(self, mock_crawler_class, scraper):
        """Test scraping failure"""
        mock_crawler = AsyncMock()
        mock_crawler.arun.side_effect = Exception("Network error")
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
        
        with pytest.raises(WebScraperError) as exc_info:
            scraper.scrape_page("https://example.com")
        
        assert "Failed to scrape" in str(exc_info.value)
        assert exc_info.value.error_type == "scraping_error"
        assert scraper._stats['failures'] == 1
    
    def test_scrape_page_invalid_url(self, scraper):
        """Test scraping with invalid URL"""
        with pytest.raises(WebScraperError) as exc_info:
            scraper.scrape_page("not-a-valid-url")
        
        assert "Invalid URL format" in str(exc_info.value)
        assert exc_info.value.error_type == "invalid_url"
    
    @patch('core.scraper.AsyncWebCrawler')
    def test_scrape_page_simple(self, mock_crawler_class, scraper):
        """Test scrape_page_simple method"""
        mock_crawler = AsyncMock()
        mock_result = Mock()
        mock_result.html = "<html><body>Simple content</body></html>"
        mock_result.success = True
        mock_crawler.arun.return_value = mock_result
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler
        
        result = scraper.scrape_page_simple("https://example.com")
        
        assert result == "<html><body>Simple content</body></html>"
    
    def test_get_stats(self, scraper):
        """Test getting statistics"""
        stats = scraper.get_stats()
        assert isinstance(stats, dict)
        assert 'total_requests' in stats
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'failures' in stats
        assert 'total_time' in stats
        assert 'avg_time_per_request' in stats
    
    def test_reset_stats(self, scraper):
        """Test resetting statistics"""
        # Modify stats
        scraper._stats['total_requests'] = 10
        scraper._stats['cache_hits'] = 5
        
        # Reset
        scraper.reset_stats()
        
        # Check all values are reset
        assert scraper._stats['total_requests'] == 0
        assert scraper._stats['cache_hits'] == 0
        assert scraper._stats['cache_misses'] == 0
        assert scraper._stats['failures'] == 0
        assert scraper._stats['total_time'] == 0.0
    
    @patch('core.scraper.AsyncWebCrawler')
    def test_context_manager(self, mock_crawler_class):
        """Test WebScraper as context manager"""
        with WebScraper() as scraper:
            assert isinstance(scraper, WebScraper)
        
        # Stats should be available after exit
        stats = scraper.get_stats()
        assert isinstance(stats, dict)