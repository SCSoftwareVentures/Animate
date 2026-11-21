#!/usr/bin/env python3
"""Verify pinned MediaPipe assets and stage them for testing or reviewed release."""
import argparse
import hashlib
import io
from pathlib import Path
import shutil
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
SITE_FILES = frozenset({'index.html', 'core.js', 'foreground.js', 'hand_ml.js', 'app.js', 'styles.css'})
VERSION = '1.2.3'
PKG = f'@mediapipe/tasks-vision@{VERSION}'
RUNTIME_SOURCE = f'https://registry.npmjs.org/@mediapipe/tasks-vision/-/tasks-vision-{VERSION}.tgz'
RUNTIME_ARCHIVE_SHA256 = '469602650dab70256df387983ea44e85fa66020335bae85a54fa8fda062ca0a0'
MODEL_SOURCE = ('https://storage.googleapis.com/mediapipe-models/'
                'hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task')
MODEL_PATH = 'models/hand_landmarker.task'
PINNED_ASSET_SHA256 = {
    'vision_bundle.mjs': 'fb0c02c296f44ce0cc324ba16bd646d8773eb4a7847db4019cc4d0430db7a9b5',
    'wasm/vision_wasm_internal.js': '2aa5fd3fdd3d8208cd7587df0bb19fb6925c4ea16a76dd025aedc1f64d6a6309',
    'wasm/vision_wasm_internal.wasm': '225bc06c0f51a9cf31fea0e9e0b0243e9e01fb5ef332cc1a7fa6656dbdfdaabf',
    'wasm/vision_wasm_module_internal.js': 'd29996249490361715c769c6a49b43ad47e6ac9a28a8e8bce8d02b238e897851',
    'wasm/vision_wasm_module_internal.wasm': 'a269e84b12aefc93c9d6a4d62b01f41e5434a9fa941533bb8e75b1e3d1669e46',
    MODEL_PATH: 'fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1',
}
# Set only after applicable notices for the exact runtime and model are documented and reviewed.
REVIEWED_LICENSE_SHA256 = None
LICENSE_NAME = 'LICENSE-runtime.txt'
RUNTIME_LIMIT = 16 * 1024 * 1024
MODEL_LIMIT = 25 * 1024 * 1024


def digest(path):
    with path.open('rb') as asset:
        return hashlib.file_digest(asset, 'sha256').hexdigest()


def fetch(source, path, limit):
    request = urllib.request.Request(source, headers={'User-Agent': 'ANIMATE-model-audit/0.7'})
    with urllib.request.urlopen(request, timeout=80) as response, path.open('wb') as output:
        data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError(f'Download exceeds size limit: {source}')
        output.write(data)


def checked_bytes(path, limit):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > limit:
        raise ValueError(f'Expected a bounded regular input file: {path}')
    with path.open('rb') as source:
        data = source.read(limit + 1)
    if len(data) > limit:
        raise ValueError(f'Input exceeds size limit: {path}')
    return data


def verified_payloads(runtime_path, model_path):
    runtime = checked_bytes(runtime_path, RUNTIME_LIMIT)
    if hashlib.sha256(runtime).hexdigest() != RUNTIME_ARCHIVE_SHA256:
        raise ValueError('Runtime archive does not match pinned SHA-256')
    model = checked_bytes(model_path, MODEL_LIMIT)
    assets = {MODEL_PATH: model}
    with tarfile.open(fileobj=io.BytesIO(runtime), mode='r:gz') as archive:
        for relative in PINNED_ASSET_SHA256.keys() - {MODEL_PATH}:
            entry = archive.getmember(f'package/{relative}')
            if not entry.isfile():
                raise ValueError(f'Expected a regular runtime member: {relative}')
            with archive.extractfile(entry) as source:
                assets[relative] = source.read()
    for relative, expected in PINNED_ASSET_SHA256.items():
        if hashlib.sha256(assets[relative]).hexdigest() != expected:
            raise ValueError(f'Asset does not match pinned SHA-256: {relative}')
    return assets


def validate_staged_site(site, require_assets=True):
    """Check an exact copy of the app, optionally with the six test-only asset files."""
    expected = set(SITE_FILES)
    if require_assets:
        expected.update({'vendor', 'vendor/mediapipe', 'vendor/mediapipe/models',
                         'vendor/mediapipe/wasm'})
        expected.update(f'vendor/mediapipe/{relative}' for relative in PINNED_ASSET_SHA256)
    if not site.is_dir() or site.is_symlink():
        raise ValueError('Expected a regular staging directory')
    paths = {entry.relative_to(site).as_posix(): entry for entry in site.rglob('*')}
    if set(paths) != expected or any(entry.is_symlink() for entry in paths.values()):
        raise ValueError('Staged site has missing, unexpected or symlinked entries')
    for filename in SITE_FILES:
        if not paths[filename].is_file() or digest(paths[filename]) != digest(ROOT / 'site' / filename):
            raise ValueError(f'Staged app file differs from checkout: {filename}')
    if require_assets:
        for relative, expected_digest in PINNED_ASSET_SHA256.items():
            asset = paths[f'vendor/mediapipe/{relative}']
            if not asset.is_file() or digest(asset) != expected_digest:
                raise ValueError(f'Staged asset does not match pinned SHA-256: {relative}')


def write_payloads(destination, assets):
    for relative, data in assets.items():
        asset = destination / relative
        asset.parent.mkdir(parents=True, exist_ok=True)
        asset.write_bytes(data)


