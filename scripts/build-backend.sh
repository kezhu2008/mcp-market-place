#!/usr/bin/env bash
# Build backend Lambda zip: pip install deps into build/ and zip.
set -euo pipefail
cd "$(dirname "$0")/../backend"

rm -rf build
mkdir -p build

python -m pip install --upgrade pip >/dev/null
pip install --target build \
  "fastapi==0.115.0" \
  "mangum==0.19.0" \
  "pydantic==2.9.2" \
  "python-ulid==3.0.0" \
  "pyjwt[crypto]==2.9.0" \
  "httpx==0.27.2" \
  "aws-lambda-powertools==3.2.0" \
  >/dev/null

cp -R app build/app

cd build
zip -qr function.zip . -x "*.pyc" -x "*/__pycache__/*"
echo "built backend/build/function.zip ($(du -sh function.zip | cut -f1))"
