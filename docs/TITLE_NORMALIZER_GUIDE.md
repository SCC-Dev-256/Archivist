# Title Normalizer CLI Tool for Cablecast

## Overview

The Title Normalizer CLI Tool is a Python-based command-line utility designed to automatically normalize show titles in Cablecast systems. It identifies shows with date patterns in the format `(M/D/YY)` and converts them to a standardized `YYYY-MM-DD - Title` format.

## Features

- **Automatic Date Detection**: Identifies titles with `(M/D/YY)` date patterns
- **Smart Normalization**: Converts dates to ISO format and moves them to the title prefix
- **Dry-Run Mode**: Preview changes without making actual updates
- **CSV Export**: Export processing results for audit trails
- **Pagination Support**: Handles large numbers of shows efficiently
- **Project Filtering**: Process shows from specific projects only
- **Comprehensive Logging**: Detailed logging with configurable verbosity
- **Error Handling**: Robust error handling with detailed reporting

## Installation

### Prerequisites

- Python 3.8 or higher
- Access to Cablecast API
- Valid API token

### Setup

1. Ensure you have the required dependencies:
```bash
pip install requests loguru
```

2. The tool is located at `core/chronologic_order.py` and can be run directly:
```bash
python core/chronologic_order.py --help
```

## Usage

### Basic Usage

```bash
# Test connection to Cablecast API
python core/chronologic_order.py --token YOUR_API_TOKEN --test-connection

# Preview changes (dry-run mode)
python core/chronologic_order.py --token YOUR_API_TOKEN --dry-run

# Apply changes to all shows
python core/chronologic_order.py --token YOUR_API_TOKEN

# Process shows from a specific project
python core/chronologic_order.py --token YOUR_API_TOKEN --project-id 123

# Export results to CSV
python core/chronologic_order.py --token YOUR_API_TOKEN --export-csv results.csv
```

### Command Line Options

