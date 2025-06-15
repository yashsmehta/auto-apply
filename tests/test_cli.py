"""Tests for the CLI module"""
import pytest
import os
import csv
import tempfile
from unittest.mock import Mock, patch, MagicMock
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli import read_csv, main


class TestReadCSV:
    """Test CSV reading functionality"""
    
    def test_read_valid_csv(self):
        """Test reading a valid CSV file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['app_name', 'info_url', 'application_url', 'context'])
            writer.writerow(['App 1', 'https://info1.com', 'https://app1.com', 'Context 1'])
            writer.writerow(['App 2', 'https://info2.com', 'https://app2.com', ''])
            f.flush()
            
            applications = read_csv(f.name)
            
        os.unlink(f.name)
        
        assert len(applications) == 2
        assert applications[0]['app_name'] == 'App 1'
        assert applications[0]['info_url'] == 'https://info1.com'
        assert applications[0]['application_url'] == 'https://app1.com'
        assert applications[0]['context'] == 'Context 1'
        assert applications[1]['context'] == ''
    
    def test_read_csv_missing_columns(self):
        """Test reading CSV with missing required columns"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['app_name', 'info_url'])  # Missing application_url
            writer.writerow(['App 1', 'https://info1.com'])
            f.flush()
            
            applications = read_csv(f.name)
            
        os.unlink(f.name)
        
        assert len(applications) == 0
    
    def test_read_csv_with_whitespace(self):
        """Test reading CSV with whitespace in values"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['app_name', 'info_url', 'application_url'])
            writer.writerow(['  App 1  ', '  https://info1.com  ', '  https://app1.com  '])
            f.flush()
            
            applications = read_csv(f.name)
            
        os.unlink(f.name)
        
        assert applications[0]['app_name'] == 'App 1'
        assert applications[0]['info_url'] == 'https://info1.com'
        assert applications[0]['application_url'] == 'https://app1.com'


class TestCLIMain:
    """Test main CLI functionality"""
    
    @patch('cli.WebScraper')
    @patch('cli.ClaudeMCP')
    @patch('cli.process_application')
    @patch('cli.save_results')
    def test_main_success(self, mock_save, mock_process, mock_claude_class, mock_scraper_class):
        """Test successful CLI execution"""
        # Create test CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['app_name', 'info_url', 'application_url'])
            writer.writerow(['Test App', 'https://info.com', 'https://app.com'])
            csv_file = f.name
        
        # Mock process_application to return success
        mock_process.return_value = {
            'status': 'success',
            'app_name': 'Test App',
            'answers': []
        }
        
        # Test with the CSV file
        with patch('sys.argv', ['cli.py', csv_file]):
            result = main()
        
        os.unlink(csv_file)
        
        assert result == 0
        assert mock_process.call_count == 1
        assert mock_save.call_count == 1
    
    @patch('cli.WebScraper')
    @patch('cli.ClaudeMCP')
    @patch('cli.process_application')
    def test_main_with_failures(self, mock_process, mock_claude_class, mock_scraper_class):
        """Test CLI execution with some failures"""
        # Create test CSV with multiple apps
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['app_name', 'info_url', 'application_url'])
            writer.writerow(['App 1', 'https://info1.com', 'https://app1.com'])
            writer.writerow(['App 2', 'https://info2.com', 'https://app2.com'])
            csv_file = f.name
        
        # Mock process_application to return one success and one failure
        mock_process.side_effect = [
            {'status': 'success', 'app_name': 'App 1', 'answers': []},
            {'status': 'error', 'error': 'Failed to process'}
        ]
        
        with patch('sys.argv', ['cli.py', csv_file]):
            result = main()
        
        os.unlink(csv_file)
        
        assert result == 1  # Exit code 1 due to failure
        assert mock_process.call_count == 2
    
    def test_main_missing_csv(self):
        """Test CLI with missing CSV file"""
        with patch('sys.argv', ['cli.py', 'nonexistent.csv']):
            result = main()
        
        assert result == 1
    
    def test_main_empty_csv(self):
        """Test CLI with empty CSV file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['app_name', 'info_url', 'application_url'])
            # No data rows
            csv_file = f.name
        
        with patch('sys.argv', ['cli.py', csv_file]):
            result = main()
        
        os.unlink(csv_file)
        
        assert result == 1
    
    @patch('cli.WebScraper')
    @patch('cli.ClaudeMCP')
    def test_main_with_arguments(self, mock_claude_class, mock_scraper_class):
        """Test CLI with command line arguments"""
        # Create test CSV
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerow(['app_name', 'info_url', 'application_url'])
            writer.writerow(['Test App', 'https://info.com', 'https://app.com'])
            csv_file = f.name
        
        # Test with no-cache flag
        with patch('sys.argv', ['cli.py', csv_file, '--no-cache']):
            with patch('cli.process_application') as mock_process:
                mock_process.return_value = {'status': 'success', 'app_name': 'Test App'}
                main()
        
        # Verify ClaudeMCP was created with use_cache=False
        mock_claude_class.assert_called_with(use_cache=False)
        mock_scraper_class.assert_called_with(use_cache=False)
        
        os.unlink(csv_file)