# Enhanced Claude AI Integration for Web UI

This document describes the enhanced Claude AI integration for the auto-apply system, optimized for web UI usage.

## Overview

The enhanced integration provides:
- Request ID tracking for debugging
- Improved error handling with user-friendly messages
- Customizable prompt templates
- Retry logic with exponential backoff
- Web-optimized response formatting
- State management for tracking progress
- Validation utilities

## Key Components

### 1. Enhanced Claude MCP (`claude_mcp.py`)

The core Claude integration with improvements:

```python
from claude_mcp import ClaudeMCP, ClaudeError

# Initialize with custom timeout
claude = ClaudeMCP(timeout=120)  # 2 minutes for complex requests

# Call with request tracking
response, request_id = claude.call_claude(prompt, request_id="custom-id-123")

# Use templates
data, request_id = claude.call_with_template(
    "info_extraction",
    html_content=html
)
```

**Features:**
- Request ID tracking for every Claude call
- Custom timeout configuration
- Built-in prompt templates
- Multiple JSON extraction strategies
- Detailed error messages with context

### 2. Helper Utilities (`claude_helpers.py`)

Web UI formatting and state management:

```python
from claude_helpers import ClaudeResponseFormatter, ApplicationStateManager

# Format errors for web display
formatter = ClaudeResponseFormatter()
error_response = formatter.format_error_for_web(exception, request_id)

# Track application processing state
state_manager = ApplicationStateManager()
session_id = state_manager.create_state("My Application")
state_manager.update_step(session_id, "info_extraction", "completed")
```

### 3. Prompt Templates (`prompt_templates.py`)

Customizable templates for consistent responses:

```python
from prompt_templates import PromptTemplates

templates = PromptTemplates()

# Customize a template
templates.customize_template("info_extraction", {
    "system_prompt": "You are specialized in grant applications...",
    "examples": [{"input": "...", "output": {...}}]
})

# Get formatted prompt
template = templates.get_template("info_extraction")
prompt = template.format_prompt(html_content=html)
```

### 4. Web Integration (`claude_web_integration.py`)

High-level API for web applications:

```python
from claude_web_integration import create_web_processor

# Create processor with configuration
processor = create_web_processor({
    "timeout": 120,
    "max_retries": 2,
    "custom_templates": {...}
})

# Process entire application
result = processor.process_application_async(
    app_name="Grant Application",
    info_url="https://example.com/info",
    form_url="https://example.com/apply",
    info_html=info_html,
    form_html=form_html
)
```

## Web API Example

The `web_api_example.py` file provides a complete Flask API implementation:

### Endpoints

1. **POST /api/process** - Process entire application
2. **POST /api/extract-info** - Extract information from a page
3. **POST /api/extract-questions** - Extract form questions
4. **POST /api/generate-answer** - Generate answer for single question
5. **POST /api/validate-answers** - Validate answers against questions
6. **GET /api/status/<session_id>** - Get processing status

### Example Usage

```bash
# Process an application
curl -X POST http://localhost:5000/api/process \
  -H "Content-Type: application/json" \
  -d '{
    "app_name": "Research Grant",
    "info_url": "https://example.com/grant-info",
    "form_url": "https://example.com/grant-apply"
  }'

# Extract questions from a form
curl -X POST http://localhost:5000/api/extract-questions \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/application-form"
  }'

# Generate answer for a single question
curl -X POST http://localhost:5000/api/generate-answer \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Why are you interested in this program?",
    "context": {
      "program_info": {...}
    },
    "constraints": {
      "max_length": 500
    }
  }'
```

## Error Handling

The enhanced integration provides detailed error information:

```json
{
  "error": true,
  "error_type": "claude_error",
  "message": "Technical error message",
  "request_id": "uuid-123",
  "timestamp": "2025-01-14T10:00:00Z",
  "user_friendly_message": "The request took too long to process..."
}
```

## Response Formatting

All responses are formatted for web display:

### Application Info Format
```json
{
  "formatted": true,
  "sections": [
    {
      "title": "Program Overview",
      "content": {
        "name": "Research Grant Program",
        "description": "..."
      }
    }
  ],
  "raw_data": {...}
}
```

### Questions Format
```json
[
  {
    "id": "q_0",
    "question": "What is your research topic?",
    "type": "textarea",
    "required": true,
    "ui_type": "textarea",
    "validation_rules": {
      "required": true,
      "maxLength": 500
    }
  }
]
```

### Answers Format
```json
{
  "total_questions": 10,
  "high_confidence": 7,
  "medium_confidence": 2,
  "low_confidence": 1,
  "confidence_summary": {
    "percentage_high": 70,
    "needs_review": true
  },
  "answers": [...]
}
```

## Customization

### Custom Prompts

You can provide custom prompts for any step:

```python
result = processor.process_application_async(
    app_name="Custom App",
    info_url=info_url,
    form_url=form_url,
    info_html=info_html,
    form_html=form_html,
    custom_prompts={
        "info_extraction": "Your custom prompt here...",
        "question_extraction": "Extract only specific fields...",
        "answer_generation": "Generate answers in specific style..."
    }
)
```

### Template Customization

Modify templates globally:

```python
processor = create_web_processor({
    "custom_templates": {
        "info_extraction": {
            "system_prompt": "You are an expert in academic grants...",
            "output_format": {
                "custom_field": "description"
            }
        }
    }
})
```

## Best Practices

1. **Timeout Configuration**: Set appropriate timeouts based on content complexity
2. **Error Recovery**: Use retry logic for transient failures
3. **Progress Tracking**: Use session IDs to track long-running operations
4. **Validation**: Always validate answers before submission
5. **HTML Preparation**: Use HTMLContentProcessor to optimize content for Claude

## Debugging

Enable detailed logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Track requests with IDs:
- All Claude calls return a request_id
- Use this ID to trace issues in logs
- Include in error reports for debugging

## Performance Tips

1. **HTML Optimization**: Large HTML files are automatically truncated
2. **Parallel Processing**: Process multiple applications concurrently
3. **Caching**: Consider caching extracted info for similar pages
4. **Template Reuse**: Use templates to avoid prompt duplication

## Installation

```bash
# Install required packages
uv add flask flask-cors

# Run the example API
uv run python web_api_example.py
```

## Security Considerations

1. **Input Validation**: Always validate URLs and HTML content
2. **Rate Limiting**: Implement rate limits for production use
3. **Authentication**: Add auth middleware for production APIs
4. **Content Sanitization**: Sanitize HTML before processing