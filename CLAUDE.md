# Auto-Apply Project Structure

## Project Overview
Auto-Apply is an automated application form processor that uses web scraping and Claude AI to automatically fill out application forms. The system provides both a web interface and CLI for processing applications. It scrapes application websites, extracts form questions, and generates appropriate answers using Claude's AI capabilities.

## Directory Structure
```
/auto-apply/
├── README.md                    # Project documentation
├── pyproject.toml              # Python project configuration (uses UV package manager)
├── uv.lock                     # UV package lock file
├── CLAUDE.md                   # This file - project structure documentation
├── MIGRATION_LOG.md            # Record of recent refactoring changes
│
├── core/                       # Core business logic modules
│   ├── __init__.py            # Package exports
│   ├── scraper.py             # Web scraping with Crawl4AI
│   ├── claude.py              # Claude AI integration (MCP + formatting)
│   ├── prompts.py             # Prompt templates for Claude
│   ├── processor.py           # Main application processing logic
│   └── utils.py               # Shared utilities and caching
│
├── web/                        # Web interface
│   ├── __init__.py            # Package initialization
│   ├── app.py                 # Flask application with all endpoints
│   ├── static/
│   │   ├── app.js             # Frontend JavaScript
│   │   └── style.css          # Consolidated styles
│   └── templates/
│       └── index.html         # Web UI template
│
├── cli.py                      # CLI entry point for batch processing
│
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── test_api.py            # API endpoint tests
│   ├── test_scraper.py        # Web scraper tests
│   ├── test_claude.py         # Claude integration tests
│   ├── test_cli.py            # CLI functionality tests
│   └── fixtures/              # Test data and mock responses
│
├── docs/                       # Documentation
│   ├── API.md                 # API endpoint reference
│   ├── CLAUDE_SETUP.md        # Claude CLI/MCP setup guide
│   └── CRAWL4AI_REFERENCE.md  # Crawl4AI usage reference
│
├── examples/                   # Example files
│   ├── applications.csv       # Sample CSV for batch processing
│   ├── sample_urls.txt        # Test URLs for various platforms
│   └── sample_complete_result.json  # Example output format
│
└── output/                     # Results directory (gitignored)
    └── {app_name}/            # Directory per application
        ├── results.json       # Complete processing data
        └── answers.md         # Human-readable Q&A format
```

## Key Components

### Core Modules (`core/`)

#### scraper.py
- **Purpose**: Web scraping using Crawl4AI
- **Class**: `WebScraper` - Async crawler with sync wrapper
- **Features**:
  - Built-in caching with configurable TTL
  - URL validation and security checks
  - Statistics tracking
  - Structured error responses

#### claude.py
- **Purpose**: Claude AI integration (merged from claude_mcp.py + claude_helpers.py)
- **Classes**:
  - `ClaudeMCP` - Claude CLI/MCP wrapper
  - `ClaudeResponseFormatter` - Response formatting
  - `HTMLContentProcessor` - HTML optimization
  - `ApplicationStateManager` - Session state tracking
- **Features**:
  - Request ID tracking
  - Response caching
  - Chunk processing for large content
  - Multiple JSON extraction strategies

#### prompts.py
- **Purpose**: Prompt templates for Claude operations
- **Classes**:
  - `PromptTemplates` - Template manager
  - `InfoExtractionTemplate` - Extract info from pages
  - `QuestionExtractionTemplate` - Extract form questions
  - `AnswerGenerationTemplate` - Generate answers
- **Features**:
  - Consistent JSON output formats
  - Customizable prompts
  - Example-based prompting

#### processor.py
- **Purpose**: Main processing logic
- **Functions**:
  - `process_application()` - Core processing workflow
  - `process_application_web()` - Web-friendly wrapper
  - `save_results()` - Save outputs to disk
- **Features**:
  - Orchestrates scraping, extraction, and generation
  - Progress callbacks
  - Error handling

