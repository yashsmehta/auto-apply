# Auto-Apply Web Interface

This directory contains the consolidated web interface for the Auto-Apply project.

## Structure

```
web/
├── __init__.py           # Package initialization
├── app.py               # Main Flask application (consolidated from run.py, web_app.py, and app.py)
├── static/
│   ├── app.js          # JavaScript for frontend functionality
│   └── style.css       # Consolidated CSS styles
└── templates/
    └── index.html      # Main HTML template
```

## Key Features

### Endpoints

The Flask app provides the following endpoints:

#### Core API Endpoints
- `GET /` - Serve the web interface
- `POST /crawl/info` or `/api/extract-info` - Extract info from URL
- `POST /crawl/form` or `/api/extract-questions` - Extract questions from form URL
- `POST /process` or `/api/process-single` - Process both URLs in parallel
- `POST /generate-answers` or `/api/generate-answers` - Generate answers from data

#### Utility Endpoints
- `GET /api/health` - Health check
- `POST /api/validate-url` - Validate URL format
- `GET /api/list-results` - List saved results
- `GET /api/get-result/<directory>` - Get specific result
- `POST /api/export/<format>` - Export results (json/markdown)

### Frontend Features

- **URL Validation**: Client and server-side validation
- **Individual Crawling**: Test info/form URLs separately
- **Parallel Processing**: Process both URLs simultaneously
- **Copy to Clipboard**: Copy individual Q&As or all results
- **Export Options**: JSON and Markdown formats
- **Keyboard Shortcuts**: 
  - `Ctrl+Enter` - Submit form
  - `Escape` - Clear results
- **Responsive Design**: Works on mobile and desktop

## Running the Web Interface

From the project root directory:

```bash
# Option 1: Use the run script
python run_web.py

# Option 2: Run the Flask app directly
python -m web.app

# Option 3: Using uv
uv run python run_web.py
```

The server will start at http://localhost:5000

## Differences from Original Files

This consolidated version combines the best features from:
- `run.py` - Base API structure and parallel processing
- `web_app.py` - File saving and result management
- `app.py` - URL validation and export functionality

All endpoints have been unified to work with both old and new naming conventions for backward compatibility.