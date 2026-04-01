#!/usr/bin/env bash
# Copyright 2026 Grainpool Holdings LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# SPDX-License-Identifier: Apache-2.0

# CI test runner for sphinx-longmd.
#
# Usage:
#   ./run_tests.sh          # full suite
#   ./run_tests.sh phase1   # phase 1 only
#   ./run_tests.sh phase2   # phase 2 only
#   ./run_tests.sh phase3   # phase 3 only
#   ./run_tests.sh quick    # unit tests only (no Sphinx builds)
set -euo pipefail
cd "$(dirname "$0")"

PHASE="${1:-all}"

echo "=== sphinx-longmd test runner ==="
echo "Python: $(python --version 2>&1)"
echo "Phase:  $PHASE"
echo ""

case "$PHASE" in
  quick)
    echo "--- Unit tests (no Sphinx builds) ---"
    pytest tests/test_anchors.py tests/test_assets.py tests/test_emitters.py tests/test_sidecar.py -v
    ;;
  phase1)
    echo "--- Phase 1: structural Markdown ---"
    pytest tests/test_builder_smoke.py tests/test_anchors.py tests/test_assets.py tests/test_emitters.py tests/test_sidecar.py -v
    ;;
  phase2)
    echo "--- Phase 2: Sphinx semantics ---"
    pytest tests/test_phase2.py -v
    ;;
  phase3)
    echo "--- Phase 3: hardening ---"
    pytest tests/test_phase3.py -v
    ;;
  all)
    echo "--- Full suite ---"
    pytest tests/ -v
    ;;
  *)
    echo "Unknown phase: $PHASE"
    echo "Usage: $0 [all|quick|phase1|phase2|phase3]"
    exit 1
    ;;
esac

echo ""
echo "=== Done ==="
