# Crawl4AI Syntax Reference

## Installation

### Basic Installation
```bash
pip install crawl4ai
```

### Installation with Additional Features
```bash
# With Torch support
pip install crawl4ai[torch]

# With Transformers support
pip install crawl4ai[transformer]

# All features
pip install crawl4ai[all]
```

### Post-Installation Setup
```bash
# Required: Install Playwright browsers and perform OS checks
crawl4ai-setup

# Optional: Diagnostic tool
crawl4ai-doctor

# Optional: Download models for advanced features
crawl4ai-download-models
```

### Docker Installation (Experimental)
```bash
docker pull unclecode/crawl4ai:basic
docker run -p 11235:11235 unclecode/crawl4ai:basic
```

## Basic Usage

### Simple Crawling Example
```python
import asyncio
from crawl4ai import AsyncWebCrawler

async def main():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com")
        print(result.markdown[:300])  # Print first 300 chars

if __name__ == "__main__":
    asyncio.run(main())
```

### With Configuration
```python
import asyncio
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def main():
    browser_conf = BrowserConfig(headless=True)
    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler(config=browser_conf) as crawler:
        result = await crawler.arun(
            url="https://example.com", 
            config=run_conf
        )
        print(result.markdown)

if __name__ == "__main__":
    asyncio.run(main())
```

## AsyncWebCrawler Class

### Constructor Parameters
- `crawler_strategy`: Custom crawler strategy
- `config`: Browser configuration (BrowserConfig instance)
- `base_directory`: Directory for storing caches/logs
- `thread_safe`: Enable concurrency safeguards

### Main Methods

#### arun(url, config)
Primary crawling method for single URLs.
- **Parameters**:
  - `url` (str): Target URL to crawl
  - `config` (CrawlerRunConfig): Configuration for this specific crawl
- **Returns**: CrawlResult object with crawled page details

#### arun_many(urls, config)
Batch URL processing with intelligent resource management.
- **Parameters**:
  - `urls` (list): List of URLs to crawl
  - `config` (CrawlerRunConfig): Configuration for all crawls
- **Returns**: Async generator yielding CrawlResult objects

### Example: Concurrent Crawling
```python
import asyncio
from crawl4ai import AsyncWebCrawler, CrawlerRunConfig, CacheMode

async def quick_parallel_example():
    urls = [
        "https://example.com/page1",
        "https://example.com/page2",
        "https://example.com/page3"
    ]

    run_conf = CrawlerRunConfig(
        cache_mode=CacheMode.BYPASS,
        stream=True  # Enable streaming mode
    )

    async with AsyncWebCrawler() as crawler:
        async for result in await crawler.arun_many(urls, config=run_conf):
            if result.success:
                print(f"[OK] {result.url}, length: {len(result.markdown.raw_markdown)}")
            else:
                print(f"[ERROR] {result.url} => {result.error_message}")
```

## Configuration Classes

### BrowserConfig Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `browser_type` | str | "chromium" | Browser engine (chromium, firefox, webkit) |
| `headless` | bool | True | Run browser without visible UI |
| `viewport_width` | int | 1080 | Initial page width in pixels |
| `viewport_height` | int | 600 | Initial page height in pixels |
| `proxy` | str | None | Single proxy URL for all traffic |
| `user_agent` | str | Chrome-based | Custom browser user agent |
| `use_persistent_context` | bool | False | Maintain browser context across runs |
| `ignore_https_errors` | bool | True | Continue despite invalid certificates |
| `java_script_enabled` | bool | True | Enable/disable JavaScript |
| `light_mode` | bool | False | Disable background features for performance |

### CrawlerRunConfig Parameters

#### Content Processing
- `word_count_threshold` (int, default: ~200): Minimum words for valid content
- `css_selector` (str): Target specific CSS selectors
- `excluded_tags` (list): HTML tags to exclude
- `only_text` (bool, default: False): Extract only text content

#### Caching & Session
- `cache_mode` (CacheMode): Caching strategy (ENABLED, DISABLED, BYPASS, etc.)
- `session_id` (str): Session identifier
- `bypass_cache` (bool, default: False): Force fresh crawl

#### Page Navigation & Timing
- `wait_until` (str, default: "domcontentloaded"): Wait condition
- `page_timeout` (int, default: 60000): Timeout in milliseconds
- `wait_for` (str): CSS selector to wait for
- `check_robots_txt` (bool, default: False): Respect robots.txt

#### Page Interaction
- `js_code` (str/list): JavaScript to execute on page
- `scan_full_page` (bool, default: False): Scroll through entire page
- `simulate_user` (bool, default: False): Simulate user interactions
- `magic` (bool, default: False): Enable automatic interaction detection

#### Media Handling
- `screenshot` (bool, default: False): Capture page screenshot
- `pdf` (bool, default: False): Generate PDF of page

### LLMConfig Parameters
```python
from crawl4ai import LLMConfig

llm_config = LLMConfig(
    provider="openai/gpt-4o-mini",  # LLM provider
    api_token=os.getenv("OPENAI_API_KEY"),  # API key
    base_url=None  # Optional custom base URL
)
```

## Complete Example with All Configurations

