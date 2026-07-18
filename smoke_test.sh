#!/usr/bin/env bash
# Fast (<2 min) reproducibility smoke test — no external data required.
# Verifies core analysis code imports and runs on a tiny fixture, and that the
# frozen headline result JSONs parse with the expected top-level keys.
#
# Usage:  bash smoke_test.sh
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${HERE}/tests/smoke_test.py"
