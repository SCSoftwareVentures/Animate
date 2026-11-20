"""Check exactly what can be published and fail closed on unreviewed model assets."""
from pathlib import Path
import hashlib
import subprocess
import sys
root = Path(__file__).resolve().parent.parent
site = root / 'site'
expected = {'index.html','core.js','foreground.js','hand_ml.js','app.js','styles.css'}
actual = {x.name for x in site.iterdir() if x.is_file()}
assert actual == expected, f'Unexpected published site files: {actual ^ expected}'
assert all(p.name == 'vendor' for p in site.iterdir() if p.is_dir()), 'Unknown public folder in site/'
html = (site/'index.html').read_text()
for file in ('core.js','foreground.js','hand_ml.js','app.js'):
    assert f'src="{file}?v=0.7.0"' in html, f'Missing versioned {file}'
assert 'href="styles.css?v=0.7.0"' in html
assert "connect-src 'self'" in html and "script-src 'self' 'wasm-unsafe-eval'" in html
assert not any(x in html for x in ('Would you buy this?', 'data-intent'))
assert 'This policy requires operator confirmation' in html
assert 'https://cdn.' not in html and 'https://storage.googleapis.com' not in html
vendor = site/'vendor'
if vendor.exists():
    assert {p.name for p in vendor.iterdir()} == {'mediapipe'}, 'Unexpected vendor directories'
    target = vendor/'mediapipe'
    manifest = target/'SHA256SUMS.txt'
    assert manifest.is_file(), 'No model asset integrity manifest'
    allowed = {'vision_bundle.mjs','LICENSE-runtime.txt','PROVENANCE.txt',
               'models/hand_landmarker.task','SHA256SUMS.txt'}
    listed = set()
    for line in manifest.read_text().splitlines():
        sha, rel = line.split('  ', 1)
        assert not Path(rel).is_absolute() and '..' not in Path(rel).parts and '\\' not in rel, 'Unsafe manifest path'
        assert len(sha)==64 and all(c in '0123456789abcdef' for c in sha), 'Bad SHA-256 manifest'
        assert rel not in listed and ('/' not in rel or rel.startswith(('wasm/','models/'))), 'Bad path'
        assert rel in allowed or (rel.startswith('wasm/') and rel.split('/')[-1].endswith(('.wasm','.js'))), 'Unapproved file'
        asset = target/rel
        assert asset.is_file() and not asset.is_symlink() and asset.resolve().is_relative_to(target.resolve()), 'Manifest path escape'
        assert hashlib.sha256(asset.read_bytes()).hexdigest()==sha, 'Model/runtime asset changed: '+rel
        listed.add(rel)
    assert {'vision_bundle.mjs','models/hand_landmarker.task','LICENSE-runtime.txt','PROVENANCE.txt'} <= listed
    actual_files = {f.relative_to(target).as_posix() for f in target.rglob('*') if f.is_file()}
    assert actual_files == listed | {'SHA256SUMS.txt'}, 'Unlisted vendor asset in publish output'
    print('PASS: locally bundled and integrity-checked model/runtime assets')
elif '--publish' in sys.argv:
    raise AssertionError('Publish blocked: locally bundled reviewed ML assets are absent')
else:
    print('INFO: ML runtime/model absent — hand option fails closed; publishing blocked without assets')
result = subprocess.run(['git','ls-files','-z'], cwd=root, text=False, capture_output=True)
if result.returncode == 0 and result.stdout:
    tracked = [p.decode('utf-8', 'replace') for p in result.stdout.split(b'\0') if p]
    banned = {'.csv','.json','.jsonl','.ndjson','.sqlite','.sqlite3','.db','.zip','.log'}
    failures = [p for p in tracked if Path(p).suffix.lower() in banned or
                Path(p).name.startswith('.env') or
                any(s in p.lower() for s in ('participant-export','respondent-data','research-ledger'))]
    assert not failures, f'Sensitive file types are tracked in repo: {failures}'
print('PASS: public site scope and repository hygiene checks')
