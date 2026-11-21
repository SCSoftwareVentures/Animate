#!/usr/bin/env python3
"""Serve an exact, source-verified, model-free ANIMATE preview in GitHub Codespaces.

Security boundary: ONLY a GitHub-authenticated PRIVATE forwarded port, never
the public GitHub repo, provides viewer authentication. This server is a static
read-only byte-preserving origin with audited security headers. It MUST NOT be
made public. No Netlify upload, paid service, model/WASM distribution or
participant research is performed.

Usage from an authorised Codespace on the correct draft branch:
    python tools/run_codespaces_private_preview.py

Then use the Ports tab to verify visibility = Private and open the HTTPS
forwarded URL, appending /operator-preview/verify.html.
"""
import argparse
import functools
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
import zipfile

from build_iphone_camera_gate import (
    EXPECTED, ZIP_NAME, build_camera_gate, validate_archive,
)
from build_zero_cost_preview import headers_text

PORT = 8765
REPOSITORY = "SCSoftwareVentures/Animate"
APPROVED_BRANCH = "engineering/animate-codespaces-private-preview-20261122"

# No directory browsing, unrelated source files, _headers, receipts or model
# paths can be served. Exact case-sensitive route match, without URL decoding.
ROUTES = frozenset(
    {"/"} | {"/" + name for name in EXPECTED if name != "_headers"}
)
SECURITY_HEADERS = {}


def parse_headers():
    lines = headers_text().splitlines()
    if lines[:1] != ["/*"]:
        raise ValueError("Unexpected reviewed Netlify security-header policy")
    result = {}
    for line in lines[1:]:
        if not line.startswith("  ") or ": " not in line:
            raise ValueError("Invalid reviewed header")
        name, value = line.strip().split(": ", 1)
        if name.lower() in {x.lower() for x in result}:
            raise ValueError("Duplicate reviewed response header")
        result[name] = value
    mandatory = {
        "Content-Security-Policy", "Permissions-Policy", "Cache-Control",
        "Strict-Transport-Security", "X-Frame-Options",
        "Referrer-Policy", "X-Content-Type-Options",
        "Cross-Origin-Resource-Policy",
    }
    if set(result) != mandatory or "no-store" not in result["Cache-Control"].lower():
        raise ValueError("Missing required response-header policy")
    return result


SECURITY_HEADERS = parse_headers()


class PreviewHandler(SimpleHTTPRequestHandler):
    """Exact-member static origin; authenticated GitHub gateway required."""

    def __init__(self, *args, directory, **kwargs):
        self.site_dir = Path(directory)
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, fmt, *args):
        # Never emit URL query parameters, session identifiers or test evidence.
        pass

    def send_header(self, keyword, value):
        super().send_header(keyword, value)

    def end_headers(self):
        for key, value in SECURITY_HEADERS.items():
            self.send_header(key, value)
        super().end_headers()

    def _member(self):
        path = urlsplit(self.path).path
        if path not in ROUTES:
            return None
        return "index.html" if path == "/" else path.lstrip("/")

    def translate_path(self, path):
        item = self._member()
        if item is None:
            # Do not delegate directory listing or filesystem path traversal.
            return str(self.site_dir / "__not_served__")
        return str(self.site_dir / item)

    def do_GET(self):
        if self._member() is None:
            self.send_error(404, "Not found")
            return
        super().do_GET()

    def do_HEAD(self):
        if self._member() is None:
            self.send_error(404, "Not found")
            return
        super().do_HEAD()

    def list_directory(self, path):
        self.send_error(404, "Not found")
        return None


def make_handler(site):
    resolved = Path(site).resolve(strict=True)
    expected_files = {p.relative_to(resolved).as_posix()
                      for p in resolved.rglob("*") if p.is_file()}
    if expected_files != EXPECTED or any(p.is_symlink() for p in resolved.rglob("*")):
        raise ValueError("Refusing unexpected or symlinked staged assets")
    return functools.partial(PreviewHandler, directory=str(resolved))


def stage_verified_preview(scratch):
    """Only unpack the exact ten-file CI-reviewed package into temp storage."""
    scratch = Path(scratch)
    if not scratch.is_dir():
        raise ValueError("Scratch directory missing")
    package = scratch / "candidate"
    receipt = build_camera_gate(package)
    archive = package / ZIP_NAME
    if not validate_archive(archive, receipt["fileSha256"]):
        raise ValueError("Unable to confirm ZIP provenance")
    root = scratch / "served"
    root.mkdir(mode=0o700)
    with zipfile.ZipFile(archive) as zf:
        # Member list and types were strictly checked by validate_archive().
        for name in sorted(EXPECTED):
            destination = root / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(zf.read(name))
    make_handler(root)
    return root, receipt


def assert_real_codespace():
    if (os.environ.get("CODESPACES") != "true"
            or not os.environ.get("CODESPACE_NAME")
            or os.environ.get("GITHUB_REPOSITORY") != REPOSITORY
            or not os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN")):
        raise ValueError("Requires GitHub Codespaces for SCSoftwareVentures/Animate")
    current_branch = subprocess.run(
        ["git", "branch", "--show-current"], check=True, capture_output=True,
        text=True,
    ).stdout.strip()
    if current_branch != APPROVED_BRANCH:
        raise ValueError("Refusing unreviewed branch: " + current_branch)
    # Never touch any authentication token. GitHub private forwarding owns login.


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=PORT)
    args = parser.parse_args()
    if args.port != PORT:
        raise SystemExit("BLOCKED: only fixed reviewed port 8765 is allowed")
    try:
        assert_real_codespace()
        with tempfile.TemporaryDirectory(prefix="animate-codespace-owner-") as temp:
            root, receipt = stage_verified_preview(temp)
            handler = make_handler(root)
            # Codespaces forwards the port over HTTPS, with GitHub auth when
            # explicitly left PRIVATE. Local HTTP is not a public release.
            server = ThreadingHTTPServer(("0.0.0.0", PORT), handler)
            server.daemon_threads = True
            try:
                print("ANIMATE verified model-free source commit: " + receipt["sourceCommit"], flush=True)
                print("PRIVATE PORT REQUIRED: GitHub Ports panel MUST say Private.", flush=True)
                print("NEVER CHANGE port visibility to Public or Organization.", flush=True)
                print("Private port login is enforced by GitHub, not this app.", flush=True)
                print("HTTP origin 127.0.0.1:%d — open the GitHub HTTPS forwarded port." % PORT,
                      flush=True)
                print("Open /operator-preview/verify.html and require PASS before camera.", flush=True)
                print("Stop this terminal process and Codespace after the owner trial.", flush=True)
                server.serve_forever(poll_interval=0.2)
            finally:
                server.server_close()
    except (OSError, ValueError, subprocess.CalledProcessError, zipfile.BadZipFile) as e:
        raise SystemExit("BLOCKED: " + str(e))


if __name__ == "__main__":
    main()
