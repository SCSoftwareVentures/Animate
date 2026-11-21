#!/usr/bin/env python3
"""Serve a validated ANIMATE stage to a single trusted bench device over HTTPS."""

import argparse
import hashlib
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import IPv4Address, IPv4Network
from pathlib import Path
import ssl
import sys

from vendor_hand_model import (
    MODEL_LIMIT, PINNED_ASSET_SHA256, ROOT, SITE_FILES, checked_bytes, digest, validate_staged_site,
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


def bench_address(value):
    try:
        address = IPv4Address(value)
    except ValueError:
        raise argparse.ArgumentTypeError('expected a loopback or private IPv4 address') from None
    if not address.is_loopback and not any(address in network for network in LAN_NETWORKS):
        raise argparse.ArgumentTypeError('expected a loopback or private IPv4 address')
    return address


def load_assets(site, require_assets):
    expected = {name: digest(ROOT / 'site' / name) for name in SITE_FILES}
    if require_assets:
        expected.update({f'vendor/mediapipe/{name}': sha for name, sha in PINNED_ASSET_SHA256.items()})
    assets = {}
    for name, sha in expected.items():
        data = checked_bytes(site / name, MODEL_LIMIT)
        if hashlib.sha256(data).hexdigest() != sha:
            raise ValueError(f'Staged asset changed during startup: {name}')
        assets[f'/{name}'] = (CONTENT_TYPES[Path(name).suffix], data)
    assets['/'] = assets['/index.html']
    return assets


class BenchHandler(BaseHTTPRequestHandler):
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
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
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
    parser.add_argument('--baseline-only', action='store_true', help='Require a stage with only the six app files')
    parser.add_argument('--bind', required=True, type=bench_address, help='Host loopback or private LAN IPv4 address')
    parser.add_argument('--client', type=bench_address, help='Exact iPhone IPv4 address, required for a LAN bind')
    parser.add_argument('--port', type=int, default=8443)
    parser.add_argument('--cert', required=True, type=Path, help='PEM certificate chain with a matching IP SAN')
    parser.add_argument('--key', required=True, type=Path, help='PEM private key outside the checkout and stage')
    args = parser.parse_args()
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
    require_assets = not args.baseline_only
    try:
        validate_staged_site(args.site_dir, require_assets=require_assets)
        assets = load_assets(site, require_assets)
    except (OSError, ValueError) as error:
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
