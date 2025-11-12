#!/bin/bash

# CI Workflow Validation Script
# This script helps validate the CI workflow configuration locally

set -e

echo "🚀 Validating CI workflow configuration..."

# Check if required files exist
echo "📁 Checking required files..."
required_files=(
    ".github/workflows/ci.yml"
    "backend/pyproject.toml"
    "backend/pytest.ini"
    "backend/requirements-dev.txt"
    "worker/pyproject.toml"
    "worker/pytest.ini"
    "worker/requirements-dev.txt"
    "frontend/package.json"
    "frontend/playwright.config.ts"
    "Makefile"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file exists"
    else
        echo "❌ $file missing"
        exit 1
    fi
done

# Validate YAML syntax of CI workflow
echo "🔧 Validating CI workflow YAML..."
if command -v python3 >/dev/null 2>&1; then
    if python3 -c "import yaml" 2>/dev/null; then
        python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
        echo "✅ CI workflow YAML is valid"
    else
        echo "⚠️  PyYAML not available, skipping YAML validation"
    fi
else
    echo "⚠️  Python3 not available, skipping YAML validation"
fi

# Check Makefile targets
echo "🛠️  Validating Makefile targets..."
makefile_targets=("help" "test" "lint" "format" "install")
for target in "${makefile_targets[@]}"; do
    if grep -q "^$target:" Makefile; then
        echo "✅ Makefile target '$target' exists"
    else
        echo "❌ Makefile target '$target' missing"
        exit 1
    fi
done

# Check package.json scripts
echo "📦 Validating frontend package.json scripts..."
frontend_scripts=("lint" "build" "test:e2e")
for script in "${frontend_scripts[@]}"; do
    if grep -q "\"$script\":" frontend/package.json; then
        echo "✅ Frontend script '$script' exists"
    else
        echo "❌ Frontend script '$script' missing"
        exit 1
    fi
done

# Check Python configurations
echo "🐍 Validating Python configurations..."
for dir in backend worker; do
    if [ -f "$dir/pyproject.toml" ]; then
        echo "✅ $dir/pyproject.toml exists"
    else
        echo "❌ $dir/pyproject.toml missing"
        exit 1
    fi
    
    if [ -f "$dir/pytest.ini" ]; then
        echo "✅ $dir/pytest.ini exists"
    else
        echo "❌ $dir/pytest.ini missing"
        exit 1
    fi
    
    if [ -f "$dir/requirements-dev.txt" ]; then
        echo "✅ $dir/requirements-dev.txt exists"
    else
        echo "❌ $dir/requirements-dev.txt missing"
        exit 1
    fi
done

echo ""
echo "🎉 CI workflow configuration validation completed successfully!"
echo ""
echo "📋 Next steps:"
echo "   1. Commit and push changes to trigger the CI workflow"
echo "   2. Check the GitHub Actions tab for workflow execution"
echo "   3. Review workflow artifacts and logs"
echo "   4. Update the README badge with your repository URL"
echo ""
echo "🏠 To run CI steps locally:"
echo "   make lint      # Run all linting"
echo "   make test      # Run all tests"
echo "   make format    # Format all code"
echo "   make install   # Install all dependencies"