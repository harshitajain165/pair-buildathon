#!/bin/bash

if [ ! -d ".venv" ]; then
  echo "Run ./setup.sh first."
  exit 1
fi

if [ ! -f ".env" ]; then
  echo "No .env found. Run ./setup.sh first."
  exit 1
fi

source .venv/bin/activate
python3 launcher.py
