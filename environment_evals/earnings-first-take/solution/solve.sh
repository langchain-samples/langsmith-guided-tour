#!/bin/bash
set -euo pipefail
cat > /app/analysis.py <<'PY'
adj = (412.0 + 340.0 * 0.79) / 380.0
print(f"Adjusted EPS: {adj:.2f} vs consensus 1.71")
PY
mkdir -p /app/report
echo "Adjusted EPS \$1.79 vs consensus \$1.71 — a 4.7% beat." > /app/report/take.md
