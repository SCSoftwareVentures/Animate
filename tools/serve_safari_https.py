#!/usr/bin/env python3
"""Serve only an integrity-verified, model-free ANIMATE bench candidate over HTTPS.

No hosting, port forwarding, preview deployment or ML redistribution is authorised.
"""

import argparse
import hashlib
import json
import subprocess
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import IPv4Address, IPv4Network
from pathlib import Path
import ssl
import sys

from build_baseline_preview import validate_site as validate_no_model_site
from vendor_hand_model import (
    MODEL_LIMIT, ROOT, SITE_FILES, checked_bytes, digest,
)


LAN_NETWORKS = tuple(map(IPv4Network, ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')))
CONTENT_TYPES = {
    '.html': 'text/html; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
    '.js': 'text/javascript; charset=utf-8',
    '.mjs': 'text/javascript; charset=utf-8',
    '.wasm': 'application/wasm',
    '.task': 'application/octet-stream',
}


# The HTTP header adds frame-ancestors, which a CSP meta tag cannot enforce.
CSP_HEADER = (
    "default-src 'none'; script-src 'self' 'wasm-unsafe-eval'; "
    "style-src 'self'; img-src 'self' data:; connect-src 'self'; "
    "object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
)
SECURITY_HEADERS = {
    'Content-Security-Policy': CSP_HEADER,
    'Permissions-Policy': 'camera=(self), microphone=(), geolocation=(), payment=()',
    'X-Frame-Options': 'DENY',
    'Cross-Origin-Resource-Policy': 'same-origin',
    'X-Content-Type-Options': 'nosniff',
    'Referrer-Policy': 'no-referrer',
    'Cache-Control': 'no-store',
}


def verify_no_model_candidate(site):
    """Fail closed unless this is a builder-generated, exact-commit six-file candidate."""
    if not validate_no_model_site(site):
        raise ValueError('Model-free baseline validation failed')
    manifest_path = site.parent / 'MANIFEST.json'
    if (not manifest_path.is_file() or manifest_path.is_symlink() or
            manifest_path.stat().st_size > 16384):
        raise ValueError('Missing, symlinked or oversized baseline candidate manifest')
    try:
        manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    except (ValueError, UnicodeError) as error:
        raise ValueError('Invalid baseline candidate manifest') from error
    fields = {
        'kind', 'sourceCommit', 'files', 'containsMediaPipeAssets',
        'hasHandMlMenuOption', 'hostingApproved', 'deviceValidationCompleted'
    }
    if not isinstance(manifest, dict) or set(manifest) != fields:
        raise ValueError('Unexpected baseline candidate manifest fields')
    result = subprocess.run(['git', 'rev-parse', 'HEAD'], cwd=ROOT,
                            text=True, capture_output=True, check=True)
    sha = result.stdout.strip()
    if (manifest['kind'] != 'NON_DISTRIBUTED_INTERNAL_BASELINE_CANDIDATE' or
            manifest['sourceCommit'] != sha or
            manifest['containsMediaPipeAssets'] is not False or
            manifest['hasHandMlMenuOption'] is not False or
            manifest['hostingApproved'] is not False or
            manifest['deviceValidationCompleted'] is not False or
            not isinstance(manifest['files'], dict) or
            set(manifest['files']) != set(SITE_FILES)):
        raise ValueError('Baseline candidate provenance or release markers differ')
    for name in SITE_FILES:
        if manifest['files'][name] != digest(site / name):
            raise ValueError('Baseline candidate file does not match manifest: ' + name)
    return True


def bench_address(value):
    try:
        address = IPv4Address(value)
    except ValueError:
        raise argparse.ArgumentTypeError('expected a loopback or private IPv4 address') from None
    if not address.is_loopback and not any(address in network for network in LAN_NETWORKS):
        raise argparse.ArgumentTypeError('expected a loopback or private IPv4 address')
    return address


def load_assets(site):
    """Load precisely the checked no-ML candidate. No model/WASM paths are served."""
    verify_no_model_candidate(site)
    assets = {}
    for name in SITE_FILES:
        data = checked_bytes(site / name, MODEL_LIMIT)
        if hashlib.sha256(data).hexdigest() != digest(site / name):
            raise ValueError('Candidate file changed while loading: ' + name)
        assets['/' + name] = (CONTENT_TYPES[Path(name).suffix], data)
    assets['/'] = assets['/index.html']
    return assets


class BenchHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        super().end_headers()

    def respond(self, send_body):
        hosts = self.headers.get_all('Host')
        if not hosts or len(hosts) != 1 or hosts[0] not in self.server.allowed_hosts:
            self.send_error(HTTPStatus.BAD_REQUEST)
            return
        asset = self.server.assets.get(self.path.partition('?')[0])
        if asset is None:
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content_type, data = asset
        self.send_response(HTTPStatus.OK)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        if send_body:
            self.wfile.write(data)

    def do_GET(self):
        self.respond(send_body=True)

    def do_HEAD(self):
        self.respond(send_body=False)

    def log_message(self, format, *args):
        # Avoid recording bench device IP addresses or URL queries.
        pass


class BenchServer(ThreadingHTTPServer):
    def get_request(self):
        request, peer = super().get_request()
        try:
            if self.allowed_client is not None and peer[0] != self.allowed_client:
                raise ConnectionRefusedError('Connection came from outside the bench')
            request.settimeout(10)
            return self.tls.wrap_socket(request, server_side=True), peer
        except OSError:
            request.close()
            raise

    def handle_error(self, _request, _client_address):
        if not isinstance(sys.exception(), (ConnectionError, TimeoutError, ssl.SSLError)):
            print('HTTPS bench request failed', file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-dir', required=True, type=Path, help='Validated site stage outside the checkout')
    parser.add_argument('--baseline-only', action='store_true', help='Require reviewed no-ML candidate and exact manifest')
    parser.add_argument('--bind', required=True, type=bench_address, help='Host loopback or private LAN IPv4 address')
    parser.add_argument('--client', type=bench_address, help='Exact iPhone IPv4 address, required for a LAN bind')
    parser.add_argument('--port', type=int, default=8443)
    parser.add_argument('--cert', required=True, type=Path, help='PEM certificate chain with a matching IP SAN')
    parser.add_argument('--key', required=True, type=Path, help='PEM private key outside the checkout and stage')
    args = parser.parse_args()
    if not args.baseline_only:
        parser.error('Refusing to serve MediaPipe: exact 1.2.3 redistribution notices are not approved; only --baseline-only is supported')
    if args.bind.is_loopback and args.client is not None:
        parser.error('Omit --client for a loopback check')
    if not args.bind.is_loopback and (args.client is None or args.client.is_loopback):
        parser.error('A private LAN bind requires --client with the exact iPhone IPv4 address')
    if not 0 <= args.port <= 65535:
        parser.error('--port must be in the range 0 to 65535')

    site = args.site_dir.resolve()
    if site.is_relative_to(ROOT) or ROOT.is_relative_to(site):
        parser.error('Staged site must be outside the checkout')
    cert, key = args.cert.resolve(), args.key.resolve()
    if any(not path.is_file() or path.is_relative_to(site) or path.is_relative_to(ROOT) for path in (cert, key)):
        parser.error('TLS certificate and key must be files outside the checkout and staged site')
    try:
        assets = load_assets(site)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.error(f'Invalid staged site: {error}')

    try:
        tls = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        tls.minimum_version = ssl.TLSVersion.TLSv1_2
        tls.load_cert_chain(certfile=cert, keyfile=key)
        with BenchServer((str(args.bind), args.port), BenchHandler) as server:
            authority = f'{args.bind}:{server.server_port}'
            server.allowed_hosts = {authority}
            if server.server_port == 443:
                server.allowed_hosts.add(str(args.bind))
            server.allowed_client = str(args.client) if args.client is not None else None
            server.assets = assets
            server.tls = tls
            print(f'Serving https://{authority}/', flush=True)
            server.serve_forever()
    except KeyboardInterrupt:
        pass
    except OSError as error:
        parser.exit(1, f'HTTPS bench setup failed: {error}\n')


if __name__ == '__main__':
    main()
