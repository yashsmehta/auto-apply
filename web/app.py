#!/usr/bin/env python3
"""
Flask web application for Auto-Apply
Consolidated from run.py, web_app.py, and app.py
Provides both API endpoints and web interface
"""

from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor, as_completed
import os
import json
import tempfile
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Tuple
import traceback
from urllib.parse import urlparse
import re

# Import from parent directory
import sys
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

try:
    from scraper import WebScraper
    from claude import ClaudeMCP
except ImportError:
    # If we can't import from parent, try from core directory
    from core.scraper import WebScraper
    from core.claude import ClaudeMCP

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Configuration
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max request size
app.config['RESULTS_FOLDER'] = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'output')

# Initialize thread pool for parallel execution
executor = ThreadPoolExecutor(max_workers=4)

# URL validation regex pattern
URL_PATTERN = re.compile(
    r'^https?://'  # http:// or https://
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
    r'localhost|'  # localhost...
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
    r'(?::\d+)?'  # optional port
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)


def validate_url(url):
    """Validate URL format and structure"""
    if not url:
        return False, "URL is required"
    
    if not isinstance(url, str):
        return False, "URL must be a string"
    
    # Check against regex pattern
    if not URL_PATTERN.match(url):
        return False, "Invalid URL format"
    
    # Additional validation using urlparse
    try:
        result = urlparse(url)
        if not all([result.scheme, result.netloc]):
            return False, "URL must include protocol (http:// or https://) and domain"
        if result.scheme not in ['http', 'https']:
            return False, "URL protocol must be http or https"
        return True, None
    except Exception:
        return False, "Invalid URL structure"


@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'service': 'auto-apply-web',
        'version': '2.0.0'
    })


@app.route('/api/validate-url', methods=['POST'])
def validate_url_endpoint():
    """Validate a single URL"""
    data = request.json
    url = data.get('url', '')
    
    is_valid, error = validate_url(url)
    
    return jsonify({
        'valid': is_valid,
        'error': error
    })


