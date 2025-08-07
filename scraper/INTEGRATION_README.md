# PDF to Flex Server Integration System

A comprehensive integration system that pipes scraped PDFs from Minnesota city websites into your Flex server infrastructure with proper labeling and VOD integration for retranscription.

## 🎯 Overview

This system bridges the gap between your enhanced PDF scraper and your Flex server VOD infrastructure:

1. **Downloads** scraped PDFs from city websites
2. **Uploads** them to appropriate Flex servers by city
3. **Labels** them with proper document types and metadata
4. **Creates VOD entries** for retranscription and streaming
5. **Integrates** with your existing Cablecast API for content management

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   PDF Scraper   │───▶│  Integration     │───▶│  Flex Servers   │
│   (1,000+ PDFs) │    │  System          │    │  (9 locations)  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  VOD System      │
                       │  (Retranscription)│
                       └──────────────────┘
                              │
                              ▼
                       ┌──────────────────┐
                       │  Cablecast API   │
                       │  (Content Mgmt)  │
                       └──────────────────┘
```

## 🗺️ City to Flex Server Mapping

| City | Flex Server | Mount Path | Description |
|------|-------------|------------|-------------|
| **Birchwood** | flex-1 | `/mnt/flex-1` | Birchwood City Council and community content |
| **Dellwood** | flex-2 | `/mnt/flex-2` | Dellwood, Grant, and Willernie combined storage |
| **Grant** | flex-2 | `/mnt/flex-2` | Dellwood, Grant, and Willernie combined storage |
| **Willernie** | flex-2 | `/mnt/flex-2` | Dellwood, Grant, and Willernie combined storage |
| **Lake Elmo** | flex-3 | `/mnt/flex-3` | Lake Elmo City Council and community content |
| **Mahtomedi** | flex-4 | `/mnt/flex-4` | Mahtomedi City Council and community content |
| **flex-5** | ❌ | `/mnt/flex-5` | **Not allocated** |
| **flex-6** | ❌ | `/mnt/flex-6` | **Not allocated** |
| **Oakdale** | flex-7 | `/mnt/flex-7` | Oakdale City Council and community content |
| **White Bear Lake** | flex-8 | `/mnt/flex-8` | White Bear Lake City Council and community content |
| **White Bear Township** | flex-9 | `/mnt/flex-9` | White Bear Township Council and community content |

## 📋 Document Type Detection

The system automatically detects and labels documents:

| Keyword | Document Type |
|---------|---------------|
| `agenda` | City Council Agenda |
| `minutes` | City Council Minutes |
| `packet` | Council Meeting Packet |
| `meeting` | Council Meeting |
| `council` | City Council |
| `resolution` | City Resolution |
| `ordinance` | City Ordinance |

## 🚀 Quick Start

### 1. Test the Integration System

```bash
# Test connectivity and configuration
python3 scraper/test_integration.py
```

### 2. Run the Complete Integration

```bash
# Process all scraped PDFs
python3 scraper/pdf_to_flex_integration.py
```

### 3. Check Results

```bash
# View integration results
cat pdf_integration_results.json
```

## 📁 File Structure

```
scraper/
├── pdf_to_flex_integration.py    # Main integration system
├── test_integration.py           # Integration testing
├── INTEGRATION_README.md         # This documentation
├── sites.json                    # City website configurations
├── enhanced_pdf_spider.py        # Enhanced PDF scraper
└── results/                      # Scraped PDF results
    ├── civicengage_enhanced_results.json
    ├── comprehensive_results.json
    └── downloads/                # Downloaded PDFs
```

## 🔧 Configuration

### API Configuration

```python
# Initialize with custom API settings
integration = PDFToFlexIntegration(
    api_base_url="http://localhost:8000",
    api_key="your_api_key_here"
)
```

### City Mapping Customization

```python
# Add custom city mappings
integration.city_mappings.append(
    CityMapping(
        city="New City",
        flex_server="flex-5", 
        mount_path="/mnt/flex-5",
        description="New city content"
    )
)
```

## 📊 API Endpoints

### Digital File Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/digitalfiles/upload` | POST | Upload PDF to Flex server |
| `/api/digitalfiles/{id}` | GET | Get file information |
| `/api/digitalfiles/{id}/link` | GET | Get streaming URL |
| `/api/digitalfiles/{id}/stream` | GET | Stream file content |
| `/api/digitalfiles/{id}` | DELETE | Delete file |
| `/api/digitalfiles/{id}/rename` | POST | Rename file |
| `/api/digitalfiles/{id}/reindex` | POST | Add to reindexing queue |
| `/api/digitalfiles/city/{city}` | GET | Get city files |

### VOD Integration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/vod/create` | POST | Create VOD entry |
| `/api/vod/publish/{id}` | POST | Publish to VOD |
| `/api/vod/batch-publish` | POST | Batch publish |

## 🔄 Integration Workflow

### 1. PDF Discovery & Download
```python
# Scraper finds PDFs
results = [
    {
        "url": "https://example.com/agenda.pdf",
        "city": "Oakdale",
        "source": "https://www.oakdalemn.gov/agendacenter"
    }
]

# Download and extract metadata
for item in results:
    pdf_path = integration.download_pdf(item['url'], "downloads")
    date = integration._extract_meeting_date(pdf_path.name, item['source'])
    document_type = integration._detect_document_type(pdf_path.name, item['source'])
    meeting_type = integration._detect_meeting_type(pdf_path.name, item['source'])
```

