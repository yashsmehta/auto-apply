"""Flask web server for auto-apply"""
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor
import os
from typing import Dict, Any

from core import (
    ClaudeMCP, 
    WebScraper, 
    process_application_web,
    create_response,
    create_error_response,
    validate_url
)
from core.claude_sdk import HTMLContentProcessor
from core.prompts import PromptTemplates

app = Flask(__name__)
CORS(app)

# Thread pool for parallel processing
executor = ThreadPoolExecutor(max_workers=4)

# Initialize shared resources
claude = ClaudeMCP(use_cache=True, timeout=120)
scraper = WebScraper(use_cache=True)
prompt_templates = PromptTemplates()
html_processor = HTMLContentProcessor()


@app.route('/')
def index():
    """Serve the main web interface"""
    return render_template('index.html')


@app.route('/crawl/info', methods=['POST'])
def crawl_info():
    """Crawl and extract information from info URL"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        # Validate URL
        is_valid, error_msg = validate_url(url)
        if not is_valid:
            return jsonify(create_error_response(error_msg, "validation_error")), 400
        
        # Scrape the page
        scrape_result = scraper.scrape_page(url)
        if not scrape_result.get('success'):
            return jsonify(create_error_response(
                "Failed to scrape the page",
                "scraping_error"
            )), 500
        
        # Prepare HTML for Claude
        html_content = html_processor.prepare_html_for_claude(
            scrape_result['html'],
            max_chars=8000
        )
        
        # Extract information using Claude
        template = prompt_templates.get_template('info_extraction')
        prompt = template.format_prompt(html_content=html_content)
        
        claude_result = claude.call_claude(prompt)
        if not claude_result.get('success'):
            return jsonify(create_error_response(
                "Failed to extract information",
                "extraction_error"
            )), 500
        
        # Parse the response
        info_data, error_msg = claude.extract_json_from_response(
            claude_result['response']
        )
        
        if error_msg:
            return jsonify(create_error_response(
                f"Failed to parse extraction results: {error_msg}",
                "parsing_error"
            )), 500
        
        # Format for web display
        formatted_info = claude.format_application_info(info_data)
        
        return jsonify(create_response(
            success=True,
            data={
                'extracted_info': formatted_info,
                'raw_data': info_data,
                'processing_time': claude_result.get('processing_time', 0)
            }
        ))
        
    except Exception as e:
        return jsonify(create_error_response(str(e))), 500


@app.route('/crawl/form', methods=['POST'])
def crawl_form():
    """Crawl and extract questions from application form URL"""
    try:
        data = request.get_json()
        url = data.get('url', '').strip()
        
        # Validate URL
        is_valid, error_msg = validate_url(url)
        if not is_valid:
            return jsonify(create_error_response(error_msg, "validation_error")), 400
        
        # Scrape the page
        scrape_result = scraper.scrape_page(url)
        if not scrape_result.get('success'):
            return jsonify(create_error_response(
                "Failed to scrape the form",
                "scraping_error"
            )), 500
        
        # Prepare HTML for Claude
        html_content = html_processor.prepare_html_for_claude(
            scrape_result['html'],
            max_chars=8000
        )
        
        # Extract questions using Claude
        template = prompt_templates.get_template('question_extraction')
        prompt = template.format_prompt(html_content=html_content)
        
        claude_result = claude.call_claude(prompt)
        if not claude_result.get('success'):
            return jsonify(create_error_response(
                "Failed to extract questions",
                "extraction_error"
            )), 500
        
        # Parse the response
        questions_data, error_msg = claude.extract_json_from_response(
            claude_result['response']
        )
        
        if error_msg:
            return jsonify(create_error_response(
                f"Failed to parse questions: {error_msg}",
                "parsing_error"
            )), 500
        
        # Format for web display
        formatted_questions = claude.format_questions_for_display(questions_data)
        
        return jsonify(create_response(
            success=True,
            data={
                'questions': formatted_questions,
                'total_questions': len(formatted_questions),
                'processing_time': claude_result.get('processing_time', 0)
            }
        ))
        
    except Exception as e:
        return jsonify(create_error_response(str(e))), 500


@app.route('/process', methods=['POST'])
def process():
    """Process both URLs in parallel"""
    try:
        data = request.get_json()
        name = data.get('name', 'Unnamed Application')
        info_url = data.get('info_url', '').strip()
        form_url = data.get('form_url', '').strip()
        
        # Validate URLs
        for url, url_type in [(info_url, 'info'), (form_url, 'form')]:
            is_valid, error_msg = validate_url(url)
            if not is_valid:
                return jsonify(create_error_response(
                    f"Invalid {url_type} URL: {error_msg}",
                    "validation_error"
                )), 400
        
        # Process application
        result = process_application_web(
            app_name=name,
            info_url=info_url,
            application_url=form_url,
            scraper=scraper,
            claude=claude
        )
        
        return jsonify(result), result.get('status_code', 200)
        
    except Exception as e:
        return jsonify(create_error_response(str(e))), 500


@app.route('/generate-answers', methods=['POST'])
def generate_answers():
    """Generate answers from extracted info and questions"""
    try:
        data = request.get_json()
        info_data = data.get('info', {})
        questions = data.get('questions', [])
        
        if not info_data or not questions:
            return jsonify(create_error_response(
                "Both info and questions are required",
                "validation_error"
            )), 400
        
        # Generate answers using Claude
        template = prompt_templates.get_template('answer_generation')
        prompt = template.format_prompt(
            application_info=info_data,
            questions=questions
        )
        
        claude_result = claude.call_claude(prompt)
        if not claude_result.get('success'):
            return jsonify(create_error_response(
                "Failed to generate answers",
                "generation_error"
            )), 500
        
        # Parse the response
        answers_data, error_msg = claude.extract_json_from_response(
            claude_result['response']
        )
        
        if error_msg:
            return jsonify(create_error_response(
                f"Failed to parse answers: {error_msg}",
                "parsing_error"
            )), 500
        
        # Format for review
        formatted_answers = claude.format_answers_for_review(answers_data)
        
        return jsonify(create_response(
            success=True,
            data={
                'answers': formatted_answers,
                'processing_time': claude_result.get('processing_time', 0)
            }
        ))
        
    except Exception as e:
        return jsonify(create_error_response(str(e))), 500


if __name__ == '__main__':
    # Ensure output directory exists
    os.makedirs('output', exist_ok=True)
    
    # Run the Flask app
    app.run(debug=True, port=5001)