@app.route('/crawl/info', methods=['POST'])
@app.route('/api/extract-info', methods=['POST'])
def crawl_info():
    """Crawl and extract info from info URL"""
    try:
        data = request.get_json()
        url = data.get('url') or data.get('info_url')
        
        if not url:
            return jsonify({"error": "Missing 'url' in request body"}), 400
        
        # Validate URL
        is_valid, error = validate_url(url)
        if not is_valid:
            return jsonify({"error": error}), 400
        
        app_name = data.get('name', 'Unknown Application')
        
        # Scrape the page
        with WebScraper() as scraper:
            result = scraper.scrape_page(url)
            if not result.get('success'):
                return jsonify({"error": f"Failed to scrape URL: {url}"}), 500
            html = result['html']
        
        # Use Claude to extract structured info
        claude = ClaudeMCP()
        # Limit HTML to first 10k chars to avoid token limits
        html_content = html[:10000]
        prompt = f"""Extract structured information from this HTML page about {app_name}. 
        Focus on: eligibility requirements, deadlines, benefits, program details, and any other important information.
        Return a JSON object with fields like: name, description, requirements, deadlines, etc.
        
        HTML Content:
        {html_content}
        
        Return ONLY valid JSON, no other text."""
        
        response = claude.call_claude(prompt)
        info = claude.extract_json_from_response(response)
        
        if not info:
            return jsonify({"error": "Failed to extract JSON from Claude response"}), 500
        
        return jsonify({
            "success": True,
            "status": "success",
            "info": info,
            "extracted_info": info,  # For compatibility
            "url": url,
            "name": app_name,
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"Error in crawl_info: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route('/crawl/form', methods=['POST'])
@app.route('/api/extract-questions', methods=['POST'])
def crawl_form():
    """Crawl and extract questions from form URL"""
    try:
        data = request.get_json()
        url = data.get('url') or data.get('form_url')
        
        if not url:
            return jsonify({"error": "Missing 'url' in request body"}), 400
        
        # Validate URL
        is_valid, error = validate_url(url)
        if not is_valid:
            return jsonify({"error": error}), 400
        
        app_name = data.get('name', 'Unknown Application')
        
        # Scrape the page
        with WebScraper() as scraper:
            result = scraper.scrape_page(url)
            if not result.get('success'):
                return jsonify({"error": f"Failed to scrape URL: {url}"}), 500
            html = result['html']
        
        # Use Claude to extract form questions
        claude = ClaudeMCP()
        # Limit HTML to first 10k chars
        html_content = html[:10000]
        prompt = f"""Extract all form questions from this HTML page for {app_name}. 
        Look for input fields, textareas, select dropdowns, radio buttons, checkboxes, and their labels.
        Return a JSON object with an array of questions, each containing:
        - question: the question text
        - type: text/textarea/select/checkbox/radio
        - required: boolean
        - options: array (if applicable)
        
        HTML Content:
        {html_content}
        
        Return ONLY valid JSON, no other text."""
        
        response = claude.call_claude(prompt)
        questions_data = claude.extract_json_from_response(response)
        
        if not questions_data:
            return jsonify({"error": "Failed to extract JSON from Claude response"}), 500
        
        # Ensure it's a list
        if isinstance(questions_data, dict) and 'questions' in questions_data:
            questions = questions_data['questions']
        elif isinstance(questions_data, list):
            questions = questions_data
        else:
            questions = []
        
        return jsonify({
            "success": True,
            "status": "success",
            "questions": questions,
            "url": url,
            "name": app_name,
            "total_questions": len(questions),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"Error in crawl_form: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500
def _crawl_info_helper(url: str, app_name: str) -> Tuple[bool, Dict[str, Any]]:
    """Helper function for parallel info crawling"""
    try:
        with WebScraper() as scraper:
            result = scraper.scrape_page(url)
            if not result.get('success'):
                return False, {"error": f"Failed to scrape info URL: {url}"}
            html = result['html']
        
        claude = ClaudeMCP()
        html_content = html[:10000]
        prompt = f"""Extract structured information from this HTML page about {app_name}. 
        Return a JSON object with fields like: name, description, requirements, deadlines, etc.
        
        HTML Content:
        {html_content}
        
        Return ONLY valid JSON, no other text."""
        
        response = claude.call_claude(prompt)
        info = claude.extract_json_from_response(response)
        
        if not info:
            return False, {"error": "Failed to extract info JSON"}
        
        return True, {"info": info, "url": url}
    except Exception as e:
        return False, {"error": str(e)}


def _crawl_form_helper(url: str, app_name: str) -> Tuple[bool, Dict[str, Any]]:
    """Helper function for parallel form crawling"""
    try:
        with WebScraper() as scraper:
            result = scraper.scrape_page(url)
            if not result.get('success'):
                return False, {"error": f"Failed to scrape form URL: {url}"}
            html = result['html']
        
        claude = ClaudeMCP()
        html_content = html[:10000]
        prompt = f"""Extract all form questions from this HTML page for {app_name}. 
        Return a JSON object with an array of questions, each containing:
        - question: the question text
        - type: text/textarea/select/checkbox/radio
        - required: boolean
        - options: array (if applicable)
        
        HTML Content:
        {html_content}
        
        Return ONLY valid JSON, no other text."""
        
        response = claude.call_claude(prompt)
        questions_data = claude.extract_json_from_response(response)
        
        if not questions_data:
            return False, {"error": "Failed to extract questions JSON"}
        
        questions = questions_data.get('questions', questions_data) if isinstance(questions_data, dict) else questions_data
        return True, {"questions": questions, "url": url}
    except Exception as e:
        return False, {"error": str(e)}


@app.route('/process', methods=['POST'])
@app.route('/api/process-single', methods=['POST'])
def process():
    """Process both URLs in parallel"""
    try:
        data = request.get_json()
        info_url = data.get('info_url')
        form_url = data.get('form_url')
        
        if not info_url or not form_url:
            return jsonify({"error": "Missing 'info_url' or 'form_url' in request body"}), 400
        
        # Validate URLs
        for url, name in [(info_url, "Info URL"), (form_url, "Form URL")]:
            is_valid, error = validate_url(url)
            if not is_valid:
                return jsonify({"error": f"{name}: {error}"}), 400
        
        app_name = data.get('name', f"Application_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        # Submit both tasks to thread pool
        future_info = executor.submit(_crawl_info_helper, info_url, app_name)
        future_form = executor.submit(_crawl_form_helper, form_url, app_name)
        
        # Wait for both to complete
        results = {
            "name": app_name,
            "timestamp": datetime.now().isoformat()
        }
        errors = []
        
        # Get info results
        info_success, info_data = future_info.result()
        if info_success:
            results['info'] = info_data['info']
            results['info_url'] = info_url
        else:
            errors.append(f"Info crawl failed: {info_data['error']}")
        
        # Get form results
        form_success, form_data = future_form.result()
        if form_success:
            results['questions'] = form_data['questions']
            results['form_url'] = form_url
        else:
            errors.append(f"Form crawl failed: {form_data['error']}")
        
        # Generate answers if both succeeded
        if info_success and form_success:
            claude = ClaudeMCP()
            prompt = f"""Based on the following information about {app_name}, generate appropriate answers for the application questions.
            
            Application Information:
            {json.dumps(results['info'], indent=2)}
            
            Questions to Answer:
            {json.dumps(results['questions'], indent=2)}
            
            Return a JSON object with an array of answers, each containing:
            - question: the original question
            - answer: your generated answer
            - confidence: low/medium/high
            - notes: any additional notes (optional)
            
            Make answers professional, specific, and tailored to the application.
            Return ONLY valid JSON, no other text."""
            
            response = claude.call_claude(prompt)
            answers_data = claude.extract_json_from_response(response)
            
            if answers_data:
                answers = answers_data.get('answers', answers_data) if isinstance(answers_data, dict) else answers_data
                results['answers'] = answers
            
            # Save results
            save_results(app_name, results)
        
        # Return results
        if errors:
            results['errors'] = errors
            results['success'] = False
            return jsonify(results), 500 if len(errors) == 2 else 200
        
        results['success'] = True
        return jsonify(results)
        
    except Exception as e:
        app.logger.error(f"Error in process: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": str(e), "success": False}), 500


@app.route('/generate-answers', methods=['POST'])
@app.route('/api/generate-answers', methods=['POST'])
def generate_answers():
    """Generate answers from info + questions"""
    try:
        data = request.get_json()
        info = data.get('info') or data.get('application_info', {})
        questions = data.get('questions', [])
        
        if not questions:
            return jsonify({"error": "Questions are required"}), 400
        
        app_name = data.get('name', 'Unknown Application')
        
        # Use Claude to generate answers
        claude = ClaudeMCP()
        prompt = f"""Based on the following information about {app_name}, generate appropriate answers for the application questions.
        Be concise but thorough. 
        
        Application Information:
        {json.dumps(info, indent=2)}
        
        Questions to Answer:
        {json.dumps(questions, indent=2)}
        
        Return a JSON object with an array of answers, each containing:
        - question: the original question
        - answer: your generated answer
        - confidence: low/medium/high (optional)
        - notes: any additional notes (optional)
        
        Make answers professional, specific, and tailored to the application.
        Return ONLY valid JSON, no other text."""
        
        response = claude.call_claude(prompt)
        answers_data = claude.extract_json_from_response(response)
        
        if not answers_data:
            return jsonify({"error": "Failed to extract JSON from Claude response"}), 500
        
        # Ensure it's a list
        if isinstance(answers_data, dict) and 'answers' in answers_data:
            answers = answers_data['answers']
        elif isinstance(answers_data, list):
            answers = answers_data
        else:
            answers = []
        
        return jsonify({
            "success": True,
            "status": "success",
            "answers": answers,
            "name": app_name,
            "total_answers": len(answers),
            "timestamp": datetime.now().isoformat()
        })
        
    except Exception as e:
        app.logger.error(f"Error in generate_answers: {str(e)}\n{traceback.format_exc()}")
        return jsonify({"error": str(e)}), 500


@app.route('/api/process-application', methods=['POST'])
def process_application():
    """Process a complete application (info + form + answers) - legacy endpoint"""
    # Redirect to the new process endpoint
    return process()


@app.route('/api/list-results', methods=['GET'])
def list_results():
    """List all saved results"""
    try:
        results_dir = app.config['RESULTS_FOLDER']
        if not os.path.exists(results_dir):
            return jsonify({'results': []})
        
        results = []
        for app_dir in os.listdir(results_dir):
            app_path = os.path.join(results_dir, app_dir)
            if os.path.isdir(app_path):
                results_file = os.path.join(app_path, 'results.json')
                if os.path.exists(results_file):
                    with open(results_file, 'r') as f:
                        data = json.load(f)
                        results.append({
                            'app_name': data.get('app_name', app_dir),
                            'timestamp': data.get('timestamp'),
                            'status': data.get('status', 'success' if data.get('answers') else 'partial'),
                            'directory': app_dir
                        })
        
        # Sort by timestamp (newest first)
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return jsonify({'results': results, 'total': len(results)})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/get-result/<directory>', methods=['GET'])
def get_result(directory):
    """Get a specific result by directory name"""
    try:
        from werkzeug.utils import secure_filename
        directory = secure_filename(directory)
        results_file = os.path.join(app.config['RESULTS_FOLDER'], directory, 'results.json')
        
        if not os.path.exists(results_file):
            return jsonify({'error': 'Result not found'}), 404
        
        with open(results_file, 'r') as f:
            data = json.load(f)
        
        # Check if answers.md exists
        answers_file = os.path.join(app.config['RESULTS_FOLDER'], directory, 'answers.md')
        if os.path.exists(answers_file):
            with open(answers_file, 'r') as f:
                data['answers_markdown'] = f.read()
        
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/<format>', methods=['POST'])
def export_results(format):
    """Export results in requested format (json or markdown)"""
    data = request.json
    
    if format not in ['json', 'markdown']:
        return jsonify({'error': 'Invalid format. Use json or markdown'}), 400
    
    try:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == 'json':
            # Create JSON file
            filename = f'auto_apply_results_{timestamp}.json'
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                json.dump(data, tmp, indent=2)
                temp_path = tmp.name
            
            return send_file(
                temp_path,
                as_attachment=True,
                download_name=filename,
                mimetype='application/json'
            )
            
        else:  # markdown
            # Create markdown file
            filename = f'auto_apply_answers_{timestamp}.md'
            with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as tmp:
                tmp.write(f"# Auto-Apply Results\n")
                tmp.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                # Handle single result or multiple results
                results = data if isinstance(data, list) else [data]
                
                for result in results:
                    if 'name' in result:
                        tmp.write(f"## {result['name']}\n\n")
                    
                    if 'answers' in result and result['answers']:
                        tmp.write("### Answers\n\n")
                        for item in result['answers']:
                            tmp.write(f"**Q: {item.get('question', 'Unknown')}**\n")
                            tmp.write(f"A: {item.get('answer', 'No answer provided')}\n\n")
                    
                    if 'error' in result and result['error']:
                        tmp.write(f"**Error:** {result['error']}\n\n")
                    
                    tmp.write("---\n\n")
                
                temp_path = tmp.name
            
            return send_file(
                temp_path,
                as_attachment=True,
                download_name=filename,
                mimetype='text/markdown'
            )
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def save_results(app_name: str, results: Dict[str, Any]):
    """Save results for an application"""
    # Create directory for this application
    app_dir = os.path.join(app.config['RESULTS_FOLDER'], app_name.replace('/', '_'))
    os.makedirs(app_dir, exist_ok=True)
    
    # Add metadata
    results['app_name'] = app_name
    if 'timestamp' not in results:
        results['timestamp'] = datetime.now().isoformat()
    
    # Save full results as JSON
    with open(os.path.join(app_dir, 'results.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    # Save answers in a readable format
    if 'answers' in results and results['answers']:
        with open(os.path.join(app_dir, 'answers.md'), 'w', encoding='utf-8') as f:
            f.write(f"# Answers for {app_name}\n\n")
            f.write(f"Generated on: {results.get('timestamp', 'Unknown')}\n\n")
            
            for i, qa in enumerate(results['answers'], 1):
                f.write(f"## Question {i}\n")
                f.write(f"**{qa.get('question', 'Unknown question')}**\n\n")
                f.write(f"{qa.get('answer', 'No answer provided')}\n\n")
                if 'confidence' in qa:
                    f.write(f"*Confidence: {qa['confidence']}*\n\n")
                if 'notes' in qa:
                    f.write(f"*Notes: {qa['notes']}*\n\n")
                f.write("---\n\n")


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    # Create output directory if it doesn't exist
    os.makedirs(app.config['RESULTS_FOLDER'], exist_ok=True)
    
    # Run the Flask development server
    print("Starting Auto-Apply Flask server...")
    print("Server running at http://localhost:5001")
    print("Press Ctrl+C to stop")
    
    app.run(
        host='127.0.0.1',
        port=5001,
        debug=False,  # Disable debug to prevent auto-reloader
        threaded=True
    )