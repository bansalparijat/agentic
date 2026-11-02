#!/bin/bash
set -euo pipefail
python3 /opt/harness/tests/scenarios/run.py --scenario recovery-and-limits --workspace /workspace/recovery-and-limits
