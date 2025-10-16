#!/bin/bash
# FPL Cheat - Local Development Setup

set -e

echo "Setting up FPL Cheat..."

# Check prerequisites
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required"
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo "Error: uv is required. Install with: curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Run setup
python3 deploy/local_setup.py