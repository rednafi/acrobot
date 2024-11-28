#! /usr/bin/env bash

# Reads the .env file, removes the values and saves the variables in .env.local

set -euo pipefail

# Check if .env file exists
if [[ ! -f ".env" ]]; then
    echo "Error: .env file not found!"
    exit 1
fi

# Create a new .env.local file with modified content
awk '
    # If the line starts with ENVIRONMENT, print it as is
    /^ENVIRONMENT/ {
        print $0
        next
    }

    # If the line is a comment or blank, print it as is
    /^[[:space:]]*#/ || /^[[:space:]]*$/ {
        print $0
        next
    }
    # Otherwise, clear the value while keeping the key and equals sign
    /^[[:space:]]*[^#][^=]+=/ {
        sub(/=.*/, "=")
        print $0
        next
    }
' .env > .env.sample

echo ".env.local has been created with values removed."
