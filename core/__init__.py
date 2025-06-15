"""Core module for auto-apply"""
from .claude import ClaudeMCP, ClaudeMCPError
from .scraper import WebScraper, WebScraperError
from .processor import process_application, save_results, process_application_web
from .utils import (
    sanitize_filename, 
    create_response, 
    create_error_response,
    get_progress_message,
    validate_url,
    url_cache,
    safe_json_parse,
    chunk_text
)
from .prompts import PromptTemplates

__all__ = [
    'ClaudeMCP',
    'ClaudeMCPError',
    'WebScraper', 
    'WebScraperError',
    'process_application',
    'save_results',
    'process_application_web',
    'sanitize_filename',
    'create_response',
    'create_error_response',
    'get_progress_message',
    'validate_url',
    'url_cache',
    'safe_json_parse',
    'chunk_text',
    'PromptTemplates'
]