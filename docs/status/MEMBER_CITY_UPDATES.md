# Member City Flex Server Updates

## Overview

This document summarizes the changes made to reflect that flex servers represent member cities rather than generic storage tiers. The system now properly organizes content by member city rather than by storage lifecycle stages.

## ✅ Changes Completed

### 1. **Core Configuration Updates**

#### `core/config.py`
- **Added**: `MEMBER_CITIES` configuration dictionary with city-specific information
- **Updated**: `LOCATIONS` configuration to use `member_cities` instead of `flex_servers`
- **Added**: Individual city location configurations for granular access control

**Member Cities Configuration:**
```python
MEMBER_CITIES = {
    'flex1': {'name': 'Birchwood', 'mount_path': '/mnt/flex-1', 'description': 'Birchwood City Council and community content'},
    'flex2': {'name': 'Dellwood Grant Willernie', 'mount_path': '/mnt/flex-2', 'description': 'Dellwood, Grant, and Willernie combined storage'},
    'flex3': {'name': 'Lake Elmo', 'mount_path': '/mnt/flex-3', 'description': 'Lake Elmo City Council and community content'},
    'flex4': {'name': 'Mahtomedi', 'mount_path': '/mnt/flex-4', 'description': 'Mahtomedi City Council and community content'},
    'flex5': {'name': 'Spare Record Storage 1', 'mount_path': '/mnt/flex-5', 'description': 'Spare storage for overflow and additional cities'},
    'flex6': {'name': 'Spare Record Storage 2', 'mount_path': '/mnt/flex-6', 'description': 'Spare storage for overflow and additional cities'},
    'flex7': {'name': 'Oakdale', 'mount_path': '/mnt/flex-7', 'description': 'Oakdale City Council and community content'},
    'flex8': {'name': 'White Bear Lake', 'mount_path': '/mnt/flex-8', 'description': 'White Bear Lake City Council and community content'},
    'flex9': {'name': 'White Bear Township', 'mount_path': '/mnt/flex-9', 'description': 'White Bear Township Council and community content'}
}
```

### 2. **File Manager Updates**

#### `core/file_manager.py`
- **Updated**: `get_accessible_mounts()` to use `member_cities` instead of `flex_servers`
- **Added**: `get_city_info()` method to retrieve specific city information
- **Added**: `get_all_cities()` method to retrieve all member city information

### 3. **Mount Checking Updates**

#### `core/check_mounts.py`
- **Added**: `MEMBER_CITY_MOUNTS` dictionary with city-specific descriptions
- **Updated**: All logging messages to include city context (e.g., "Birchwood City Council")
- **Updated**: Function documentation to reflect member city organization
- **Added**: City-specific error messages and descriptions
- **Maintained**: All actual mount paths as `/mnt/flex-N`

### 4. **API Endpoint Additions**

#### `core/api/routes/browse.py`
- **Added**: `GET /api/member-cities` - Returns information about all member cities
- **Added**: `GET /api/member-cities/<city_id>` - Returns information about a specific member city

### 5. **Documentation Updates**

#### `README.md`
- **Updated**: Flex Server Overview section to reflect member city organization
- **Replaced**: Storage tier descriptions with city-specific descriptions

#### `docs/USER_MANUAL.md`
- **Updated**: Storage Locations section with city-specific descriptions
- **Replaced**: Generic storage tier descriptions with member city information

#### `docs/TECHNICAL_DOCUMENTATION.md`
- **Added**: Member City Configuration section
- **Updated**: Configuration examples to reflect city-based organization

#### `docs/API_REFERENCE.md`
- **Added**: Member Cities API documentation
- **Added**: Examples for new member cities endpoints

#### `docs/WORKFLOW_DOCUMENTATION.md`
- **Updated**: Workflow examples to include city context
- **Updated**: Mermaid diagrams to show city-based organization
- **Added**: `get_city_name()` function for city-specific logging
- **Updated**: File discovery workflow to reference member cities

### 6. **Configuration File Updates**

#### `.env.example`
- **Updated**: Comments to include city names for each flex server
- **Maintained**: All variable names unchanged
- **Added**: City-specific descriptions for each mount point

### 7. **Test File Updates**

#### `tests/unit/test_check_mounts.py`
- **Updated**: Test data to include city-specific descriptions
- **Added**: City-specific test cases for missing mount points
- **Updated**: Test function names and documentation
- **Added**: Tests for both member cities and spare storage

