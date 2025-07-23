#!/bin/bash
# Script to disable GitHub Actions workflows to prevent billing issues

echo "🔧 Disabling GitHub Actions workflows to prevent billing issues..."

# Create .github/workflows directory if it doesn't exist
mkdir -p .github/workflows

# Disable the security-tests.yml workflow by renaming it
if [ -f ".github/workflows/security-tests.yml" ]; then
    mv .github/workflows/security-tests.yml .github/workflows/security-tests.yml.disabled
    echo "✅ Disabled security-tests.yml workflow"
else
    echo "ℹ️  security-tests.yml workflow not found"
fi

# Create a simple README explaining the local security setup
cat > .github/workflows/README.md << 'EOF'
# Local Security Scanning

GitHub Actions workflows have been disabled to prevent billing issues.

## Local Security Checks

Instead of GitHub Actions, use the local security scanning tools:

```bash
# Run all security checks
make security-scan

# Quick security check
make security-quick

# Install security tools
make install
```

## Available Commands

- `make security-scan` - Full security scan (replaces GitHub Actions)
- `make security-quick` - Quick security check
- `make test` - Run tests
- `make format` - Format code
- `make lint` - Run linting

## Security Tools Installed

- **Safety** - Dependency vulnerability scanning
- **Bandit** - Python security linting
- **Semgrep** - Advanced security analysis
- **Black** - Code formatting
- **Flake8** - Code linting

This approach eliminates dependency on GitHub's paid services while maintaining security standards.
EOF

echo "✅ Created README explaining local security setup"
echo ""
echo "📋 To re-enable GitHub Actions later, run:"
echo "   mv .github/workflows/security-tests.yml.disabled .github/workflows/security-tests.yml"
echo ""
echo "🔒 Local security scanning is now available with:"
echo "   make security-scan" 