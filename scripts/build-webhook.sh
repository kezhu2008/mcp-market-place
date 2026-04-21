#!/usr/bin/env bash
# Build webhook Lambda zip. Only boto3 is needed at runtime, which the Lambda
# runtime already provides — so the zip is tiny.
set -euo pipefail
cd "$(dirname "$0")/../webhook"

rm -rf build
mkdir -p build

cp handler.py build/handler.py

cd build
zip -qr function.zip . -x "*.pyc" -x "*/__pycache__/*"
echo "built webhook/build/function.zip ($(du -sh function.zip | cut -f1))"
