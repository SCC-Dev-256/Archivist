# Minnesota City Website Scraper

A specialized web scraper for extracting PDF documents from Minnesota city government websites.

## Features

- **Multi-Platform Support**: Handles different website platforms including CivicEngage, WordPress, Drupal, and sites with Cloudflare protection
- **Intelligent Parsing**: Uses platform-specific parsing strategies for optimal PDF discovery
- **Respectful Crawling**: Implements proper delays and respects robots.txt
- **Structured Output**: Generates JSON results with city categorization
- **FilesPipeline-based downloads**: SHA256 checksums, deduplication, and manifest output
- **Prometheus metrics**: Downloads, bytes, duplicates, rejects
- **Early guard middleware**: HEAD checks for Content-Type and Content-Length, offsite blocking, and optional Redis HEAD cache

## Supported Cities

The scraper is configured for the following Minnesota cities:

1. **Oakdale** - CivicEngage platform
2. **Lake Elmo** - CivicEngage platform  
3. **Mahtomedi** - CivicEngage platform
4. **White Bear Lake** - Cloudflare protected site
5. **White Bear Township** - CivicEngage platform
6. **Grant** - Drupal-based site
7. **Birchwood** - WordPress site

## Installation

```bash
pip install -r requirements.txt
## Configuration & Environment

Key environment variables (can be set via shell or `.env`):

```bash
# Absolute path for Scrapy FILES_STORE
export FILES_STORE_PATH=/opt/Archivist/downloads

# Cap individual file size via HEAD Content-Length (bytes)
export MAX_CONTENT_LENGTH=$((200*1024*1024))  # 200MB default

# HEAD cache TTL for downloader middleware (seconds)
export HEAD_CACHE_TTL=3600

# Optional Redis URL for HEAD cache and metrics aggregation
export REDIS_URL=redis://127.0.0.1:6379/0
```

Scrapy settings are wired in `scraper/main.py` and include:
- `ITEM_PIPELINES = { 'scraper.pipelines.PdfFilesPipeline': 100 }`
- `DOWNLOADER_MIDDLEWARES = { 'scraper.middlewares.EarlyGuardMiddleware': 500 }`
- `FILES_EXPIRES = 0`, `MEDIA_ALLOW_REDIRECTS = True`

Outputs:
- Downloaded PDFs under `FILES_STORE_PATH/pdfs/<city>/...`
- Manifest at `FILES_STORE_PATH/manifest.json` with URL, city, checksums, size, and timestamp

Prometheus counters (if `prometheus_client` is installed and a registry is scraped):
- `pdf_downloaded_total`, `pdf_downloaded_bytes_total`, `pdf_duplicates_total`, `pdf_rejected_total`

```

## Usage

### Basic Usage

```python
from scraper.main import CityScraper

# Initialize scraper
scraper = CityScraper()

# Run scraping
results = scraper.run()

# Save results
scraper.save_results("my_results.json")

# Get summary
summary = scraper.get_city_summary()
print(summary)
```

### Command Line

```bash
cd scraper
python -m scraper.main
### CLI (optional)

The project includes a basic CLI for validation, crawl, merge, and webhook notification:

```bash
python -m scraper.cli --config scraper/sites.json \
  --output-dir /opt/Archivist/downloads \
  --merged-output combined_pdfs/all_merged.pdf \
  --max-merge-size $((200*1024*1024))
```

```

## Configuration

The scraper uses `sites.json` to configure target websites. Each site entry includes:

- `url`: The main page to scrape
- `city`: City name for categorization
- `selectors`: CSS selectors for finding PDF links
- `google_drive`: Whether the site uses Google Drive (currently false for all sites)
- `notes`: Additional information about the site structure

### Example Configuration

```json
{
  "url": "https://www.oakdalemn.gov/agendacenter",
  "city": "Oakdale",
  "selectors": [
    "a[href*='/AgendaCenter/ViewFile/']",
    "a[href*='/AgendaCenter/PreviousVersions/']"
  ],
  "google_drive": false,
  "notes": "CivicEngage platform, uses ViewFile endpoints"
}
```

## Platform-Specific Handling

### CivicEngage Platforms
- **Cities**: Oakdale, Lake Elmo, Mahtomedi, White Bear Township
- **Strategy**: Follows ViewFile endpoints to extract actual PDF URLs
- **Selectors**: `a[href*='/AgendaCenter/ViewFile/']`

### WordPress Sites
- **Cities**: Birchwood
- **Strategy**: Direct PDF link extraction with agenda page following
- **Selectors**: `a[href$='.pdf']`, `a[href*='agenda']`

### Drupal Sites
- **Cities**: Grant
- **Strategy**: Deep crawling with agenda page following
- **Selectors**: `a[href$='.pdf']`, `a[href*='agenda']`

### Cloudflare Protected Sites
- **Cities**: White Bear Lake
- **Strategy**: Basic PDF extraction (may require JavaScript rendering)
- **Selectors**: `a[href$='.pdf']`, `a[href*='meeting']`

## Output Format

The scraper generates JSON output with the following structure:

```json
[
  {
    "url": "https://example.com/document.pdf",
    "city": "Oakdale",
    "source": "https://www.oakdalemn.gov/agendacenter"
  }
]
```

## Advanced Usage

### Custom Configuration

```python
from scraper.config import SiteConfig

# Create custom site configuration
custom_site = SiteConfig(
    url="https://example.com/agendas",
    city="Example City",
    selectors=["a[href$='.pdf']"],
    google_drive=False,
    notes="Custom site"
)

# Use with scraper
scraper = CityScraper()
scraper.sites = [custom_site]
results = scraper.run()
```

### Filtering Results

```python
# Filter by city
oakdale_pdfs = [r for r in results if r['city'] == 'Oakdale']

# Filter by URL pattern
agenda_pdfs = [r for r in results if 'agenda' in r['url'].lower()]
```

## Troubleshooting

### Common Issues

1. **No PDFs Found**: Check if the site structure has changed or if selectors need updating
2. **Cloudflare Protection**: Sites with Cloudflare may require JavaScript rendering
3. **Rate Limiting**: The scraper includes delays, but some sites may still block requests

4. **Non-PDF responses rejected**: EarlyGuardMiddleware drops non-`application/pdf` content and oversized files before download.
5. **Duplicates skipped**: Pipeline removes duplicates by SHA256 and records them in the manifest.

### Debugging

Enable debug logging:

```python
import logging
logging.getLogger('scraper').setLevel(logging.DEBUG)

# Scrapy verbose logs
export LOG_LEVEL=DEBUG
```

## Contributing

To add support for new cities:

1. Analyze the website structure
2. Determine the appropriate platform type
3. Add configuration to `sites.json`
4. Test with the scraper
5. Update documentation

## License

This project is for educational and research purposes. Please respect website terms of service and robots.txt files. 