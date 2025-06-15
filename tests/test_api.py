"""
Tests for Flask API endpoints
Tests all 4 endpoints: /crawl/info, /crawl/form, /process, /generate-answers
"""

import pytest
import json
import os
from unittest.mock import Mock, patch, MagicMock
from concurrent.futures import Future
import sys

# Add parent directory to path to import the Flask app
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run import app, executor


# Load fixture data
FIXTURE_PATH = os.path.join(os.path.dirname(__file__), 'fixtures', 'sample_responses.json')
if os.path.exists(FIXTURE_PATH):
    with open(FIXTURE_PATH, 'r') as f:
        FIXTURES = json.load(f)
else:
    FIXTURES = {
        "sample_info": {
            "company": "Tech Startup",
            "position": "Software Engineer",
            "requirements": ["Python", "Flask", "REST APIs"]
        },
        "sample_questions": [
            {"question": "What is your name?", "type": "text"},
            {"question": "Why do you want this job?", "type": "textarea"}
        ],
        "sample_answers": [
            {"question": "What is your name?", "answer": "John Doe"},
            {"question": "Why do you want this job?", "answer": "I am passionate about technology."}
        ]
    }


@pytest.fixture
def client():
    """Create a test client for the Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestCrawlInfoEndpoint:
    """Test the /crawl/info endpoint"""
    
    def test_valid_url(self, client):
        """Test crawling a valid URL"""
        with patch('run.WebScraper') as mock_scraper_class:
            mock_scraper = Mock()
            mock_scraper.scrape_page.return_value = {
                'success': True,
                'html': '<html><body>Test content</body></html>'
            }
            mock_scraper_class.return_value = mock_scraper
            
            with patch('run.ClaudeMCP') as mock_claude_class:
                mock_claude = Mock()
                mock_claude.call_claude_web.return_value = {
                    'success': True,
                    'data': FIXTURES.get('sample_info')
                }
                mock_claude_class.return_value = mock_claude
                
                response = client.post('/crawl/info',
                    json={'url': 'https://example.com'},
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert 'data' in data
                assert 'Access-Control-Allow-Origin' in response.headers
    
    def test_missing_url(self, client):
        """Test missing URL parameter"""
        response = client.post('/crawl/info',
            json={},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'URL is required' in data['error']
    
    def test_invalid_url(self, client):
        """Test invalid URL format"""
        response = client.post('/crawl/info',
            json={'url': 'not-a-url'},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert 'Invalid URL' in data['error']


class TestCrawlFormEndpoint:
    """Test the /crawl/form endpoint"""
    
    def test_valid_url(self, client):
        """Test crawling a valid form URL"""
        with patch('run.WebScraper') as mock_scraper_class:
            mock_scraper = Mock()
            mock_scraper.scrape_page.return_value = {
                'success': True,
                'html': '<form><input name="name"><textarea name="message"></textarea></form>'
            }
            mock_scraper_class.return_value = mock_scraper
            
            with patch('run.ClaudeMCP') as mock_claude_class:
                mock_claude = Mock()
                mock_claude.call_claude_web.return_value = {
                    'success': True,
                    'data': FIXTURES.get('sample_questions')
                }
                mock_claude_class.return_value = mock_claude
                
                response = client.post('/crawl/form',
                    json={'url': 'https://example.com/form'},
                    content_type='application/json'
                )
                
                assert response.status_code == 200
                data = json.loads(response.data)
                assert data['success'] is True
                assert 'data' in data
                assert isinstance(data['data'], list)


class TestProcessEndpoint:
    """Test the /process endpoint with parallel execution"""
    
    def test_process_both_urls(self, client):
        """Test processing both info and form URLs"""
        # Create mock futures
        info_future = Future()
        form_future = Future()
        
        info_future.set_result({
            'success': True,
            'data': FIXTURES.get('sample_info')
        })
        
        form_future.set_result({
            'success': True,
            'data': FIXTURES.get('sample_questions')
        })
        
        with patch.object(executor, 'submit', side_effect=[info_future, form_future]):
            response = client.post('/process',
                json={
                    'name': 'Test Application',
                    'info_url': 'https://example.com/info',
                    'form_url': 'https://example.com/form'
                },
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'info' in data['data']
            assert 'questions' in data['data']
    
    def test_missing_parameters(self, client):
        """Test missing required parameters"""
        response = client.post('/process',
            json={'name': 'Test'},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False


class TestGenerateAnswersEndpoint:
    """Test the /generate-answers endpoint"""
    
    def test_generate_answers(self, client):
        """Test generating answers from info and questions"""
        with patch('run.ClaudeMCP') as mock_claude_class:
            mock_claude = Mock()
            mock_claude.call_claude_web.return_value = {
                'success': True,
                'data': FIXTURES.get('sample_answers')
            }
            mock_claude_class.return_value = mock_claude
            
            response = client.post('/generate-answers',
                json={
                    'info': FIXTURES.get('sample_info'),
                    'questions': FIXTURES.get('sample_questions')
                },
                content_type='application/json'
            )
            
            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'data' in data
            assert isinstance(data['data'], list)
    
    def test_missing_data(self, client):
        """Test missing info or questions"""
        response = client.post('/generate-answers',
            json={'info': {}},
            content_type='application/json'
        )
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False


class TestCORSHeaders:
    """Test CORS headers on all endpoints"""
    
    def test_cors_headers(self, client):
        """Test that CORS headers are present"""
        endpoints = [
            ('/crawl/info', {'url': 'https://example.com'}),
            ('/crawl/form', {'url': 'https://example.com'}),
            ('/process', {'name': 'Test', 'info_url': 'https://example.com', 'form_url': 'https://example.com'}),
            ('/generate-answers', {'info': {}, 'questions': []})
        ]
        
        for endpoint, data in endpoints:
            with patch('run.WebScraper'), patch('run.ClaudeMCP'):
                response = client.post(endpoint, json=data, content_type='application/json')
                assert 'Access-Control-Allow-Origin' in response.headers
                assert response.headers['Access-Control-Allow-Origin'] == '*'