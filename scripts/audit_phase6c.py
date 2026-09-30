import os
import re

print("=== AUDIT PHASE 6C: SCANNING CODEBASE ===")

patterns = [
    ("HARDCODED_FALLBACK_NUM", re.compile(r'(\.length|\.count|\.total|\.score|\.spend|\.tokens)\s*\|\|\s*\d+')),
    ("HARDCODED_1_42", re.compile(r'1\.42', re.IGNORECASE)),
    ("HARDCODED_24_5", re.compile(r'24\.5', re.IGNORECASE)),
    ("HARDCODED_99_9", re.compile(r'99\.9', re.IGNORECASE)),
    ("STATIC_PAYLOADS", re.compile(r'STATIC_PAYLOADS|ATTACK_PAYLOADS', re.IGNORECASE)),
    ("FAKE_KEY", re.compile(r'ag_live_pk_|sk_live_|pk_test_|sk_test_', re.IGNORECASE)),
    ("CONNECTED_BADGE", re.compile(r'status[\'\"]?\s*:\s*[\'\"]CONNECTED[\'\"]', re.IGNORECASE)),
    ("OPERATIONAL_STRING", re.compile(r'[\'\"]Operational[\'\"]', re.IGNORECASE)),
]

findings = []

for base_dir in ['backend', 'frontend/src']:
    for root, dirs, files in os.walk(base_dir):
        if any(skip in root for skip in ['node_modules', '.next', '__pycache__', '.pytest_cache']):
            continue
        # Also exclude test assertions that verify these strings are absent
        for f in files:
            if not f.endswith(('.py', '.ts', '.tsx', '.js', '.jsx')):
                continue
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8', errors='ignore') as fh:
                for idx, line in enumerate(fh, 1):
                    for label, pat in patterns:
                        if pat.search(line):
                            findings.append((label, path, idx, line.strip()))

for label, path, idx, line in findings:
    # Filter out test files
    if 'tests' in path:
        continue
    print(f"[{label}] {path}:{idx} -> {line[:100]}")

print(f"\nTotal findings: {len(findings)}")
