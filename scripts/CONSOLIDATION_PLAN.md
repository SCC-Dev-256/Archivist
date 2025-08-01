# Script Consolidation Plan

## Overview
This document outlines the consolidation strategy for the Archivist scripts directory to reduce redundancy and improve maintainability.

## Current Redundancy Analysis

### 🚨 High Priority Consolidations

#### 1. **Multiple Startup Scripts**
**Files with Overlapping Functionality:**
- `start_archivist.sh` (98 lines)
- `start_archivist_centralized.sh` (579 lines)
- `start_archivist_centralized.py` (492 lines)
- `start_integrated_system.py` (189 lines)
- `start_complete_system.py` (380 lines)
- `start_vod_system_simple.py` (307 lines)

**Recommendation:** Consolidate into 3 core scripts:
- `start_system.sh` - Simple shell-based startup
- `start_system.py` - Python-based startup with advanced features
- `start_vod_only.py` - VOD processing only

#### 2. **Worker Scripts**
**Files with Overlapping Functionality:**
- `run_worker.sh` (33 lines)
- `run_worker_debug.sh` (46 lines)

**Recommendation:** Merge into single script with debug flag:
- `run_worker.sh --debug` or `run_worker.sh --mode=debug`

#### 3. **Web Server Scripts**
**Files with Overlapping Functionality:**
- `run_web.sh` (59 lines)
- `test_web_ui.py` (root directory)

**Recommendation:** Consolidate web startup options:
- `run_web.sh --mode=development` (Flask-SocketIO)
- `run_web.sh --mode=production` (Gunicorn)

### 🔧 Medium Priority Consolidations

#### 4. **Monitoring Scripts**
**Files with Overlapping Functionality:**
- `monitor.py` (134 lines)
- `system_status.py` (180 lines)
- `vod_sync_monitor.py` (387 lines)

**Recommendation:** Create unified monitoring framework:
- `monitor.py --type=system` (system resources)
- `monitor.py --type=vod` (VOD sync)
- `monitor.py --type=all` (comprehensive)

#### 5. **Development Scripts**
**Files with Overlapping Functionality:**
- `run_tests.sh` (26 lines)
- `test_cablecast_auth.py` (152 lines)
- `backfill_transcriptions.py` (66 lines)

**Recommendation:** Create unified testing framework:
- `run_tests.sh --type=api` (API tests)
- `run_tests.sh --type=auth` (authentication tests)
- `run_tests.sh --type=data` (data migration tests)

### 📝 Low Priority Consolidations

#### 6. **Maintenance Scripts**
**Files with Overlapping Functionality:**
- `reorganize_codebase.py` (418 lines)
- `reorganize_directory_structure.py` (660 lines)

**Recommendation:** Merge into single reorganization tool:
- `reorganize.py --type=codebase`
- `reorganize.py --type=directories`

## Proposed New Structure

```
scripts/
├── deployment/
│   ├── start_system.sh          # Consolidated startup
│   ├── start_system.py          # Advanced startup
│   ├── run_worker.sh            # Unified worker (with debug mode)
│   ├── run_web.sh               # Unified web server
│   ├── stop_system.sh           # System shutdown
│   └── infrastructure/          # Infrastructure setup
│       ├── setup-grafana.sh
│       ├── init-letsencrypt.sh
│       └── deploy.sh
├── development/
│   ├── run_tests.sh             # Unified testing
│   ├── vod_cli.py               # VOD CLI tool
│   └── update_docs.py           # Documentation updates
├── monitoring/
│   ├── monitor.py               # Unified monitoring
│   └── show_debug_logs.sh       # Debug log viewer
├── maintenance/
│   ├── reorganize.py            # Unified reorganization
│   └── manage_deps.py           # Dependency management
├── security/                    # Security scripts (unchanged)
├── setup/                       # Setup scripts (unchanged)
├── utils/                       # Utility scripts (unchanged)
└── logs/                        # Script logs (unchanged)
```

## Implementation Priority

### Phase 1: Critical Consolidations (Week 1)
1. ✅ **Worker Scripts** - Already consolidated
2. **Startup Scripts** - Create unified startup system
3. **Web Server Scripts** - Merge web startup options

### Phase 2: Monitoring Consolidation (Week 2)
1. **Monitoring Framework** - Create unified monitoring system
2. **Testing Framework** - Consolidate testing scripts

### Phase 3: Maintenance Consolidation (Week 3)
1. **Reorganization Tools** - Merge maintenance scripts
2. **Documentation Updates** - Update all README files

## Benefits of Consolidation

### ✅ **Reduced Maintenance**
- Fewer scripts to maintain
- Consistent patterns across scripts
- Centralized configuration

### ✅ **Improved Usability**
- Clearer script purposes
- Consistent command-line interfaces
- Better error handling

### ✅ **Enhanced Reliability**
- Unified testing approach
- Consistent environment setup
- Standardized logging

## Migration Strategy

### 1. **Backward Compatibility**
- Keep old scripts during transition
- Add deprecation warnings
- Provide migration guides

### 2. **Gradual Migration**
- Start with least-used scripts
- Test thoroughly before removing old scripts
- Update documentation incrementally

### 3. **Validation**
- Test all consolidated scripts
- Verify functionality matches original
- Update CI/CD pipelines

## Risk Assessment

### 🟢 **Low Risk**
- Worker script consolidation (already done)
- Web server consolidation
- Utility script consolidation

### 🟡 **Medium Risk**
- Startup script consolidation
- Monitoring script consolidation
- Testing script consolidation

### 🔴 **High Risk**
- Maintenance script consolidation
- Infrastructure script changes

## Success Metrics

### 📊 **Quantitative**
- Reduce script count by 40%
- Reduce total lines of code by 30%
- Improve script execution time by 20%

### 📈 **Qualitative**
- Improved developer experience
- Reduced confusion about which script to use
- Better documentation coverage
- Consistent error handling

## Next Steps

1. **Review and Approve** this consolidation plan
2. **Prioritize** consolidation phases
3. **Implement** Phase 1 consolidations
4. **Test** thoroughly before proceeding
5. **Document** changes and migration guides