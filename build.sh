#!/usr/bin/env bash
set -euo pipefail

echo "==> Installing Python dependencies"
pip install -r backend/requirements.txt

echo "==> Installing frontend npm packages"
cd frontend
npm install

echo "==> Building React frontend"
npm run build

echo "==> Build complete"
