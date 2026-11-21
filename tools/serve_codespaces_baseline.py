#!/usr/bin/env python3
"""Manual-start, no-ML ANIMATE preview for a privately forwarded GitHub Codespace.

This server binds 127.0.0.1 ONLY; Codespaces supplies external TLS and
authentication if the owner separately configures the forwarded port as
PRIVATE. This code cannot verify GitHub's port visibility. It refuses to start
outside Codespaces or without explicit owner authorisation and a verified
six-file baseline candidate. Never run it with a publicly forwarded port.
"""
import argparse
from http.server import ThreadingHTTPServer
import os
from pathlib import Path
import re

from audit_hosted_preview import validate_origin
from serve_safari_https import BenchHandler, load_assets
from vendor_hand_model import ROOT

PORT = 8765
DEFAULT_DOMAIN = "app.github.dev"


def validate_preview_intent(host, env, acknowledged):
    """Pure fail-closed guard; DOES NOT check the actual GitHub port visibility."""
    if not acknowledged:
        raise ValueError("Owner must confirm the GitHub port visibility is Private")
    if env.get("CODESPACES", "").lower() != "true":
        raise ValueError("Refusing to start outside GitHub Codespaces")
    name = env.get("CODESPACE_NAME", "")
    if not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", name):
        raise ValueError("Missing or invalid GitHub Codespace identity")
    if env.get("ANIMATE_OWNER_PREVIEW_APPROVED") != "YES":
        raise ValueError("Preview requires an explicit operator session approval")
    approved_host = validate_origin("https://" + host)
    expected_host = f"{name}-{PORT}.{DEFAULT_DOMAIN}"
    if approved_host != expected_host:
        raise ValueError("Requested Host differs from expected private Codespaces port hostname")
    return approved_host


def prepare_server(site, host, env, acknowledged, port=PORT):
    """Load, verify and bind exactly the six ML-free assets to loopback only."""
    allowed = validate_preview_intent(host, env, acknowledged)
    if port not in (PORT, 0):
        raise ValueError("Unapproved port; the configured preview port is 8765")
    given = Path(site)
    if given.is_symlink():
        raise ValueError("Symlinked baseline site is forbidden")
    staged = given.resolve()
    if staged.is_relative_to(ROOT) or ROOT.is_relative_to(staged):
        raise ValueError("Baseline site must remain outside the repository")
    assets = load_assets(staged)
    server = ThreadingHTTPServer(("127.0.0.1", port), BenchHandler)
    server.allowed_hosts = {allowed, allowed + ":443"}
    server.assets = assets
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--site-dir", required=True, type=Path,
                        help="Previously built no-model candidate/site directory outside Git checkout")
    parser.add_argument("--forwarded-host", required=True,
                        help="Hostname copied from the PRIVATE Codespaces Ports tab; no tokens")
    parser.add_argument("--acknowledge-private-port", action="store_true",
                        help="Owner has independently checked port 8765 visibility is PRIVATE")
    args = parser.parse_args()
    try:
        server = prepare_server(args.site_dir, args.forwarded_host, os.environ,
                                args.acknowledge_private_port)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print("Bound only to 127.0.0.1:8765; the preview must remain PRIVATE in GitHub Ports.", flush=True)
    print("No MediaPipe runtime/model is served; no participant data is accepted.", flush=True)
    print("Stop with Ctrl+C, close the forwarded port and stop/delete Codespace after testing.", flush=True)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
