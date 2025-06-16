"""Main processing logic for auto-apply"""
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from .claude import ClaudeMCP, ClaudeMCPError
from .scraper import WebScraper, WebScraperError
from .utils import create_response, create_error_response, sanitize_filename, get_progress_message


def process_application(app: Dict[str, str], scraper: WebScraper, claude: ClaudeMCP,
                       progress_callback: Optional[callable] = None) -> Dict[str, Any]:
    """Process a single application with enhanced error handling
    
    Args:
        app: Application data dict
        scraper: WebScraper instance
        claude: ClaudeMCP instance
        progress_callback: Optional callback for progress updates
        
    Returns:
        Dict with processing results
    """
    print(f"\nProcessing: {app['app_name']}")
    results = {
        'app_name': app['app_name'],
        'timestamp': datetime.now().isoformat(),
        'info_url': app['info_url'],
        'application_url': app['application_url'],
        'processing_steps': []
    }
    
    total_steps = 6  # Total number of processing steps
    current_step = 0
    
    def update_progress(message: str):
        nonlocal current_step
        current_step += 1
        if progress_callback:
            progress_callback(get_progress_message(current_step, total_steps, message))
        print(f"  [{current_step}/{total_steps}] {message}")
        results['processing_steps'].append({
            'step': current_step,
            'message': message,
            'timestamp': datetime.now().isoformat()
        })
    
    try:
        # Step 1: Scrape info page
        update_progress(f"Scraping info page: {app['info_url']}")
        try:
            # Use new enhanced method but handle legacy usage
            scrape_result = scraper.scrape_page(app['info_url'])
            if isinstance(scrape_result, dict) and scrape_result.get('success'):
                info_html = scrape_result['html']
                results['info_scrape_details'] = scrape_result.get('details', {})
            else:
                # Legacy fallback
                info_html = scraper.scrape_page_simple(app['info_url'])
        except WebScraperError as e:
            raise Exception(f"Failed to scrape info page: {str(e)}")
        
        if not info_html:
            raise Exception("Failed to scrape info page - no content returned")
        
        # Step 2: Extract key information using Claude
        update_progress("Extracting application information...")
        info_prompt = f"""Analyze this HTML page and extract key information about this application/program.
        Focus on: eligibility requirements, deadlines, benefits, program details, and any other important information.
        Return the information as a JSON object with clear keys and values.
        
        HTML content:
        {info_html[:5000]}  # Limit to first 5k chars for context
        """
        
        try:
            # Use enhanced method
            claude_result = claude.call_claude(info_prompt)
            if isinstance(claude_result, dict) and claude_result.get('success'):
                info_response = claude_result['response']
                results['info_extraction_details'] = claude_result.get('metadata', {})
            else:
                # Legacy fallback
                info_response = claude.call_claude_simple(info_prompt)
        except ClaudeMCPError as e:
            raise Exception(f"Failed to extract information: {str(e)}")
        
        info_data, error_msg = claude.extract_json_from_response(info_response)
        if error_msg:
            results['info_extraction_warning'] = error_msg
        results['application_info'] = info_data or {'raw_response': info_response}
        
        # Step 3: Scrape application page
        update_progress(f"Scraping application page: {app['application_url']}")
        try:
            scrape_result = scraper.scrape_page(app['application_url'])
            if isinstance(scrape_result, dict) and scrape_result.get('success'):
                app_html = scrape_result['html']
                results['app_scrape_details'] = scrape_result.get('details', {})
            else:
                app_html = scraper.scrape_page_simple(app['application_url'])
        except WebScraperError as e:
            raise Exception(f"Failed to scrape application page: {str(e)}")
        
        if not app_html:
            raise Exception("Failed to scrape application page - no content returned")
        
        # Step 4: Extract questions using Claude
        update_progress("Extracting application questions...")
        questions_prompt = f"""Analyze this HTML page and extract all form questions/fields from this application.
        Look for input fields, textareas, select dropdowns, radio buttons, checkboxes, and their labels.
        Return as a JSON array where each item has 'question' (the label/question text) and 'type' (text/textarea/select/radio/checkbox).
        
        HTML content:
        {app_html[:5000]}  # Limit to first 5k chars
        """
        
        try:
            claude_result = claude.call_claude(questions_prompt)
            if isinstance(claude_result, dict) and claude_result.get('success'):
                questions_response = claude_result['response']
                results['questions_extraction_details'] = claude_result.get('metadata', {})
            else:
                questions_response = claude.call_claude_simple(questions_prompt)
        except ClaudeMCPError as e:
            raise Exception(f"Failed to extract questions: {str(e)}")
        
        questions_data, error_msg = claude.extract_json_from_response(questions_response)
        if error_msg:
            results['questions_extraction_warning'] = error_msg
        
        if not questions_data or not isinstance(questions_data, list):
            # Try to parse as object with questions array
            if isinstance(questions_data, dict) and 'questions' in questions_data:
                questions_data = questions_data['questions']
            else:
                questions_data = []
        
        results['questions'] = questions_data
        
        # Step 5: Generate answers using Claude
        update_progress("Generating answers...")
        answers_prompt = f"""Based on the application information and questions below, generate appropriate answers for each question.
        Be concise but thorough. Return as a JSON array with 'question' and 'answer' for each item.
        
        Application Info:
        {json.dumps(results['application_info'], indent=2)}
        
        Questions to answer:
        {json.dumps(questions_data, indent=2)}
        """
        
        try:
            claude_result = claude.call_claude(answers_prompt)
            if isinstance(claude_result, dict) and claude_result.get('success'):
                answers_response = claude_result['response']
                results['answers_generation_details'] = claude_result.get('metadata', {})
            else:
                answers_response = claude.call_claude_simple(answers_prompt)
        except ClaudeMCPError as e:
            raise Exception(f"Failed to generate answers: {str(e)}")
        
        answers_data, error_msg = claude.extract_json_from_response(answers_response)
        if error_msg:
            results['answers_extraction_warning'] = error_msg
        
        if not answers_data or not isinstance(answers_data, list):
            # Try to parse as object with answers array
            if isinstance(answers_data, dict) and 'answers' in answers_data:
                answers_data = answers_data['answers']
            else:
                answers_data = []
        
        results['answers'] = answers_data
        
        # Step 6: Finalize results
        update_progress("Processing complete")
        results['status'] = 'success'
        results['total_questions'] = len(questions_data)
        results['total_answers'] = len(answers_data)
        
    except Exception as e:
        print(f"  Error: {str(e)}")
        results['status'] = 'error'
        results['error'] = str(e)
        results['error_type'] = type(e).__name__
    
    return results


