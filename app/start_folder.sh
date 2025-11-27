#!/bin/bash

# Check if folder path is provided
if [ -z "$1" ]; then
    echo "Error: Please provide a folder path"
    echo "Usage: $0 /path/to/folder"
    exit 1
fi

# Go to the parent directory of the script
cd "$(dirname "$0")/../kk"

# Run main_folder.py with the provided folder path
python -m main_folder "$1"