| Option | Required | Description |
|--------|----------|-------------|
| `--token` | Yes | Cablecast API token |
| `--base-url` | No | Cablecast server URL (default: https://cablecast.example.com) |
| `--project-id` | No | Filter shows by project ID |
| `--dry-run` | No | Preview changes without updating |
| `--export-csv` | No | Export results to CSV file |
| `--verbose` | No | Enable verbose logging |
| `--test-connection` | No | Test API connection and exit |

### Examples

#### 1. Test Connection
```bash
python core/chronologic_order.py --token abc123 --test-connection
```

#### 2. Preview Changes
```bash
python core/chronologic_order.py --token abc123 --dry-run --verbose
```

#### 3. Process Specific Project
```bash
python core/chronologic_order.py --token abc123 --project-id 456 --dry-run
```

#### 4. Apply Changes with Export
```bash
python core/chronologic_order.py --token abc123 --export-csv normalization_results.csv
```

## Title Normalization Logic

### Input Patterns

The tool recognizes titles with date patterns in the format `(M/D/YY)`:

- `Grant City Council (6/3/25)`
- `Board Meeting (12/25/24)`
- `Special Event (1/1/30)`

### Output Format

Titles are normalized to `YYYY-MM-DD - Title` format:

- `Grant City Council (6/3/25)` → `2025-06-03 - Grant City Council`
- `Board Meeting (12/25/24)` → `2024-12-25 - Board Meeting`
- `Special Event (1/1/30)` → `1930-01-01 - Special Event`

### Year Handling

- Years 00-29 are interpreted as 2000-2029
- Years 30-99 are interpreted as 1930-1999

### Skipped Titles

Titles are skipped if:
- No date pattern is found
- Title is already normalized
- Date components are invalid (e.g., month > 12, day > 31)

## API Integration

### Endpoints Used

- `GET /cablecastapi/v1/shows` - Fetch shows with pagination
- `PUT /cablecastapi/v1/shows/{show_id}` - Update show title

### Authentication

The tool uses Bearer token authentication:
```
Authorization: Bearer YOUR_API_TOKEN
```

### Pagination

The tool automatically handles pagination:
- Fetches 100 shows per request
- Continues until all shows are retrieved
- Supports project filtering via query parameters

## Output and Reporting

### Console Output

The tool provides detailed console output including:
- Connection status
- Processing progress
- Summary statistics
- Error details

Example output:
```
2024-01-15 10:30:00 | INFO     | chronologic_order:main:250 - ✓ Cablecast API connection successful
2024-01-15 10:30:01 | INFO     | chronologic_order:get_all_shows:150 - Total shows fetched: 1,250
2024-01-15 10:30:02 | INFO     | chronologic_order:process_shows:200 - Processing 1,250 shows...
2024-01-15 10:30:05 | INFO     | chronologic_order:process_shows:250 - [DRY RUN] Would update show 123:
2024-01-15 10:30:05 | INFO     | chronologic_order:process_shows:251 -   Old: Grant City Council (6/3/25)
2024-01-15 10:30:05 | INFO     | chronologic_order:process_shows:252 -   New: 2025-06-03 - Grant City Council

==================================================
PROCESSING SUMMARY
==================================================
Total shows: 1,250
Processed: 45
Updated: 45
Skipped: 1,205
Errors: 0
```

### CSV Export

When using `--export-csv`, the tool creates a CSV file with columns:
- `show_id`: Cablecast show ID
- `original_title`: Original show title
- `new_title`: Normalized title (if applicable)
- `action`: Action taken (updated, skipped, error)
- `reason`: Reason for action

## Error Handling

### Common Errors

1. **Authentication Failed (401)**
   - Check API token validity
   - Verify token permissions

2. **Connection Failed**
   - Verify Cablecast server URL
   - Check network connectivity

3. **Invalid Date Patterns**
   - Tool automatically skips invalid dates
   - Check logs for specific issues

### Troubleshooting

#### Connection Issues
```bash
# Test connection first
python core/chronologic_order.py --token YOUR_TOKEN --test-connection

# Check with verbose logging
python core/chronologic_order.py --token YOUR_TOKEN --test-connection --verbose
```

#### Permission Issues
- Ensure API token has read/write permissions for shows
- Verify project access if using `--project-id`

#### Date Pattern Issues
- Review logs for specific title patterns
- Check if dates are in expected `(M/D/YY)` format

## Best Practices

### Before Running

1. **Always test connection first**
   ```bash
   python core/chronologic_order.py --token YOUR_TOKEN --test-connection
   ```

2. **Use dry-run mode initially**
   ```bash
   python core/chronologic_order.py --token YOUR_TOKEN --dry-run
   ```

3. **Export results for audit**
   ```bash
   python core/chronologic_order.py --token YOUR_TOKEN --export-csv audit.csv
   ```

### Production Usage

1. **Backup your data** before running in production
2. **Run during maintenance windows** to minimize impact
3. **Monitor logs** for any unexpected behavior
4. **Verify results** after processing

### Performance Considerations

- Tool processes shows in batches of 100
- Large datasets may take several minutes
- Use project filtering to reduce processing time
- Consider running during off-peak hours

## Integration with Archivist

The Title Normalizer integrates with the existing Archivist codebase:

### Dependencies
- Uses `core.cablecast_client` patterns
- Follows `core.exceptions` error handling
- Implements `loguru` logging standards

### Code Structure
```
core/chronologic_order.py          # Main CLI tool
tests/test_title_normalizer.py     # Unit tests
docs/TITLE_NORMALIZER_GUIDE.md     # This documentation
```

## Development

### Running Tests

```bash
# Run all tests
pytest tests/test_title_normalizer.py -v

# Run specific test class
pytest tests/test_title_normalizer.py::TestTitleNormalizer -v

# Run with coverage
pytest tests/test_title_normalizer.py --cov=core.chronologic_order
```

### Adding Features

1. **New Date Patterns**: Modify `TitleNormalizer.date_pattern`
2. **Additional Filters**: Add new CLI arguments
3. **Export Formats**: Extend export functionality
4. **API Endpoints**: Add support for additional Cablecast endpoints

### Code Standards

- Follow existing codebase patterns
- Include comprehensive docstrings
- Add unit tests for new functionality
- Update documentation for changes

## Support

For issues or questions:

1. Check the logs for error details
2. Review this documentation
3. Test with dry-run mode first
4. Verify API token and permissions

## Version History

### v1.0
- Initial implementation
- Basic title normalization
- Dry-run mode
- CSV export
- Comprehensive testing
- Full documentation

## License

This tool is part of the Archivist project and follows the same licensing terms. 