def process_application_web(app_name: str, info_url: str, application_url: str,
                          scraper: Optional[WebScraper] = None,
                          claude: Optional[ClaudeMCP] = None,
                          progress_callback: Optional[callable] = None) -> Dict[str, Any]:
    """Web UI friendly version of process_application
    
    Returns structured response suitable for JSON API
    """
    # Create instances if not provided
    if not scraper:
        scraper = WebScraper(use_cache=True)
    if not claude:
        claude = ClaudeMCP(use_cache=True)
    
    app = {
        'app_name': app_name,
        'info_url': info_url,
        'application_url': application_url
    }
    
    try:
        results = process_application(app, scraper, claude, progress_callback)
        
        # Transform for web response
        if results['status'] == 'success':
            return create_response(
                success=True,
                data={
                    'application': app_name,
                    'timestamp': results['timestamp'],
                    'application_info': results.get('application_info', {}),
                    'questions': results.get('questions', []),
                    'answers': results.get('answers', []),
                    'statistics': {
                        'total_questions': results.get('total_questions', 0),
                        'total_answers': results.get('total_answers', 0),
                        'processing_steps': len(results.get('processing_steps', []))
                    },
                    'processing_details': {
                        'steps': results.get('processing_steps', []),
                        'scraping': {
                            'info_page': results.get('info_scrape_details', {}),
                            'application_page': results.get('app_scrape_details', {})
                        },
                        'claude': {
                            'info_extraction': results.get('info_extraction_details', {}),
                            'questions_extraction': results.get('questions_extraction_details', {}),
                            'answers_generation': results.get('answers_generation_details', {})
                        }
                    }
                }
            )
        else:
            return create_error_response(
                error=results.get('error', 'Unknown error'),
                error_type=results.get('error_type', 'processing_error'),
                status_code=500
            )
            
    except Exception as e:
        return create_error_response(
            error=str(e),
            error_type=type(e).__name__,
            status_code=500
        )


def save_results(app_name: str, results: Dict[str, Any]):
    """Save results for an application"""
    # Create directory for this application
    safe_app_name = sanitize_filename(app_name)
    app_dir = os.path.join('output', safe_app_name)
    os.makedirs(app_dir, exist_ok=True)
    
    # Save full results as JSON
    with open(os.path.join(app_dir, 'results.json'), 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    # Save answers in a readable format
    if 'answers' in results:
        with open(os.path.join(app_dir, 'answers.md'), 'w', encoding='utf-8') as f:
            f.write(f"# Answers for {app_name}\n\n")
            f.write(f"Generated on: {results.get('timestamp', 'Unknown')}\n\n")
            
            for i, qa in enumerate(results['answers'], 1):
                f.write(f"## Question {i}\n")
                f.write(f"**{qa['question']}**\n\n")
                f.write(f"{qa['answer']}\n\n")
                f.write("---\n\n")