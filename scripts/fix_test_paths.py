with open('backend/tests/test_phase6c_truthfulness.py', 'r', encoding='utf-8') as f:
    content = f.read()

replacements = [
    ('"/digital-twin/run"', '"/api/digital-twin/run"'),
    ('"/red-team/run"', '"/api/red-team/run"'),
    ('"/optimization/recommendations', '"/api/optimization/recommendations'),
    ('"/optimization/compute"', '"/api/optimization/compute"'),
    ('"/impact/metrics', '"/api/impact/metrics'),
    ('"/system/health"', '"/api/system/health"'),
    ('"/integrations"', '"/api/integrations"'),
    ('"/organization/invite-user"', '"/api/organization/invite-user"'),
]

for old, new in replacements:
    content = content.replace(old, new)

with open('backend/tests/test_phase6c_truthfulness.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Updated endpoints with /api prefix')
