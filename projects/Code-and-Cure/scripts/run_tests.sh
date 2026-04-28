#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$ROOT_DIR"
python -m pytest src/core_logic/test_logic.py src/core_logic/test_stream_session.py src/api/test_security_integration.py

cd "$ROOT_DIR/src/frontend"
npm run build
