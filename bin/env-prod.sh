#! /usr/bin/env bash

# Reads the .env.sample file and copies it to .env

set -euo pipefail

# Check if .env.sample file exists
if [[ ! -f ".env.sample" ]]; then
    echo "Error: .env.sample file not found!"
    exit 1
fi

# Copy the .env.sample file to .env
cp .env.sample .env

echo ".env has been updated with .env.sample values."