### 2. Cablecast Show Matching
```python
# Find matching Cablecast show (same day only)
if date:
    show_match = integration.find_matching_cablecast_show(city, date, document_type)
    if show_match:
        # PDF will be linked to existing show
        show_id = show_match['show_id']
    else:
        # PDF needs manual review
        unmatched_pdfs.append(pdf)
```

### 3. Upload & VOD Creation
```python
# Upload to appropriate Flex server
upload_result = integration.upload_to_flex_server(pdf_path, city, source)

# Create VOD entry as sidecar file
vod_result = integration.create_vod_entry(
    upload_result['file_id'],
    city,
    document_type,
    show_match  # None if no match found
)
```

### 4. PDF Stitching & Consolidation
```python
# Group PDFs by city and date
grouped_pdfs = stitcher.group_pdfs_by_city_and_date(integration_results)

# Stitch similarly dated PDFs into consolidated documents
for city, date_groups in grouped_pdfs.items():
    for date, pdfs in date_groups.items():
        if len(pdfs) > 1:
            consolidated_pdf = stitcher.stitch_city_date_pdfs(city, date, pdfs)
            # Create VOD entry for consolidated PDF
```

### 5. Final VOD Integration
```python
# Consolidated PDFs are now available for:
# - Streaming with VOD video content
# - Display as sidecar documents
# - Manual review for unmatched PDFs
# - Cablecast show linking
```

## 📈 Expected Results

Based on your scraper success:

| City | Expected PDFs | Flex Server | Status |
|------|---------------|-------------|---------|
| **Oakdale** | 29 | flex-7 | ✅ Ready |
| **Mahtomedi** | 28 | flex-4 | ✅ Ready |
| **White Bear Township** | 30 | flex-9 | ✅ Ready |
| **Grant** | 406 | flex-2 | ✅ Ready |
| **Birchwood** | 512 | flex-1 | ✅ Ready |
| **Total** | **1,005** | **5 servers** | **Ready** |

## 🔍 Monitoring & Debugging

### Check Integration Status

```bash
# Test connectivity
python3 scraper/test_integration.py

# Check Flex server status
curl -X GET "http://localhost:8000/api/mount-points"

# List city documents
curl -X GET "http://localhost:8000/api/digitalfiles/city/Oakdale"
```

### View Integration Logs

```bash
# Check integration results
cat pdf_integration_results.json

# Monitor API logs
tail -f /opt/Archivist/logs/archivist.log
```

### Troubleshooting

| Issue | Solution |
|-------|----------|
| **Flex server not accessible** | Check mount points: `ls -la /mnt/flex-*` |
| **API connection failed** | Verify API is running: `curl http://localhost:8000/health` |
| **PDF download failed** | Check network connectivity and URL accessibility |
| **VOD creation failed** | Verify VOD service is running and configured |

## 🎯 VOD Retranscription Integration

### Automatic Transcription Queue

When PDFs are uploaded with `auto_transcribe: true`:

1. **PDF Detection**: System detects PDF MIME type
2. **Queue Job**: Adds to WhisperX transcription queue
3. **Processing**: Generates SCC captions and summaries
4. **VOD Integration**: Links to Cablecast VOD system
5. **Content Available**: Streamable with captions

### Manual Transcription Trigger

```bash
# Trigger transcription for specific file
curl -X POST "http://localhost:8000/api/transcribe" \
  -H "Content-Type: application/json" \
  -d '{"path": "/mnt/flex-7/city_documents/oakdale/20250115_agenda.pdf"}'
```

## 🔐 Security & Permissions

### File Access Control

- **Upload**: Requires CSRF token and API authentication
- **Download**: Rate-limited to prevent abuse
- **Streaming**: Direct file access with proper MIME types
- **Deletion**: Requires authentication and confirmation

### Data Protection

- **Metadata**: Stored securely in PostgreSQL
- **File Storage**: Organized by city and document type
- **Access Logs**: All operations logged for audit
- **Backup**: Integrated with existing Flex server backup system

## 🚀 Next Steps

### Immediate Actions

1. **Test Integration**: Run `python3 scraper/test_integration.py`
2. **Process PDFs**: Run `python3 scraper/pdf_to_flex_integration.py`
3. **Monitor VOD**: Check transcription queue and VOD system
4. **Verify Content**: Browse uploaded files via web interface

### Future Enhancements

1. **Automated Scheduling**: Daily PDF discovery and integration
2. **Advanced OCR**: PDF text extraction and search indexing
3. **Content Analytics**: Document usage and access patterns
4. **Multi-format Support**: Audio/video file integration
5. **API Extensions**: Additional endpoints for content management

## 📞 Support

For integration issues:

1. **Check Logs**: `/opt/Archivist/logs/archivist.log`
2. **Test Connectivity**: `python3 scraper/test_integration.py`
3. **Verify API**: `curl http://localhost:8000/health`
4. **Review Results**: `cat pdf_integration_results.json`

The integration system is designed to be robust and self-healing, with comprehensive error handling and detailed logging for troubleshooting. 