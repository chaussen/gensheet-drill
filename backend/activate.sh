#!/bin/bash

# This script should be sourced: source activate.sh

if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "Already in virtual environment: $VIRTUAL_ENV"
else
    if [ ! -d "venv" ]; then
        echo "Creating virtual environment..."
        python3 -m venv venv
        source venv/bin/activate
        pip install --upgrade pip
        if [ -f "requirements.txt" ]; then
            echo "Installing dependencies..."
            pip install -r requirements.txt
        fi
    else
        source venv/bin/activate
        echo "Activated existing venv."
    fi
fi
