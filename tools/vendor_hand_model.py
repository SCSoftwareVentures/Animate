#!/usr/bin/env python3
"""Operator-assisted, reproducible self-host packaging of MediaPipe Tasks Vision.
Never executes in the application, automated CI, or browser. Downloads only with an
explicit CLI invocation. Requires third-party licensing review before redistribution.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
VERSION = '1.2.3'
MODEL_SOURCE = ('https://storage.googleapis.com/mediapipe-models/'
                'hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task')
PKG = f'@mediapipe/tasks-vision@{VERSION}'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def fetch_model(path):
    req = urllib.request.Request(MODEL_SOURCE, headers={'User-Agent': 'ANIMATE-model-audit/0.6'})
    with urllib.request.urlopen(req, timeout=80) as response, path.open('wb') as output:
        length = 0
        while True:
            chunk = response.read(65536)
            if not chunk: break
            length += len(chunk)
            if length > 25 * 1024 * 1024: raise RuntimeError('Model exceeds 25 MiB safety cap')
            output.write(chunk)
    if length < 100000: raise RuntimeError('Model file is unexpectedly small')
    return digest(path)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--probe-model-hash', action='store_true', help='Download only to a temporary folder, print SHA-256, do not vendor')
    ap.add_argument('--install', action='store_true', help='Vendor approved runtime and model')
    ap.add_argument('--expected-model-sha256', default='', help='Separately reviewed 64-hex model digest')
    ap.add_argument('--license-reviewed', action='store_true', help='Operator attests redistribution rights checked for both assets')
    args = ap.parse_args()
    if args.install == args.probe_model_hash:
        ap.error('Choose exactly one of --probe-model-hash or --install')
    if args.install:
        if not args.license_reviewed:
            ap.error('STOP: --license-reviewed required; npm license does not establish model-weight rights')
        if len(args.expected_model_sha256) != 64 or any(c not in '0123456789abcdef' for c in args.expected_model_sha256.lower()):
            ap.error('STOP: pin an independently checked --expected-model-sha256')
    with tempfile.TemporaryDirectory(prefix='animate-model-') as d:
        t = Path(d)
        model = t / 'hand_landmarker.task'
        actual_hash = fetch_model(model)
        print('Official model source:', MODEL_SOURCE)
        print('Model SHA-256:', actual_hash)
        print('Model bytes:', model.stat().st_size)
        if args.probe_model_hash:
            print('PROBE ONLY: No files were installed. Independently review model licence and integrity before installation.')
            return
        if actual_hash != args.expected_model_sha256.lower():
            raise RuntimeError('MODEL SHA MISMATCH — file rejected; do not update expected digest automatically')
        prefix = t / 'npm'
        subprocess.run(['npm','install','--prefix',str(prefix),'--no-audit','--no-fund',
                        '--ignore-scripts','--save-exact',PKG], check=True)
        package = prefix / 'node_modules' / '@mediapipe' / 'tasks-vision'
        meta = json.loads((package / 'package.json').read_text())
        if meta.get('version') != VERSION: raise RuntimeError('Wrong installed runtime version')
        bundle = package / 'vision_bundle.mjs'
        binaries = sorted(f for f in (package / 'wasm').iterdir() if f.suffix in ('.js','.wasm'))
        if not bundle.is_file() or not any(f.suffix=='.wasm' for f in binaries):
            raise RuntimeError('Expected bundled ESM or WASM assets missing; inspect package layout')
        license_files = [f for f in package.iterdir() if f.is_file() and f.name.upper().startswith('LICENSE')]
        if not license_files: raise RuntimeError('No npm runtime license text found; cannot vendor')
        dest = ROOT / 'site' / 'vendor' / 'mediapipe'
        if dest.exists(): raise RuntimeError('Already vendored: manually review and remove previous assets before updating')
        dest.mkdir(parents=True)
        (dest / 'wasm').mkdir()
        (dest / 'models').mkdir()
        shutil.copy2(bundle, dest / bundle.name)
        for file in binaries: shutil.copy2(file, dest / 'wasm' / file.name)
        shutil.copy2(model, dest / 'models' / model.name)
        shutil.copy2(license_files[0], dest / 'LICENSE-runtime.txt')
        (dest / 'PROVENANCE.txt').write_text(
          'Runtime package: '+PKG+'\nRuntime registry: https://registry.npmjs.org/\n'
          'Model source: '+MODEL_SOURCE+'\nModel SHA-256: '+actual_hash+'\n'
          'Operator attested that redistribution of BOTH runtime and model is permitted.\n'
          'No runtime CDN calls, cloud inference or automatic asset downloads.\n')
        files = sorted(f for f in dest.rglob('*') if f.is_file())
        lines = [f'{digest(file)}  {file.relative_to(dest).as_posix()}' for file in files]
        (dest / 'SHA256SUMS.txt').write_text('\n'.join(lines)+'\n')
        print('VENDORED:', len(files), 'files,',sum(f.stat().st_size for f in files),'bytes')
        print('NEXT: review integrity manifest and test in CI; manually approve Pages deployment only afterwards.')

if __name__=='__main__': main()
