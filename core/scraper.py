"""Web scraper module with enhanced error handling for web UI"""
from crawl4ai import AsyncWebCrawler
from typing import Optional, Dict, Any, Tuple
import asyncio
import time
from .utils import validate_url, create_error_response, url_cache


class WebScraperError(Exception):
    """Custom exception for web scraping errors"""
    def __init__(self, message: str, error_type: str = "scraping_error", details: Dict[str, Any] = None):
        super().__init__(message)
        self.error_type = error_type
        self.details = details or {}


class WebScraper:
    """Web scraper using Crawl4AI for enhanced content extraction with web UI support"""
    
    def __init__(self, use_cache: bool = True, timeout: int = 30):
        self.use_cache = use_cache
        self.timeout = timeout
        self._stats = {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "cache_hits": 0
        }
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get scraping statistics"""
        return self._stats.copy()
    
    async def _async_scrape(self, url: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """Async helper method to scrape a page with detailed error info"""
        start_time = time.time()
        error_details = None
        
        try:
            async with AsyncWebCrawler(
                verbose=False,
                timeout=self.timeout
            ) as crawler:
                result = await crawler.arun(url)
                
                elapsed_time = time.time() - start_time
                
                if result.success:
                    return result.html, {
                        "elapsed_time": elapsed_time,
                        "content_length": len(result.html) if result.html else 0,
                        "status": "success"
                    }
                else:
                    error_details = {
                        "elapsed_time": elapsed_time,
                        "status": "failed",
                        "reason": "Crawler returned unsuccessful result"
                    }
                    return None, error_details
                    
        except asyncio.TimeoutError:
            error_details = {
                "elapsed_time": time.time() - start_time,
                "status": "timeout",
                "reason": f"Request timed out after {self.timeout} seconds"
            }
            return None, error_details
            
        except Exception as e:
            error_details = {
                "elapsed_time": time.time() - start_time,
                "status": "error",
                "reason": str(e),
                "error_type": type(e).__name__
            }
            return None, error_details
    
    def scrape_page(self, url: str, wait_time: int = 3) -> Dict[str, Any]:
        """Scrape a single page and return structured result for web UI
        
        Args:
            url: The URL to scrape
            wait_time: Kept for backward compatibility (not used)
            
        Returns:
            Dict containing:
                - success: bool
                - html: Optional[str] - The scraped HTML content
                - error: Optional[str] - Error message if failed
                - details: Dict with metadata about the request
        """
        self._stats["total_requests"] += 1
        
        # Validate URL first
        is_valid, error_msg = validate_url(url)
        if not is_valid:
            self._stats["failed_requests"] += 1
            raise WebScraperError(
                f"Invalid URL: {error_msg}",
                error_type="validation_error",
                details={"url": url, "validation_error": error_msg}
            )
        
        # Check cache if enabled
        if self.use_cache:
            cached_result = url_cache.get(url, "scrape")
            if cached_result:
                self._stats["cache_hits"] += 1
                self._stats["successful_requests"] += 1
                return {
                    "success": True,
                    "html": cached_result["html"],
                    "details": {
                        **cached_result.get("details", {}),
                        "from_cache": True
                    }
                }
        
        try:
            # Run the async scraper
            html, details = asyncio.run(self._async_scrape(url))
            
            if html:
                self._stats["successful_requests"] += 1
                
                result = {
                    "success": True,
                    "html": html,
                    "details": {
                        **details,
                        "url": url,
                        "from_cache": False
                    }
                }
                
                # Cache successful result
                if self.use_cache:
                    url_cache.set(url, "scrape", result)
                
                return result
            else:
                self._stats["failed_requests"] += 1
                raise WebScraperError(
                    f"Failed to scrape {url}",
                    error_type="scraping_failed",
                    details={**details, "url": url}
                )
                
        except WebScraperError:
            raise
        except Exception as e:
            self._stats["failed_requests"] += 1
            raise WebScraperError(
                f"Unexpected error scraping {url}: {str(e)}",
                error_type="unexpected_error",
                details={
                    "url": url,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                }
            )
    
    def scrape_page_simple(self, url: str, wait_time: int = 3) -> Optional[str]:
        """Legacy method for backward compatibility - returns just HTML or None"""
        try:
            result = self.scrape_page(url, wait_time)
            return result.get("html") if result.get("success") else None
        except:
            return None
    
    def clear_cache(self):
        """Clear the URL cache"""
        if self.use_cache:
            url_cache.clear()
    
    def validate_and_prepare_url(self, url: str) -> str:
        """Validate and prepare URL for scraping"""
        is_valid, error_msg = validate_url(url)
        if not is_valid:
            raise WebScraperError(
                error_msg,
                error_type="validation_error",
                details={"url": url}
            )
        
        # Ensure HTTPS for security
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)
        
        return url