"""Utility functions for web UI integration"""
import json
import re
import time
import hashlib
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse
from datetime import datetime, timedelta
from functools import wraps
import threading


class URLCache:
    """Simple in-memory cache for URL results with TTL"""
    
    def __init__(self, ttl_seconds: int = 3600):
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self.ttl_seconds = ttl_seconds
    
    def _generate_key(self, url: str, operation: str) -> str:
        """Generate cache key from URL and operation type"""
        return hashlib.md5(f"{url}:{operation}".encode()).hexdigest()
    
    def get(self, url: str, operation: str) -> Optional[Any]:
        """Get cached result if available and not expired"""
        key = self._generate_key(url, operation)
        
        with self._lock:
            if key in self._cache:
                result, timestamp = self._cache[key]
                if time.time() - timestamp < self.ttl_seconds:
                    return result
                else:
                    del self._cache[key]
        
        return None
    
    def set(self, url: str, operation: str, result: Any):
        """Store result in cache"""
        key = self._generate_key(url, operation)
        
        with self._lock:
            self._cache[key] = (result, time.time())
    
    def clear(self):
        """Clear all cached items"""
        with self._lock:
            self._cache.clear()
    
    def cleanup_expired(self):
        """Remove expired entries from cache"""
        current_time = time.time()
        
        with self._lock:
            expired_keys = [
                key for key, (_, timestamp) in self._cache.items()
                if current_time - timestamp >= self.ttl_seconds
            ]
            for key in expired_keys:
                del self._cache[key]


# Global cache instance
url_cache = URLCache(ttl_seconds=3600)  # 1 hour TTL


def create_response(success: bool, data: Any = None, error: str = None, 
                   status_code: int = 200) -> Dict[str, Any]:
    """Create standardized JSON response format for web UI"""
    response = {
        "success": success,
        "timestamp": datetime.now().isoformat(),
        "status_code": status_code
    }
    
    if success and data is not None:
        response["data"] = data
    elif not success and error:
        response["error"] = {
            "message": error,
            "type": "error"
        }
    
    return response


def create_error_response(error: str, error_type: str = "error", 
                         status_code: int = 500) -> Dict[str, Any]:
    """Create standardized error response"""
    return {
        "success": False,
        "timestamp": datetime.now().isoformat(),
        "status_code": status_code,
        "error": {
            "message": error,
            "type": error_type
        }
    }


def validate_url(url: str) -> Tuple[bool, Optional[str]]:
    """Validate URL format and accessibility
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "URL cannot be empty"
    
    # Basic URL validation
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False, "Invalid URL format"
        
        if result.scheme not in ['http', 'https']:
            return False, "URL must use HTTP or HTTPS protocol"
        
        # Check for common invalid patterns
        if '..' in url or url.count('/') > 10:
            return False, "URL contains suspicious patterns"
        
        return True, None
        
    except Exception as e:
        return False, f"Invalid URL: {str(e)}"


def sanitize_filename(filename: str) -> str:
    """Sanitize filename for safe file system usage"""
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    # Remove control characters
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    # Limit length
    if len(filename) > 200:
        filename = filename[:200]
    # Remove leading/trailing dots and spaces
    filename = filename.strip('. ')
    # Default if empty
    if not filename:
        filename = "unnamed"
    
    return filename


def timeout_handler(timeout_seconds: int = 60):
    """Decorator to add timeout handling to functions
    
    Note: Uses threading-based timeout for cross-platform compatibility
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            import concurrent.futures
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                try:
                    result = future.result(timeout=timeout_seconds)
                    return result
                except concurrent.futures.TimeoutError:
                    raise TimeoutError(f"Operation timed out after {timeout_seconds} seconds")
        
        return wrapper
    return decorator


def extract_domain(url: str) -> Optional[str]:
    """Extract domain from URL for display purposes"""
    try:
        parsed = urlparse(url)
        return parsed.netloc
    except:
        return None


def format_file_size(size_bytes: int) -> str:
    """Format bytes to human readable size"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


def chunk_text(text: str, max_length: int = 5000) -> list[str]:
    """Split text into chunks for processing"""
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Try to split on paragraphs first
    paragraphs = text.split('\n\n')
    
    for para in paragraphs:
        if len(current_chunk) + len(para) + 2 <= max_length:
            if current_chunk:
                current_chunk += "\n\n"
            current_chunk += para
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = para
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks


def safe_json_parse(text: str) -> Optional[Dict[str, Any]]:
    """Safely parse JSON with multiple fallback strategies"""
    # Direct parse
    try:
        return json.loads(text)
    except:
        pass
    
    # Look for JSON in code blocks
    json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    matches = re.findall(json_pattern, text)
    for match in matches:
        try:
            return json.loads(match)
        except:
            pass
    
    # Look for JSON objects
    json_obj_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
    matches = re.findall(json_obj_pattern, text)
    for match in matches:
        try:
            return json.loads(match)
        except:
            pass
    
    # Look for JSON arrays
    json_arr_pattern = r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]'
    matches = re.findall(json_arr_pattern, text)
    for match in matches:
        try:
            return json.loads(match)
        except:
            pass
    
    return None


def rate_limit_check(key: str, max_requests: int = 10, 
                    window_seconds: int = 60) -> Tuple[bool, Optional[str]]:
    """Simple rate limiting check
    
    Returns:
        Tuple of (is_allowed, error_message)
    """
    # This is a placeholder for actual rate limiting implementation
    # In production, you'd want to use Redis or similar
    return True, None


def get_progress_message(step: int, total_steps: int, message: str) -> Dict[str, Any]:
    """Create progress update message for web UI"""
    return {
        "type": "progress",
        "step": step,
        "total_steps": total_steps,
        "percentage": round((step / total_steps) * 100),
        "message": message,
        "timestamp": datetime.now().isoformat()
    }