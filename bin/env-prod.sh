#! /usr/bin/env bash

# Reads the .env.local file and copies it to .env

set -euo pipefail

# Check if .env.local file exists
if [[ ! -f ".env.local" ]]; then
    echo "Error: .env.local file not found!"
    exit 1
fi

# Copy the .env.local file to .env
cp .env.local .env

echo ".env has been updated with .env.local values."
