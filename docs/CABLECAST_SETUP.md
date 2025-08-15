# Cablecast HTTP Basic Authentication Setup Guide

## Overview

This guide explains how to configure HTTP Basic Authentication for the Cablecast VOD integration in the Archivist application. The system now uses HTTP Basic Authentication instead of JWT tokens, as required by the Cablecast API.

## Environment Variables

You need to set the following environment variables in your `.env` file:

```bash
# Cablecast Server Configuration
CABLECAST_SERVER_URL=https://rays-house.cablecast.net
CABLECAST_USER_ID=admin
CABLECAST_PASSWORD=rwscctrms
CABLECAST_LOCATION_ID=your_location_id

```

## Step-by-Step Setup

### 1. Get Your Cablecast Credentials

1. **Access your Cablecast instance**: Go to `https://rays-house.cablecast.net`
2. **Login to the admin interface** with your credentials
3. **Navigate to API settings** (usually under Admin → API or Settings → API)
4. **Note your credentials**:
   - Username (usually your Cablecast login username)
   - Password (your Cablecast login password)
   - Location ID (found in the API settings or location management)

### 2. Configure Environment Variables

Create or update your `.env` file in the project root:

```bash
# Copy the example environment file
cp .env.example .env

# Edit the .env file with your credentials
nano .env
```

Add your Cablecast credentials:

```bash
# Cablecast Configuration
CABLECAST_SERVER_URL=https://rays-house.cablecast.net
CABLECAST_USER_ID=your_actual_username
CABLECAST_PASSWORD=your_actual_password
CABLECAST_LOCATION_ID=123456
```

### 3. Test the Connection

Run the authentication test script:

```bash
# Make the script executable
chmod +x scripts/test_cablecast_auth.py

# Run the test
python scripts/test_cablecast_auth.py
```

Expected output for successful authentication:

```
🚀 Cablecast HTTP Basic Authentication Test
==================================================
🔍 Checking environment variables...
🌐 Server URL: https://rays-house.cablecast.net
👤 User ID: your_username
🔑 Password: SET

🔐 Testing HTTP Basic Authentication manually...
🌐 Testing connection to: https://rays-house.cablecast.net/api/v1/shows
👤 Username: your_username
🔑 Password: ********
📊 Response Status: 200
✅ Authentication successful!
📺 Found 15 shows

🔧 Testing CablecastAPIClient class...
✅ CablecastAPIClient connection successful!
📺 Retrieved 5 shows
🎬 Retrieved 3 VODs
📍 Retrieved 2 locations

==================================================
📋 Test Summary:
🔐 Manual Auth: ✅ PASS
🔧 Client Class: ✅ PASS

🎉 All tests passed! HTTP Basic Authentication is working correctly.
```

### 4. Troubleshooting

#### Authentication Failed (401 Error)

If you get a 401 error:

1. **Check credentials**: Verify your username and password are correct
2. **Check URL**: Ensure `CABLECAST_SERVER_URL` points to your correct Cablecast instance
3. **Check permissions**: Ensure your user has API access permissions
4. **Check location ID**: Verify the `CABLECAST_LOCATION_ID` is correct

#### Connection Error

If you get a connection error:

1. **Check network**: Ensure your server can reach the Cablecast instance
2. **Check firewall**: Verify no firewall is blocking the connection
3. **Check SSL**: Ensure the URL uses HTTPS and the certificate is valid
4. **Check DNS**: Verify the domain name resolves correctly

#### Timeout Error

If you get a timeout:

1. **Increase timeout**: Set `REQUEST_TIMEOUT=60` in your `.env` file
2. **Check network**: Verify network connectivity to the Cablecast server
3. **Check server load**: The Cablecast server might be under heavy load

## API Endpoints

Once authenticated, you can access these endpoints:

### Shows
- `GET /api/v1/shows` - List all shows
- `GET /api/v1/shows/{id}` - Get specific show
- `POST /api/v1/shows` - Create new show

### VODs
- `GET /api/v1/vods` - List all VODs
- `GET /api/v1/vods/{id}` - Get specific VOD
- `POST /api/v1/vods` - Create new VOD
- `PUT /api/v1/vods/{id}` - Update VOD
- `DELETE /api/v1/vods/{id}` - Delete VOD

### Captions
- `POST /api/v1/vods/{id}/captions` - Upload SCC caption file

## Security Considerations

### Environment Variables
- **Never commit credentials** to version control
- **Use strong passwords** for your Cablecast account
- **Rotate credentials** regularly
- **Use environment-specific** `.env` files

### Network Security
- **Use HTTPS** for all API communications
- **Verify SSL certificates** are valid
- **Monitor API access** logs
- **Implement rate limiting** to prevent abuse

### Access Control
- **Use dedicated API accounts** if possible
- **Limit permissions** to only what's needed
- **Monitor API usage** for unusual activity
- **Implement IP restrictions** if supported

## Integration with Archivist

Once authentication is working, the Archivist system can:

1. **Auto-link transcriptions** to existing shows
2. **Create new shows** for transcriptions
3. **Upload SCC caption files** to VODs
4. **Manage VOD metadata** and chapters
5. **Monitor VOD processing** status

### Example Usage

```python
from core.services import VODService

# Initialize VOD service
vod_service = VODService()

# Test connection
if vod_service.test_connection():
    print("Connected to Cablecast!")
    
    # Get shows
    shows = vod_service.get_shows()
    print(f"Found {len(shows)} shows")
    
    # Link transcription to show
    result = vod_service.link_transcription_to_show("transcription_id", show_id=123)
    print(f"Linking result: {result}")
```

## Support

If you continue to have issues:

1. **Check the logs**: Look for detailed error messages in the application logs
2. **Test manually**: Use curl or Postman to test the API directly
3. **Contact Cablecast support**: For issues with the Cablecast API itself
4. **Check documentation**: Review the Cablecast API documentation at your instance URL

## Example curl Commands

Test the API manually:

```bash
# Test authentication
curl -u "username:password" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  "https://rays-house.cablecast.net/api/v1/shows"

# Get specific show
curl -u "username:password" \
  -H "Content-Type: application/json" \
  "https://rays-house.cablecast.net/api/v1/shows/123"

# Get VODs
curl -u "username:password" \
  -H "Content-Type: application/json" \
  "https://rays-house.cablecast.net/api/v1/vods"
``` 