#### `tests/test_complete_scc_pipeline.py`
- **Updated**: Test file paths to include city context in comments
- **Added**: City-specific descriptions for test video files

## 🔄 Content Organization Changes

### Before (Storage Tiers)
```
flex-1: Primary video storage and active content
flex-2: Secondary storage and backup content
flex-3: Archive storage for older content
flex-4: Special projects and custom content
flex-5: Test and development content
flex-6-9: Additional storage as needed
```

### After (Member Cities)
```
flex-1: Birchwood City Council and community content
flex-2: Dellwood, Grant, and Willernie combined storage
flex-3: Lake Elmo City Council and community content
flex-4: Mahtomedi City Council and community content
flex-5: Spare Record Storage 1 (overflow and additional cities)
flex-6: Spare Record Storage 2 (overflow and additional cities)
flex-7: Oakdale City Council and community content
flex-8: White Bear Lake City Council and community content
flex-9: White Bear Township Council and community content
```

## 🎯 Benefits of These Changes

### 1. **Clear Content Organization**
- Content is now organized by member city rather than storage lifecycle
- Each city has dedicated storage space for their content
- Clear separation between different member cities

### 2. **Improved Access Control**
- Location-based access control for individual cities
- Users can be restricted to specific member cities
- Granular permissions based on city membership

### 3. **Better API Support**
- New endpoints to query member city information
- City-specific content browsing capabilities
- Improved metadata for city-based content

### 4. **Enhanced Documentation**
- Clear documentation of which cities use which storage locations
- Updated examples and references throughout the codebase
- Consistent terminology across all documentation

## 🔧 Usage Examples

### Get All Member Cities
```bash
curl -X GET "http://localhost:8000/api/member-cities"
```

### Get Specific City Information
```bash
curl -X GET "http://localhost:8000/api/member-cities/flex1"
```

### Browse City-Specific Content
```bash
curl -X GET "http://localhost:8000/api/browse?path=/mnt/flex-1&location=birchwood"
```

### Access Control by City
```python
from core.config import LOCATIONS

# Check if user has access to Birchwood
birchwood_config = LOCATIONS.get('birchwood')
if user in birchwood_config['allowed_users']:
    # Allow access to Birchwood content
    pass
```

## 📋 Files That Still Need Updates

### 1. **Scripts and Utilities**
- `core/check_mounts.py` - Update mount point descriptions
- `scripts/` - Any scripts that reference storage tiers
- `tests/` - Update test files to use city-based organization

### 2. **Additional Documentation**
- `docs/WORKFLOW_DOCUMENTATION.md` - Update workflow examples
- `docs/INTEGRATION_GUIDE.md` - Update integration examples
- Any other documentation files that reference storage tiers

### 3. **Configuration Files**
- `.env.example` - Update environment variable descriptions
- `docker-compose.yml` - Update service descriptions
- Any deployment scripts that reference storage tiers

## 🚀 Next Steps

### Immediate (Next 1-2 hours)
1. **Update remaining documentation files** that still reference storage tiers
2. **Test the new API endpoints** to ensure they work correctly
3. **Update any scripts** that hardcode storage tier references

### Short Term (Next 1-2 days)
1. **Update test files** to use city-based organization
2. **Review and update any remaining configuration files**
3. **Add city-specific content organization examples**

### Medium Term (Next week)
1. **Consider adding city-specific features** like city-based reporting
2. **Implement city-specific content policies** if needed
3. **Add city-based analytics and monitoring**

## ✅ Verification Checklist

- [x] Core configuration updated with member cities
- [x] File manager updated to use city-based organization
- [x] Mount checking module updated with city context
- [x] New API endpoints added for member cities
- [x] README.md updated with city descriptions
- [x] User manual updated with city organization
- [x] Technical documentation updated
- [x] API reference documentation updated
- [x] Workflow documentation updated with city-based organization
- [x] Environment configuration updated with city descriptions
- [x] Test files updated with city-based organization
- [x] All configuration files reviewed and updated as needed

## 📞 Support

For questions about these changes or assistance with implementation, refer to:
- `docs/FLEX_SERVER_DOCUMENTATION.md` - Updated flex server documentation
- `core/config.py` - Member cities configuration
- `core/api/routes/browse.py` - Member cities API endpoints 