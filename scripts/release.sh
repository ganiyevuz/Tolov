#!/bin/bash

# Exit on error
set -e

echo "🚀 Starting release process..."

echo "🧹 Cleaning previous builds..."
rm -rf build/ dist/ *.egg-info tolov.egg-info

echo "🔨 Building package..."
uv build

echo "📤 Uploading to PyPI..."
uv publish

echo "✅ Release completed successfully!"
echo "🎉 Package uploaded to PyPI!"
