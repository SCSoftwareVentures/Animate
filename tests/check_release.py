"""Check exactly what can be published and fail closed on unreviewed model assets."""
from pathlib import Path
import hashlib
import subprocess
import sys

if not __debug__:
    raise SystemExit('Release validation requires Python assertions to be enabled')

# Pinned MediaPipe Tasks Vision 1.2.3 npm payload and Google Hand Landmarker float16 v1.
PINNED_ASSET_SHA256 = {
    'vision_bundle.mjs': 'fb0c02c296f44ce0cc324ba16bd646d8773eb4a7847db4019cc4d0430db7a9b5',
    'wasm/vision_wasm_internal.js': '2aa5fd3fdd3d8208cd7587df0bb19fb6925c4ea16a76dd025aedc1f64d6a6309',
    'wasm/vision_wasm_internal.wasm': '225bc06c0f51a9cf31fea0e9e0b0243e9e01fb5ef332cc1a7fa6656dbdfdaabf',
    'wasm/vision_wasm_module_internal.js': 'd29996249490361715c769c6a49b43ad47e6ac9a28a8e8bce8d02b238e897851',
    'wasm/vision_wasm_module_internal.wasm': 'a269e84b12aefc93c9d6a4d62b01f41e5434a9fa941533bb8e75b1e3d1669e46',
    'models/hand_landmarker.task': 'fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1',
}

root = Path(__file__).resolve().parent.parent
site = root / 'site'
expected = {'index.html','core.js','foreground.js','hand_ml.js','app.js','styles.css'}
assert site.is_dir() and not site.is_symlink(), 'Expected a regular site directory'
site_entries = list(site.iterdir())
assert not any(p.is_symlink() for p in site_entries), 'Unexpected symlink in site/'
actual = {x.name for x in site_entries if x.is_file()}
assert actual == expected, f'Unexpected published site files: {actual ^ expected}'
assert all(p.name in expected or (p.name == 'vendor' and p.is_dir()) for p in site_entries), 'Unknown entry in site/'
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
    assert target.is_dir() and not target.is_symlink(), 'Expected a regular MediaPipe directory'
    manifest = target/'SHA256SUMS.txt'
    metadata = {'LICENSE-runtime.txt', 'PROVENANCE.txt'}
    required_assets = set(PINNED_ASSET_SHA256) | metadata
    required_files = required_assets | {manifest.name}
    required_dirs = {'models', 'wasm'}
    entries = {p.relative_to(target).as_posix(): p for p in target.rglob('*')}
    assert not any(p.is_symlink() for p in entries.values()), 'Unexpected symlink in MediaPipe assets'
    actual_files = {relative for relative, path in entries.items() if path.is_file()}
    actual_dirs = {relative for relative, path in entries.items() if path.is_dir()}
    assert actual_files == required_files, f'Unexpected or missing MediaPipe files: {sorted(actual_files ^ required_files)}'
    assert actual_dirs == required_dirs, f'Unexpected or missing MediaPipe directories: {sorted(actual_dirs ^ required_dirs)}'
    assert set(entries) == actual_files | actual_dirs, 'Unexpected MediaPipe filesystem entry'
    assert all(entries[relative].stat().st_size > 0 for relative in metadata), 'Empty runtime license or provenance'
    listed = set()
    for line in manifest.read_text(encoding='utf-8').splitlines():
        sha, separator, relative = line.partition('  ')
        assert separator and len(sha) == 64 and all(c in '0123456789abcdef' for c in sha), 'Bad SHA-256 manifest'
        assert relative in required_assets and relative not in listed, f'Unexpected or duplicate manifest path: {relative}'
        with entries[relative].open('rb') as asset:
            asset_sha = hashlib.file_digest(asset, 'sha256').hexdigest()
        assert asset_sha == sha, f'Model/runtime asset changed: {relative}'
        if relative in PINNED_ASSET_SHA256:
            assert asset_sha == PINNED_ASSET_SHA256[relative], f'Model/runtime asset does not match pinned SHA-256: {relative}'
        listed.add(relative)
    assert listed == required_assets, f'Missing manifest assets: {sorted(required_assets - listed)}'
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
