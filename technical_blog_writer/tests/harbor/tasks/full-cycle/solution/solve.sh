#!/bin/bash
set -euo pipefail
python3 /opt/harness/tests/scenarios/run.py --scenario full-cycle --workspace /workspace/full-cycle
