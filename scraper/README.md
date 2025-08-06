# Minnesota City Website Scraper

A specialized web scraper for extracting PDF documents from Minnesota city government websites.

## Features

- **Multi-Platform Support**: Handles different website platforms including CivicEngage, WordPress, Drupal, and sites with Cloudflare protection
- **Intelligent Parsing**: Uses platform-specific parsing strategies for optimal PDF discovery
- **Respectful Crawling**: Implements proper delays and respects robots.txt
- **Structured Output**: Generates JSON results with city categorization

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

### Debugging

Enable debug logging:

```python
import logging
logging.getLogger('scraper').setLevel(logging.DEBUG)
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