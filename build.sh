#!/usr/bin/env bash
set -euo pipefail

echo "==> Installing Python dependencies"
pip install -r requirements.txt

echo "==> Installing frontend npm packages"
cd frontend
npm install

echo "==> Building React frontend"
npm run build
cd ..

echo "==> Build complete"
