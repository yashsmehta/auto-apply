# Auto-Apply API Documentation

## Overview

The Auto-Apply API provides endpoints for crawling, processing, and generating answers for application forms. The API is built with Flask and supports parallel processing of multiple URLs.

## Base URL

```
http://localhost:5000
```

## Authentication

No authentication is required for API endpoints.

## API Endpoints

### 1. Root Endpoint

**GET /**

Returns API information and available endpoints.

**Response:**
```json
{
  "message": "Auto-Apply API Server",
  "version": "1.0.0",
  "endpoints": {
    "GET /": "This help message",
    "POST /crawl/info": "Crawl and extract info from info URL",
    "POST /crawl/form": "Crawl and extract questions from form URL",
    "POST /process": "Process both URLs in parallel",
    "POST /generate-answers": "Generate answers from info + questions"
  }
}
```

### 2. Crawl Info URL

**POST /crawl/info**

Crawls an information URL (company page, job posting, etc.) and extracts structured information using Claude AI.

**Request Body:**
```json
{
  "url": "https://example.com/about",
  "name": "Example Application"  // optional
}
```

**Success Response (200):**
```json
{
  "success": true,
  "info": {
    "name": "Company Name",
    "description": "Company description...",
    "requirements": ["requirement1", "requirement2"],
    "deadlines": "Application deadline info"
    // Additional fields extracted by Claude
  },
  "url": "https://example.com/about",
  "name": "Example Application"
}
```

**Error Response (400/500):**
```json
{
  "error": "Error message describing what went wrong"
}
```

### 3. Crawl Form URL

**POST /crawl/form**

Crawls an application form URL and extracts all form questions with their metadata.

**Request Body:**
```json
{
  "url": "https://forms.google.com/example",
  "name": "Example Application"  // optional
}
```

**Success Response (200):**
```json
{
  "success": true,
  "questions": [
    {
      "question": "What is your name?",
      "type": "text",
      "required": true
    },
    {
      "question": "Select your experience level",
      "type": "select",
      "required": true,
      "options": ["Entry Level", "Mid Level", "Senior"]
    }
    // Additional questions
  ],
  "url": "https://forms.google.com/example",
  "name": "Example Application"
}
```

**Error Response (400/500):**
```json
{
  "error": "Error message describing what went wrong"
}
```

### 4. Process Both URLs (Parallel)

**POST /process**

Processes both info and form URLs in parallel for faster execution. This is the recommended endpoint for complete processing.

**Request Body:**
```json
{
  "info_url": "https://example.com/about",
  "form_url": "https://forms.google.com/example",
  "name": "Example Application"  // optional
}
```

**Success Response (200):**
```json
{
  "success": true,
  "name": "Example Application",
  "info": {
    // Extracted information object
  },
  "questions": [
    // Array of extracted questions
  ],
  "info_url": "https://example.com/about",
  "form_url": "https://forms.google.com/example"
}
```

**Partial Success Response (500):**
```json
{
  "success": false,
  "errors": [
    "Info crawl failed: Error message",
    "Form crawl failed: Error message"
  ],
  "partial_results": {
    // Any successfully extracted data
  }
}
```

### 5. Generate Answers

**POST /generate-answers**

Generates answers for application questions based on the extracted information using Claude AI.

**Request Body:**
```json
{
  "info": {
    // Information object from crawl/info or process endpoint
  },
  "questions": [
    // Questions array from crawl/form or process endpoint
  ],
  "name": "Example Application"  // optional
}
```

**Success Response (200):**
```json
{
  "success": true,
  "answers": [
    {
      "question": "What is your name?",
      "answer": "Generated answer based on context",
      "confidence": "high",
      "notes": "Additional notes if applicable"
    }
    // Additional answers
  ],
  "name": "Example Application"
}
```

**Error Response (400/500):**
```json
{
  "error": "Error message describing what went wrong"
}
```

## Error Handling

All endpoints return appropriate HTTP status codes:

- **200 OK**: Request succeeded
- **400 Bad Request**: Missing required parameters or invalid request
- **404 Not Found**: Endpoint does not exist
- **500 Internal Server Error**: Server-side error during processing

Error responses always include an `error` field with a descriptive message.

## Usage Examples

### Complete Workflow Example

```bash
# 1. Process both URLs in parallel (recommended)
curl -X POST http://localhost:5000/process \
  -H "Content-Type: application/json" \
  -d '{
    "info_url": "https://example.com/about",
    "form_url": "https://forms.google.com/example",
    "name": "Example Application"
  }'

# 2. Generate answers from the results
curl -X POST http://localhost:5000/generate-answers \
  -H "Content-Type: application/json" \
  -d '{
    "info": { ... },  # From previous response
    "questions": [ ... ],  # From previous response
    "name": "Example Application"
  }'
```

### Individual Endpoint Example

```bash
# Crawl info URL only
curl -X POST http://localhost:5000/crawl/info \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/about"
  }'

# Crawl form URL only
curl -X POST http://localhost:5000/crawl/form \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://forms.google.com/example"
  }'
```

## Performance Notes

- The `/process` endpoint uses parallel execution with a thread pool (4 workers)
- HTML content is limited to 10,000 characters to avoid token limits
- Results are not cached - each request triggers fresh crawling
- Timeouts are handled by the underlying WebScraper and ClaudeMCP modules

## CORS Support

CORS is enabled for all routes, allowing requests from any origin during development.