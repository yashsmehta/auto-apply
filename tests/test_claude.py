"""Tests for Claude integration module"""
import pytest
import subprocess
import json
import time
from unittest.mock import Mock, patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.claude import ClaudeMCP, ClaudeMCPError


class TestClaudeMCPError:
    """Test custom ClaudeMCPError exception"""
    
    def test_error_creation(self):
        """Test creating ClaudeMCPError with all parameters"""
        error = ClaudeMCPError(
            "Test error",
            error_type="test_error",
            details={"code": 123}
        )
        assert str(error) == "Test error"
        assert error.error_type == "test_error"
        assert error.details == {"code": 123}
    
    def test_error_default_values(self):
        """Test ClaudeMCPError with default values"""
        error = ClaudeMCPError("Simple error")
        assert str(error) == "Simple error"
        assert error.error_type == "claude_error"
        assert error.details == {}


class TestClaudeMCP:
    """Test ClaudeMCP class functionality"""
    
    @pytest.fixture
    def claude(self):
        """Create a ClaudeMCP instance for testing"""
        return ClaudeMCP(work_folder="/tmp", timeout=60, use_cache=False)
    
    @pytest.fixture
    def claude_with_cache(self):
        """Create a ClaudeMCP instance with caching enabled"""
        return ClaudeMCP(use_cache=True)
    
    def test_init(self):
        """Test ClaudeMCP initialization"""
        claude = ClaudeMCP(work_folder="/test", timeout=120, use_cache=True)
        assert claude.work_folder == "/test"
        assert claude.timeout == 120
        assert claude.use_cache is True
        assert claude._stats == {
            "total_calls": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "failures": 0,
            "total_time": 0.0
        }
    
    @patch('subprocess.run')
    def test_call_claude_success(self, mock_run, claude):
        """Test successful Claude call"""
        mock_result = Mock()
        mock_result.stdout = "Test response from Claude"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = claude.call_claude("Test prompt")
        
        assert result == "Test response from Claude"
        assert claude._stats['total_calls'] == 1
        assert claude._stats['cache_misses'] == 1
    
    @patch('subprocess.run')
    def test_call_claude_with_cache_hit(self, mock_run, claude_with_cache):
        """Test Claude call with cache hit"""
        prompt = "Test prompt"
        cached_response = "Cached response"
        
        # Pre-populate cache
        from utils import cache_set
        import hashlib
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()
        cache_set(f"claude:{prompt_hash}", cached_response, ttl=300)
        
        result = claude_with_cache.call_claude(prompt)
        
        assert result == cached_response
        assert claude_with_cache._stats['cache_hits'] == 1
        assert claude_with_cache._stats['total_calls'] == 1
        
        # subprocess.run should not be called
        mock_run.assert_not_called()
    
    @patch('subprocess.run')
    def test_call_claude_failure(self, mock_run, claude):
        """Test Claude call failure"""
        mock_result = Mock()
        mock_result.stdout = ""
        mock_result.stderr = "Error: Failed to process"
        mock_result.returncode = 1
        mock_run.return_value = mock_result
        
        with pytest.raises(ClaudeMCPError) as exc_info:
            claude.call_claude("Test prompt")
        
        assert "Claude command failed" in str(exc_info.value)
        assert exc_info.value.error_type == "command_error"
        assert claude._stats['failures'] == 1
    
    @patch('subprocess.run')
    def test_call_claude_timeout(self, mock_run, claude):
        """Test Claude call timeout"""
        mock_run.side_effect = subprocess.TimeoutExpired("claude", 60)
        
        with pytest.raises(ClaudeMCPError) as exc_info:
            claude.call_claude("Test prompt")
        
        assert "Claude timed out" in str(exc_info.value)
        assert exc_info.value.error_type == "timeout"
    
    @patch('subprocess.run')
    def test_call_claude_web_success(self, mock_run, claude):
        """Test call_claude_web with JSON response"""
        mock_result = Mock()
        mock_result.stdout = json.dumps({"key": "value"})
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = claude.call_claude_web("Test prompt")
        
        assert result['success'] is True
        assert result['data'] == {"key": "value"}
        assert 'request_id' in result
        assert 'timestamp' in result
    
    @patch('subprocess.run')
    def test_call_claude_web_non_json_response(self, mock_run, claude):
        """Test call_claude_web with non-JSON response"""
        mock_result = Mock()
        mock_result.stdout = "Plain text response"
        mock_result.stderr = ""
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        result = claude.call_claude_web("Test prompt")
        
        assert result['success'] is True
        assert result['data'] == "Plain text response"
        assert result.get('raw_response') is True
    
    def test_extract_json_from_response_valid(self, claude):
        """Test extracting valid JSON from response"""
        responses = [
            '{"key": "value"}',
            'Some text\n```json\n{"key": "value"}\n```\nMore text',
            'Text before {"key": "value"} text after'
        ]
        
        for response in responses:
            data, error = claude.extract_json_from_response(response)
            assert data == {"key": "value"}
            assert error is None
    
    def test_extract_json_from_response_invalid(self, claude):
        """Test extracting invalid JSON from response"""
        response = "This is not JSON"
        data, error = claude.extract_json_from_response(response)
        
        assert data is None
        assert "No valid JSON found" in error
    
    def test_extract_json_from_response_array(self, claude):
        """Test extracting JSON array from response"""
        response = '[{"item": 1}, {"item": 2}]'
        data, error = claude.extract_json_from_response(response)
        
        assert data == [{"item": 1}, {"item": 2}]
        assert error is None
    
    def test_get_stats(self, claude):
        """Test getting statistics"""
        stats = claude.get_stats()
        assert isinstance(stats, dict)
        assert 'total_calls' in stats
        assert 'cache_hits' in stats
        assert 'cache_misses' in stats
        assert 'failures' in stats
        assert 'total_time' in stats
        assert 'avg_time_per_call' in stats
        assert 'cache_hit_rate' in stats
    
    def test_reset_stats(self, claude):
        """Test resetting statistics"""
        # Modify stats
        claude._stats['total_calls'] = 10
        claude._stats['cache_hits'] = 5
        
        # Reset
        claude.reset_stats()
        
        # Check all values are reset
        assert claude._stats['total_calls'] == 0
        assert claude._stats['cache_hits'] == 0
        assert claude._stats['cache_misses'] == 0
        assert claude._stats['failures'] == 0
        assert claude._stats['total_time'] == 0.0