# Auto-Apply

A simple tool to automatically scrape application forms, extract questions, and generate answers using Claude MCP. Available as both a command-line tool and a web interface.

## Features

- **Web Scraping**: Extracts content from JavaScript-rendered pages using Crawl4AI
- **AI-Powered Analysis**: Uses Claude to understand application requirements and form questions
- **Automated Answer Generation**: Generates contextual answers based on application information
- **Web Interface**: User-friendly web UI with step-by-step progress tracking
- **REST API**: Programmatic access to all functionality
- **Batch Processing**: Process multiple applications via CSV (CLI mode)

## Setup

1. Install UV package manager:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```

2. Install dependencies:
```bash
uv sync
```

3. Install Claude Code CLI (requires Node.js):
```bash
npm install -g @anthropic-ai/claude-code
```

4. Ensure Claude CLI is installed and accessible in your PATH

## Usage

### Web Interface (Default)

1. Start the web server:
```bash
uv run python main.py
```

2. The browser will automatically open to `http://localhost:5001`

3. Use the web interface to:
   - Enter two URLs: one for company/program info and one for the application form
   - Process both URLs simultaneously to extract information and questions
   - Automatically generate answers based on the extracted information
   - Export results as JSON or Markdown
   - View and manage previous results

### Command-Line Interface

#### Option 1: Full CLI with advanced features
```bash
uv run python cli.py
```
Features: Caching control, verbose output, custom output directory

#### Option 2: Legacy CSV processing (simple)
```bash
uv run python main_csv.py
```

For both options:

1. Create a CSV file (see `examples/applications.csv` for reference) with the following columns:
   - `app_name`: Name of the application
   - `info_url`: URL of the page with application information
   - `application_url`: URL of the actual application form

Example:
```csv
app_name,info_url,application_url
My Fellowship,https://example.com/fellowship,https://example.com/apply
```

2. Results will be saved in the `output/` directory:
   - `output/{app_name}/results.json` - Complete results with all data
   - `output/{app_name}/answers.md` - Human-readable answers

## API Endpoints

### Health Check
- **GET** `/api/health`
  - Returns server status and timestamp

### Extract Information
- **POST** `/api/extract-info`
  - Body: `{"url": "https://example.com"}`
  - Extracts key information from any webpage

### Extract Questions
- **POST** `/api/extract-questions`
  - Body: `{"url": "https://example.com/form"}`
  - Extracts form fields and questions

### Generate Answers
- **POST** `/api/generate-answers`
  - Body: `{"application_info": {...}, "questions": [...]}`
  - Generates answers based on provided context

### Process Application
- **POST** `/api/process-application`
  - Body: `{"app_name": "...", "info_url": "...", "form_url": "..."}`
  - Complete end-to-end processing

### List Results
- **GET** `/api/list-results`
  - Returns all saved results

### Get Result
- **GET** `/api/get-result/{directory}`
  - Returns specific result details

## Testing

Run the test suite to verify all endpoints:

```bash
# Test all endpoints
uv run python test_endpoints.py

# Test specific endpoint
uv run python test_endpoints.py --test extract-info
```

## Example Workflows

### Web UI Workflow

1. **Complete Application Processing**:
   - Enter application name, info URL, and form URL
   - Click "Process Application"
   - Watch real-time progress through all steps
   - Download results as JSON or Markdown

2. **Step-by-Step Processing**:
   - Use "Extract Info Only" to analyze program details
   - Use "Extract Questions Only" to get form fields
   - Use "Generate Answers" with custom inputs
   - Combine results manually as needed

### API Workflow

```python
import requests

# Process a complete application
response = requests.post('http://localhost:5000/api/process-application', json={
    'app_name': 'Summer Program 2024',
    'info_url': 'https://example.com/about',
    'form_url': 'https://example.com/apply'
})

result = response.json()
print(f"Generated {len(result['answers'])} answers")
```

## How it works

1. **Information Extraction**: Scrapes and analyzes program information pages
2. **Form Analysis**: Identifies all form fields, questions, and input types
3. **Answer Generation**: Uses Claude AI to generate contextual, relevant answers
4. **Result Storage**: Saves complete results with both JSON and Markdown formats

## Documentation

- **API Reference**: See `docs/API.md` for detailed API endpoint documentation
- **Claude Setup**: See `docs/CLAUDE_SETUP.md` for Claude CLI configuration
- **Crawl4AI Guide**: See `docs/CRAWL4AI_REFERENCE.md` for advanced scraping options

## Technical Details

- **Web Scraping**: Crawl4AI for efficient JavaScript-rendered page extraction
- **AI Integration**: Claude MCP for natural language processing
- **Web Framework**: Flask with Bootstrap UI
- **Data Format**: JSON for storage, Markdown for human readability

## Notes

- The script uses Crawl4AI for web scraping (handles JavaScript-rendered pages)
- Claude MCP is used for all AI operations (parsing and answering)
- Each application is processed sequentially in CLI mode
- Results are saved even if processing fails (with error details)
- The web server includes CORS support for API access