#### utils.py
- **Purpose**: Shared utilities
- **Classes**:
  - `URLCache` - Thread-safe caching
- **Functions**:
  - URL validation and sanitization
  - JSON parsing and extraction
  - Response formatting
  - Text chunking

### Web Interface (`web/`)

#### app.py
- **Purpose**: Flask web server with REST API
- **Endpoints**:
  - `GET /` - Serve web interface
  - `POST /crawl/info` - Extract info from URL
  - `POST /crawl/form` - Extract questions from form
  - `POST /process` - Process both URLs in parallel
  - `POST /generate-answers` - Generate answers
  - `GET /results` - List saved results
  - `GET /results/<name>` - Get specific result
- **Features**:
  - Parallel URL processing with ThreadPoolExecutor
  - CORS support
  - File saving for web results
  - HTML template rendering

#### static/app.js
- **Purpose**: Frontend JavaScript
- **Features**:
  - URL validation
  - Real-time processing status
  - Copy to clipboard
  - Export (JSON/Markdown)
  - Keyboard shortcuts

### CLI Interface

#### cli.py
- **Purpose**: Command-line interface for batch processing
- **Usage**: `python cli.py [options]`
- **Options**:
  - `--no-cache` - Disable caching
  - `--verbose` - Enable verbose output
  - `-o/--output` - Custom output directory
- **Features**:
  - CSV batch processing
  - Progress tracking
  - Continues on individual failures

## Workflows

### Web Interface Workflow
```
1. User Input:
   Web Form → Enter Info URL + Application URL
   
2. Parallel Processing:
   Info URL → Crawl4AI → Claude Extract Info ─┐
                                               ├→ Claude Generate Answers
   Form URL → Crawl4AI → Claude Extract Questions ─┘
   
3. Output:
   - Real-time display in web UI
   - Save to output/{app_name}/
   - Export as JSON or Markdown
```

### CLI Batch Processing Workflow
```
1. Input:
   CSV File → Read applications (name, info URL, form URL)
   
2. Processing:
   For each application:
   - Scrape info URL → Extract information
   - Scrape form URL → Extract questions
   - Generate answers using Claude
   
3. Output:
   - output/{app_name}/results.json
   - output/{app_name}/answers.md
```

## Running the Project

### Web Interface (Default)
```bash
# Install dependencies
uv sync

# Run web server (browser opens automatically)
uv run python main.py

# Alternative: Run directly from web directory
uv run python web/app.py
```

### CLI Batch Processing
```bash
# Option 1: Full-featured CLI
uv run python cli.py

# Option 2: Legacy simple CSV processing
uv run python main_csv.py

# CLI with options
uv run python cli.py --no-cache --verbose -o custom_output/
```

### Running Tests
```bash
# Run all tests
uv run pytest tests/

# Run specific test file
uv run pytest tests/test_api.py

# Run with coverage
uv run pytest --cov=core --cov=web tests/
```

## API Reference

See `docs/API.md` for detailed API documentation.

## Key Features

1. **Parallel Processing**: Info and form URLs processed simultaneously
2. **Caching**: In-memory cache reduces redundant API calls
3. **Error Handling**: Graceful failure handling with detailed error messages
4. **Multiple Interfaces**: Both web UI and CLI support
5. **Export Options**: JSON and Markdown output formats
6. **URL Validation**: Security checks before processing
7. **Progress Tracking**: Real-time status updates

## Recent Changes

See `MIGRATION_LOG.md` for details on the recent refactoring that:
- Consolidated multiple Flask implementations
- Flattened directory structure for simplicity
- Merged related modules (claude_mcp.py + claude_helpers.py)
- Simplified test organization
- Removed duplicate files and unused code

## Technologies Used

- **Python 3.8+**: Core language
- **UV**: Modern Python package manager
- **Crawl4AI**: Async web crawler
- **Flask**: Web framework
- **Claude CLI/MCP**: AI integration
- **Bootstrap**: Web UI styling
- **pytest**: Testing framework