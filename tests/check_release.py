"""Check exactly what can be published and fail closed on unreviewed model assets."""
from html.parser import HTMLParser
from pathlib import Path
import hashlib
import json
import subprocess
import sys

if not __debug__:
    raise SystemExit('Release validation requires Python assertions to be enabled')

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root / 'tools'))
from vendor_hand_model import LICENSE_NAME, PINNED_ASSET_SHA256, REVIEWED_LICENSE_SHA256, SITE_FILES


class PagePolicy(HTMLParser):
    def __init__(self):
        super().__init__()
        self.policies = []
        self.in_head = False

    def handle_starttag(self, tag, attributes):
        if tag == 'head':
            self.in_head = True
        attrs = dict(attributes)
        if tag == 'meta' and (attrs.get('http-equiv') or '').lower() == 'content-security-policy':
            assert self.in_head and len(attrs) == len(attributes), 'Invalid Content Security Policy meta element'
            self.policies.append(attrs.get('content') or '')

    def handle_endtag(self, tag):
        if tag == 'head':
            self.in_head = False


publish = '--publish' in sys.argv
site = root / 'site'
expected = SITE_FILES
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
policy = PagePolicy()
policy.feed(html)
assert len(policy.policies) == 1, 'Expected exactly one Content Security Policy'
directives = [part.split() for part in policy.policies[0].split(';') if part.strip()]
expected_directives = {
    'default-src': ["'none'"], 'script-src': ["'self'", "'wasm-unsafe-eval'"],
    'style-src': ["'self'"], 'img-src': ["'self'", 'data:'], 'connect-src': ["'self'"],
    'object-src': ["'none'"], 'base-uri': ["'none'"], 'form-action': ["'none'"],
}
assert len(directives) == len(expected_directives) and dict(
    (name, sources) for name, *sources in directives
) == expected_directives, 'Content Security Policy differs from the reviewed directives'
assert not any(x in html for x in ('Would you buy this?', 'data-intent'))
assert 'This policy requires operator confirmation' in html
assert 'https://cdn.' not in html and 'https://storage.googleapis.com' not in html
vendor = site/'vendor'
if vendor.exists():
    assert {p.name for p in vendor.iterdir()} == {'mediapipe'}, 'Unexpected vendor directories'
    target = vendor/'mediapipe'
    assert target.is_dir() and not target.is_symlink(), 'Expected a regular MediaPipe directory'
    manifest = target/'SHA256SUMS.txt'
    metadata = {LICENSE_NAME, 'PROVENANCE.txt'}
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
    if publish:
        assert REVIEWED_LICENSE_SHA256 is not None, 'Publish blocked: exact MediaPipe redistribution notices are pending'
        with entries[LICENSE_NAME].open('rb') as license_file:
            assert hashlib.file_digest(license_file, 'sha256').hexdigest() == REVIEWED_LICENSE_SHA256, (
                'Publish blocked: licence and attribution file does not match reviewed SHA-256'
            )
    print('PASS: locally bundled and integrity-checked model/runtime assets')
elif publish:
    raise AssertionError('Publish blocked: locally bundled reviewed ML assets are absent')
else:
    print('INFO: ML runtime/model absent — hand option fails closed; publishing blocked without assets')
result = subprocess.run(['git','ls-files','-z'], cwd=root, text=False, capture_output=True)
if publish or (root / '.git').exists():
    assert result.returncode == 0 and result.stdout, 'Could not inspect tracked files'
if result.returncode == 0 and result.stdout:
    tracked = [p.decode('utf-8', 'replace') for p in result.stdout.split(b'\0') if p]
    banned = {'.csv','.json','.jsonl','.ndjson','.sqlite','.sqlite3','.db','.db-wal','.db-shm','.zip','.log'}
    # The ONLY permitted tracked JSON is a precisely validated safe Codespaces
    # configuration. Never exempt arbitrary configuration, logs or research data.
    devcontainer_name = '.devcontainer/devcontainer.json'
    if devcontainer_name in tracked:
        config_file = root / devcontainer_name
        assert (config_file.is_file() and not config_file.is_symlink() and
                not (root / '.devcontainer').is_symlink()), 'Unsafe devcontainer config path'
        config = json.loads(config_file.read_text(encoding='utf-8'))
        assert config == {
            'name': 'ANIMATE — private iPhone preview (manual start only)',
            'image': 'mcr.microsoft.com/devcontainers/python:1-3.12-bookworm',
            'forwardPorts': [8765],
            'portsAttributes': {
                '8765': {
                    'label': 'ANIMATE: PRIVATE owner preview',
                    'onAutoForward': 'notify',
                    'protocol': 'http',
                }
            }
        }, 'Unreviewed Codespaces configuration; commands/env/ports are forbidden'
    failures = [p for p in tracked if (
                (Path(p).suffix.lower() in banned and p != devcontainer_name) or
                Path(p).name.startswith('.env') or
                any(s in p.lower() for s in ('participant-export','respondent-data','research-ledger'))
            )]
    assert not failures, f'Sensitive file types are tracked in repo: {failures}'
print('PASS: public site scope and repository hygiene checks')