def move_new_tree(source, destination):
    lock = destination.with_name(f'.{destination.name}.animate-lock')
    lock.touch(exist_ok=False)
    try:
        if destination.exists() or destination.is_symlink():
            raise ValueError(f'Destination already exists: {destination}')
        source.rename(destination)
    finally:
        lock.unlink()


def stage_test_site(destination, assets):
    with tempfile.TemporaryDirectory(prefix='.animate-stage-', dir=destination.parent) as scratch:
        site = Path(scratch) / 'site'
        site.mkdir(mode=0o700)
        for filename in SITE_FILES:
            shutil.copyfile(ROOT / 'site' / filename, site / filename)
        write_payloads(site / 'vendor' / 'mediapipe', assets)
        validate_staged_site(site)
        move_new_tree(site, destination)


def install_reviewed(assets, license_file):
    vendor = ROOT / 'site' / 'vendor'
    destination = vendor / 'mediapipe'
    if vendor.exists() or vendor.is_symlink():
        raise ValueError('Existing vendor directory must be reviewed before installing')
    with tempfile.TemporaryDirectory(prefix='.animate-vendor-', dir=vendor.parent) as scratch:
        staged = Path(scratch) / 'vendor'
        bundle = staged / 'mediapipe'
        bundle.mkdir(parents=True)
        write_payloads(bundle, assets)
        shutil.copyfile(license_file, bundle / LICENSE_NAME)
        if digest(bundle / LICENSE_NAME) != REVIEWED_LICENSE_SHA256:
            raise ValueError('Licence and attribution file does not match reviewed SHA-256')
        (bundle / 'PROVENANCE.txt').write_text(
            f'Runtime package: {PKG}\nRuntime source: {RUNTIME_SOURCE}\n'
            f'Runtime archive SHA-256: {RUNTIME_ARCHIVE_SHA256}\n'
            f'Model source: {MODEL_SOURCE}\nModel SHA-256: {PINNED_ASSET_SHA256[MODEL_PATH]}\n'
            'Operator attested that redistribution of the runtime and model is permitted.\n',
            encoding='utf-8',
        )
        files = sorted(file for file in bundle.rglob('*') if file.is_file())
        manifest = ''.join(f'{digest(file)}  {file.relative_to(bundle).as_posix()}\n' for file in files)
        (bundle / 'SHA256SUMS.txt').write_text(manifest, encoding='utf-8')
        move_new_tree(staged, vendor)
    print('Installed reviewed MediaPipe bundle:', destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--probe-model-hash', action='store_true', help='Verify the publisher model digest without staging')
    mode.add_argument('--stage-test', action='store_true', help='Stage pinned inputs for private, non-publishable testing')
    mode.add_argument('--install', action='store_true', help='Install assets with approved redistribution evidence')
    parser.add_argument('--site-dir', type=Path, help='New external site directory for --stage-test')
    parser.add_argument('--runtime-archive', type=Path, help='Local pinned npm tarball')
    parser.add_argument('--model-file', type=Path, help='Local pinned model bundle')
    parser.add_argument('--expected-model-sha256', default='', help='Independently reviewed model digest for --install')
    parser.add_argument('--license-reviewed', action='store_true', help='Operator attests redistribution review for both assets')
    parser.add_argument('--license-file', type=Path, help='Approved licence and third-party attribution file for --install')
    args = parser.parse_args()

    if args.stage_test:
        if args.site_dir is None or args.runtime_archive is None or args.model_file is None:
            parser.error('--stage-test requires --site-dir, --runtime-archive and --model-file')
        destination = args.site_dir.resolve()
        if destination.is_relative_to(ROOT) or any(
            (parent / '.git').is_file() or (parent / '.git' / 'HEAD').is_file()
            for parent in destination.parents
        ):
            parser.error('Stage test assets outside Git checkouts')
        if not destination.parent.is_dir() or destination.exists() or args.site_dir.is_symlink():
            parser.error('--site-dir must be a new path with an existing parent')
        assets = verified_payloads(args.runtime_archive, args.model_file)
        stage_test_site(destination, assets)
        print(f'Staged {len(assets)} verified assets for private testing: {destination}')
        return

    if args.site_dir is not None:
        parser.error('--site-dir is only for --stage-test')
    if args.install:
        if not args.license_reviewed or args.expected_model_sha256.lower() != PINNED_ASSET_SHA256[MODEL_PATH]:
            parser.error('--install requires operator review and the independently pinned model SHA-256')
        if REVIEWED_LICENSE_SHA256 is None:
            parser.error(f'Redistribution notices for the pinned MediaPipe {VERSION} bundle are pending')
        if args.license_file is None or not args.license_file.is_file() or args.license_file.is_symlink():
            parser.error('--install requires the reviewed --license-file')

    with tempfile.TemporaryDirectory(prefix='animate-model-') as scratch:
        model = args.model_file
        if model is None:
            model = Path(scratch) / 'hand_landmarker.task'
            fetch(MODEL_SOURCE, model, MODEL_LIMIT)
        if args.probe_model_hash:
            actual = hashlib.sha256(checked_bytes(model, MODEL_LIMIT)).hexdigest()
            print(f'Model SHA-256: {actual}\nModel bytes: {model.stat().st_size}')
            if actual != PINNED_ASSET_SHA256[MODEL_PATH]:
                raise ValueError('Model does not match pinned SHA-256')
            return
        runtime = args.runtime_archive
        if runtime is None:
            runtime = Path(scratch) / 'tasks-vision.tgz'
            fetch(RUNTIME_SOURCE, runtime, RUNTIME_LIMIT)
        install_reviewed(verified_payloads(runtime, model), args.license_file)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, KeyError, tarfile.TarError) as error:
        raise SystemExit(str(error))