```python
import asyncio
import os
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode

async def comprehensive_example():
    # Browser configuration
    browser_config = BrowserConfig(
        browser_type="chromium",
        headless=True,
        viewport_width=1280,
        viewport_height=720,
        user_agent="MyBot/1.0"
    )
    
    # Crawler configuration
    run_config = CrawlerRunConfig(
        # Content processing
        word_count_threshold=10,
        exclude_external_links=True,
        process_iframes=True,
        
        # Caching
        cache_mode=CacheMode.BYPASS,
        
        # Page interaction
        js_code="window.scrollTo(0, document.body.scrollHeight);",
        wait_for="div.content",
        wait_until="networkidle",
        
        # Media
        screenshot=True,
        pdf=False
    )
    
    async with AsyncWebCrawler(config=browser_config) as crawler:
        result = await crawler.arun(
            url="https://example.com",
            config=run_config
        )
        
        if result.success:
            print(f"Title: {result.title}")
            print(f"Content length: {len(result.markdown)}")
            print(f"Links found: {len(result.links['internal'])}")
            
            # Access media
            if result.screenshot:
                print("Screenshot captured")
            
            # Access images
            for image in result.media.get("images", []):
                print(f"Image: {image['src']}")

if __name__ == "__main__":
    asyncio.run(comprehensive_example())
```

## CacheMode Options

```python
from crawl4ai import CacheMode

# Available cache modes:
CacheMode.ENABLED    # Use cache if available
CacheMode.DISABLED   # Don't use cache at all
CacheMode.BYPASS     # Skip cache for this request
CacheMode.REFRESH    # Update cache with new data
```

## Error Handling

```python
async def safe_crawl():
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun("https://example.com")
        
        if result.success:
            print("Crawl successful!")
            print(result.markdown)
        else:
            print(f"Crawl failed: {result.error_message}")
            print(f"Status code: {result.status_code}")
```

## Page Interaction and Dynamic Content

### JavaScript Execution
Execute JavaScript code on the page using the `js_code` parameter:

```python
config = CrawlerRunConfig(
    js_code="window.scrollTo(0, document.body.scrollHeight);"
)
```

Multiple commands can be executed:
```python
js_code = """
document.querySelector('.load-more-button').click();
await new Promise(resolve => setTimeout(resolve, 2000));
"""
```

### Wait Conditions
Two types of wait conditions are supported:

#### CSS-based waiting:
```python
config = CrawlerRunConfig(
    wait_for="css:.content-loaded"
)
```

#### JavaScript-based waiting:
```python
config = CrawlerRunConfig(
    wait_for="js:() => document.querySelectorAll('.item').length > 10"
)
```

### Session Management
Maintain browser sessions across multiple interactions:

```python
# First interaction
result1 = await crawler.arun(
    url="https://example.com",
    session_id="my_session",
    js_code="document.querySelector('#load-more').click();"
)

# Continue in same session
result2 = await crawler.arun(
    url="https://example.com",
    session_id="my_session",
    js_only=True,  # Don't reload page
    js_code="document.querySelector('#load-more').click();"
)
```

### Dynamic Content Handling

#### Loading more content:
```python
config = CrawlerRunConfig(
    js_code="""
    const loadButton = document.querySelector('.load-more');
    if (loadButton) {
        loadButton.click();
        await new Promise(r => setTimeout(r, 3000));
    }
    """,
    wait_for="css:.new-content"
)
```

#### Form interaction:
```python
config = CrawlerRunConfig(
    js_code="""
    document.querySelector('#username').value = 'user';
    document.querySelector('#password').value = 'pass';
    document.querySelector('#submit').click();
    """,
    wait_for="css:.dashboard"
)
```

## Common Use Cases

### Infinite Scroll
```python
config = CrawlerRunConfig(
    js_code="""
    for (let i = 0; i < 5; i++) {
        window.scrollTo(0, document.body.scrollHeight);
        await new Promise(r => setTimeout(r, 2000));
    }
    """,
    wait_for="js:() => document.querySelectorAll('.item').length > 50"
)
```

### Pagination
```python
# Navigate through pages
for page in range(1, 6):
    config = CrawlerRunConfig(
        session_id="pagination_session",
        js_code=f"document.querySelector('.page-{page}').click();",
        wait_for="css:.page-content",
        js_only=page > 1  # Don't reload on subsequent pages
    )
```

### Dynamic Form Submission
```python
config = CrawlerRunConfig(
    js_code="""
    // Fill form
    document.querySelector('#search').value = 'query';
    document.querySelector('#submit').click();
    """,
    wait_for="css:.search-results"
)
```

### Crawl with Custom Headers
```python
browser_config = BrowserConfig(
    extra_headers={
        "Accept-Language": "en-US,en;q=0.9",
        "Custom-Header": "value"
    }
)
```

## Best Practices

1. **Always use context managers** (`async with`) for proper resource cleanup
2. **Configure appropriately**: Use `BrowserConfig` for global settings, `CrawlerRunConfig` for per-crawl settings
3. **Handle errors**: Always check `result.success` before accessing data
4. **Use caching wisely**: Default caching improves performance for repeated crawls
5. **Respect rate limits**: Use delays between requests when crawling multiple pages
6. **Monitor resources**: For batch crawling, `arun_many()` includes automatic resource management
7. **Wait conditions for dynamic content**: Use CSS selectors for simple element presence, JavaScript functions for complex conditions
8. **Session management for multi-step processes**: Use consistent `session_id` across related requests
9. **Error handling in JavaScript**: Check for element existence before interaction, use try-catch blocks
10. **Performance optimization**: Use targeted selectors, minimize JavaScript execution time

## Integration with Auto-Apply

For the auto-apply project, these features can be used to:
1. Handle dynamic application forms that load content via JavaScript
2. Click through multi-page application processes
3. Wait for form fields to become available
4. Submit forms and wait for responses
5. Extract data from dynamically loaded content