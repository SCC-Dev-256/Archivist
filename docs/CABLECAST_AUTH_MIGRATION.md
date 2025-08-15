# Cablecast Authentication Migration Guide

## Overview

This document explains the migration from JWT-based authentication to HTTP Basic Authentication for the Cablecast VOD integration. This change was necessary to properly integrate with the Cablecast API as documented at `https://rays-house.cablecast.net/ui/api-docs#auth`.

## What Changed

### Before (JWT Authentication)
- Used JWT tokens with automatic refresh
- Required login endpoint calls
- Complex token management
- Not compatible with Cablecast API

### After (HTTP Basic Authentication)
- Uses standard HTTP Basic Authentication
- Username/password in Authorization header
- Simple and reliable
- Fully compatible with Cablecast API

## Files Modified

### 1. `core/cablecast_client.py`
**Major Changes:**
- Removed JWT authentication logic
- Added HTTP Basic Authentication
- Simplified connection management
- Added comprehensive error handling
- Added additional VOD management methods

**Key Methods Added:**
- `test_connection()` - Test API connectivity
- `get_vod_status()` - Get VOD processing status
- `get_vod_chapters()` - Manage VOD chapters
- `get_locations()` - Get Cablecast locations
- `search_shows()` - Search shows by query
- `wait_for_vod_processing()` - Wait for VOD completion

### 2. `core/config.py`
**Changes:**
- Updated default Cablecast server URL to `https://rays-house.cablecast.net`
- Maintained backward compatibility with existing environment variables

### 3. `web/api/cablecast.py`
**No Changes Required:**
- The API endpoints continue to work unchanged
- All existing functionality is preserved
- New methods are automatically available

## New Files Created

### 1. `scripts/test_cablecast_auth.py`
- Comprehensive authentication test script
- Tests both manual requests and client class
- Provides detailed error reporting
- Helps troubleshoot connection issues

### 2. `scripts/setup_cablecast.py`
- Interactive setup script for configuration
- Securely prompts for credentials
- Updates .env file automatically
- Tests connection after configuration

### 3. `docs/CABLECAST_SETUP.md`
- Complete setup guide
- Troubleshooting information
- Security considerations
- Example usage

### 4. `.env.example`
- Updated with Cablecast configuration variables
- Clear documentation of required settings
- Secure defaults

## Environment Variables

### Required Variables
```bash
CABLECAST_SERVER_URL=https://rays-house.cablecast.net
CABLECAST_USER_ID=your_username
CABLECAST_PASSWORD=your_password
CABLECAST_LOCATION_ID=your_location_id
```

### Optional Variables
```bash
CABLECAST_API_KEY=your_api_key_here  # If required by your instance
```

## Migration Steps

### 1. Update Environment Variables
```bash
# Run the interactive setup script
python scripts/setup_cablecast.py

# Or manually update your .env file
nano .env
```

### 2. Test the Connection
```bash
# Run the authentication test
python scripts/test_cablecast_auth.py
```

### 3. Verify Integration
```bash
# Test the API endpoints
curl -X GET "http://localhost:8000/api/cablecast/health"
```

## Benefits of HTTP Basic Authentication

### 1. Simplicity
- No complex token management
- No refresh logic required
- Standard HTTP authentication

### 2. Reliability
- No token expiration issues
- No re-authentication loops
- Consistent behavior

### 3. Compatibility
- Works with all Cablecast API endpoints
- Standard HTTP authentication
- No custom authentication logic

### 4. Security
- Credentials encrypted in transit (HTTPS)
- No token storage required
- Standard security practices

## API Compatibility

All existing API endpoints continue to work:

### Shows
- `GET /api/cablecast/shows` - List shows
- `GET /api/cablecast/shows/{id}` - Get specific show
- `GET /api/cablecast/search/shows` - Search shows

### VODs
- `GET /api/cablecast/vods` - List VODs
- `GET /api/cablecast/vods/{id}` - Get specific VOD
- `DELETE /api/cablecast/vods/{id}` - Delete VOD
- `PUT /api/cablecast/vods/{id}/metadata` - Update metadata

### Transcriptions
- `POST /api/cablecast/link/{id}` - Auto-link transcription
- `POST /api/cablecast/link/{id}/manual` - Manual link
- `GET /api/cablecast/link/{id}/status` - Get link status
- `DELETE /api/cablecast/link/{id}` - Unlink transcription

### Captions
- `POST /api/cablecast/vods/{id}/captions` - Upload SCC captions

## Troubleshooting

### Common Issues

#### 1. Authentication Failed (401)
- Check username and password
- Verify server URL is correct
- Ensure user has API permissions

#### 2. Connection Error
- Check network connectivity
- Verify firewall settings
- Check SSL certificate validity

#### 3. Timeout Error
- Increase `REQUEST_TIMEOUT` in .env
- Check server load
- Verify network stability

### Debug Commands

```bash
# Test basic connectivity
curl -I https://rays-house.cablecast.net

# Test authentication manually
curl -u "username:password" \
  -H "Content-Type: application/json" \
  "https://rays-house.cablecast.net/api/v1/shows"

# Run full test suite
python scripts/test_cablecast_auth.py
```

## Security Considerations

### 1. Credential Management
- Store credentials in environment variables
- Never commit .env files to version control
- Use strong, unique passwords
- Rotate credentials regularly

### 2. Network Security
- Always use HTTPS
- Verify SSL certificates
- Monitor API access logs
- Implement rate limiting

### 3. Access Control
- Use dedicated API accounts if possible
- Limit permissions to minimum required
- Monitor for unusual activity
- Implement IP restrictions if supported

## Future Enhancements

### 1. Enhanced Error Handling
- More detailed error messages
- Automatic retry with backoff
- Circuit breaker pattern

### 2. Caching
- Cache show and VOD data
- Reduce API calls
- Improve performance

### 3. Monitoring
- API usage metrics
- Error rate monitoring
- Performance tracking

### 4. Advanced Features
- Batch operations
- Webhook support
- Real-time status updates

## Support

For issues with this migration:

1. **Check the logs** for detailed error messages
2. **Run the test script** to verify configuration
3. **Review the setup guide** for troubleshooting steps
4. **Contact Cablecast support** for API-specific issues

## Conclusion

The migration to HTTP Basic Authentication provides a more reliable, secure, and compatible integration with the Cablecast API. The simplified authentication method eliminates the complexity of JWT token management while maintaining all existing functionality.

All existing code continues to work without changes, and new features are automatically available through the enhanced client implementation. 