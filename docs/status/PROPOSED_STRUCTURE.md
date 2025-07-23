# Proposed Codebase Reorganization

## Current Issues
1. Root directory clutter with test files and configuration
2. Core module overload (20+ files)
3. Mixed concerns in single files
4. Inconsistent API organization
5. Test files scattered across directories

## Proposed New Structure

```
archivist/
├── README.md
├── .env
├── .env.example
├── requirements.txt
├── setup.py
├── pytest.ini
├── alembic.ini
├── docker-compose.yml
├── Dockerfile.web
├── Dockerfile.worker
├── Makefile
├── .gitignore
│
├── src/                          # Main source code
│   ├── archivist/                # Main package
│   │   ├── __init__.py
│   │   ├── app.py               # Flask app factory
│   │   ├── config.py            # Configuration management
│   │   ├── database.py          # Database initialization
│   │   │
│   │   ├── api/                 # API layer
│   │   │   ├── __init__.py
│   │   │   ├── routes/          # Route definitions
│   │   │   │   ├── __init__.py
│   │   │   │   ├── browse.py
│   │   │   │   ├── transcribe.py
│   │   │   │   ├── queue.py
│   │   │   │   ├── vod.py
│   │   │   │   └── cablecast.py
│   │   │   ├── schemas/         # Pydantic schemas
│   │   │   │   ├── __init__.py
│   │   │   │   ├── requests.py
│   │   │   │   ├── responses.py
│   │   │   │   └── validation.py
│   │   │   └── middleware/      # API middleware
│   │   │       ├── __init__.py
│   │   │       ├── auth.py
│   │   │       ├── rate_limiting.py
│   │   │       └── security.py
│   │   │
│   │   ├── services/            # Business logic layer
│   │   │   ├── __init__.py
│   │   │   ├── transcription/   # Transcription services
│   │   │   │   ├── __init__.py
│   │   │   │   ├── whisper_service.py
│   │   │   │   ├── summarizer_service.py
│   │   │   │   └── captioner_service.py
│   │   │   ├── vod/            # VOD integration services
│   │   │   │   ├── __init__.py
│   │   │   │   ├── cablecast_client.py
│   │   │   │   ├── vod_manager.py
│   │   │   │   ├── show_mapper.py
│   │   │   │   └── transcription_linker.py
│   │   │   ├── file/           # File management services
│   │   │   │   ├── __init__.py
│   │   │   │   ├── file_manager.py
│   │   │   │   ├── mount_checker.py
│   │   │   │   └── storage_service.py
│   │   │   └── queue/          # Task queue services
│   │   │       ├── __init__.py
│   │   │       ├── queue_manager.py
│   │   │       ├── job_cleaner.py
│   │   │       └── worker_service.py
│   │   │
│   │   ├── models/             # Data models
│   │   │   ├── __init__.py
│   │   │   ├── database.py     # SQLAlchemy models
│   │   │   ├── pydantic.py     # Pydantic models
│   │   │   └── enums.py        # Enumerations
│   │   │
│   │   ├── utils/              # Utility modules
│   │   │   ├── __init__.py
│   │   │   ├── logging.py
│   │   │   ├── security.py
│   │   │   ├── validation.py
│   │   │   └── helpers.py
│   │   │
│   │   └── web/                # Web interface (if needed)
│   │       ├── __init__.py
│   │       ├── templates/
│   │       └── static/
│   │
├── tests/                      # All tests
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/                   # Unit tests
│   │   ├── __init__.py
│   │   ├── test_services/
│   │   ├── test_models/
│   │   └── test_utils/
│   ├── integration/            # Integration tests
│   │   ├── __init__.py
│   │   ├── test_api/
│   │   └── test_database/
│   ├── fixtures/               # Test fixtures
│   └── load_tests/             # Load testing
│
├── scripts/                    # Utility scripts
│   ├── __init__.py
│   ├── deployment/             # Deployment scripts
│   │   ├── deploy.sh
│   │   ├── setup-grafana.sh
│   │   └── init-letsencrypt.sh
│   ├── monitoring/             # Monitoring scripts
│   │   ├── monitor.py
│   │   └── vod_sync_monitor.py
│   ├── maintenance/            # Maintenance scripts
│   │   ├── cleanup.py
│   │   └── backfill.py
│   └── development/            # Development scripts
│       ├── run_tests.sh
│       └── update_docs.py
│
├── docs/                       # Documentation
│   ├── api/                    # API documentation
│   ├── deployment/             # Deployment guides
│   ├── development/            # Development guides
│   └── user/                   # User guides
│
├── config/                     # Configuration files
│   ├── nginx/
│   ├── grafana/
│   ├── prometheus/
│   └── certbot/
│
├── data/                       # Data directories
│   ├── uploads/
│   ├── outputs/
│   ├── logs/
│   └── cache/
│
└── migrations/                 # Database migrations
```

## Migration Benefits

### 1. **Clear Separation of Concerns**
- **API Layer**: Pure HTTP handling and routing
- **Services Layer**: Business logic and external integrations
- **Models Layer**: Data structures and database models
- **Utils Layer**: Shared utilities and helpers

### 2. **Improved Maintainability**
- Smaller, focused modules
- Clear dependencies between layers
- Easier to locate specific functionality
- Better test organization

### 3. **Enhanced Scalability**
- Easy to add new services
- Clear patterns for new features
- Better dependency management
- Modular architecture

### 4. **Better Development Experience**
- Clear file locations
- Consistent naming conventions
- Organized test structure
- Separated configuration

## Migration Strategy

### Phase 1: Create New Structure
1. Create new directory structure
2. Move files to new locations
3. Update imports and references
4. Fix circular dependencies

### Phase 2: Refactor Large Files
1. Split large files into focused modules
2. Extract business logic from API handlers
3. Create service layer abstractions
4. Improve error handling

### Phase 3: Improve Organization
1. Consolidate similar functionality
2. Remove duplicate code
3. Standardize naming conventions
4. Add comprehensive documentation

### Phase 4: Testing and Validation
1. Update test structure
2. Ensure all tests pass
3. Add integration tests
4. Performance validation

## Implementation Priority

### High Priority
1. Move test files to `tests/` directory
2. Create `src/` structure
3. Separate API from business logic
4. Organize services by domain

### Medium Priority
1. Split large files
2. Improve error handling
3. Add service layer abstractions
4. Standardize naming

### Low Priority
1. Add comprehensive documentation
2. Performance optimizations
3. Advanced monitoring
4. Additional utilities 