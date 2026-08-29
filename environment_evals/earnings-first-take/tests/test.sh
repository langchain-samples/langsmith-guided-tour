#!/bin/bash
set -u
mkdir -p /logs/verifier
python3 /tests/verify.py || echo '{"reward": 0.0}' > /logs/verifier/reward.json
