#!/bin/bash
set -euo pipefail
mkdir -p /logs/verifier
printf '0\n' > /logs/verifier/reward.txt
python3 /tests/verify.py --scenario recovery-and-limits --workspace /workspace/recovery-and-limits --installation /opt/harness --contracts /tests/contracts.json > /logs/verifier/details.json
printf '1\n' > /logs/verifier/reward.txt
