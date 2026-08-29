import json, pathlib, subprocess

report = pathlib.Path("/app/report/take.md")
prose = report.read_text() if report.is_file() else ""
report.unlink(missing_ok=True)          # keep analysis.py, delete the prose

try:
    p = subprocess.run(["python", "analysis.py"], cwd="/app",
                       capture_output=True, text=True, timeout=60)
    rc, out = p.returncode, p.stdout
except Exception:
    rc, out = 1, ""

s = {
    "analysis_reproduces": float(rc == 0),   # the script runs from a clean state
    "eps_correct":         float("1.79" in out),   # it computes the adjusted figure
    "prose_ties_to_code":  float("1.79" in prose), # the note agrees with the code
}
s["reward"] = round(sum(s.values()) / len(s), 4)

pathlib.Path("/logs/verifier").mkdir(parents=True, exist_ok=True)
pathlib.Path("/logs/verifier/reward.json").write_text(json.dumps(s, indent=2))
print(json.dumps(s, indent=2))
