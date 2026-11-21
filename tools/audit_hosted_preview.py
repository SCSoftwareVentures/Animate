#!/usr/bin/env python3
"""Owner-gated external HTTPS preview audit; no hosting or deployment.

CI tests this tool with IN-MEMORY responses only. Live network requests are
impossible unless the operator explicitly supplies --allow-network-audit, a
matching ANIMATE_APPROVED_PREVIEW_HOST, and ANIMATE_PREVIEW_AUTH_COOKIE.
A technical pass is not legal, privacy, hosting or release approval.
"""
import argparse
from dataclasses import dataclass
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import ssl
from urllib.parse import urlsplit

from build_baseline_preview import sha256
from serve_safari_https import verify_no_model_candidate
from vendor_hand_model import SITE_FILES

MODEL_PATHS = (
    "/vendor/mediapipe/vision_bundle.mjs",
    "/vendor/mediapipe/models/hand_landmarker.task",
    "/vendor/mediapipe/wasm/vision_wasm_internal.wasm",
)
FORBIDDEN_PATHS = MODEL_PATHS + (
    "/MANIFEST.json", "/.env", "/research-ledger.csv",
)
MAX_RESPONSE = 2 * 1024 * 1024
REQUIRED_POLICY = ("default-src 'none'", "script-src 'self'",
                   "connect-src 'self'", "frame-ancestors 'none'")


class AuditError(ValueError):
    pass


@dataclass(frozen=True)
class Evidence:
    status: int
    headers: dict
    body: bytes = b""

    def header(self, name):
        return self.headers.get(name.lower(), "")


def require(condition, description):
    if not condition:
        raise AuditError(description)


def validate_origin(origin):
    """Require an exact public HTTPS host; no embedded credentials or query tokens."""
    try:
        parts = urlsplit(origin)
        port = parts.port
    except ValueError as error:
        raise AuditError("Malformed HTTPS origin") from error
    require(parts.scheme == "https" and parts.netloc and parts.hostname,
            "Preview must use verified HTTPS")
    require(not parts.username and not parts.password and not parts.query and not parts.fragment,
            "Origin cannot include credentials, query strings or fragments")
    require(parts.path in ("", "/") and port in (None, 443),
            "Only a canonical HTTPS origin on port 443 is allowed")
    host = parts.hostname.lower()
    require(len(host) <= 253 and "." in host and not host.endswith(".") and
            all(re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label)
                for label in host.split(".")),
            "Preview hostname must be a normal fully-qualified DNS name")
    try:
        ipaddress.ip_address(host)
    except ValueError:
        pass
    else:
        raise AuditError("IP-literal origins are not accepted for hosted previews")
    require(not host.endswith((".localhost", ".local", ".internal", ".test",
                                ".example", ".invalid")) and host != "localhost",
            "Reserved or internal preview hosts are not accepted")
    return host


def validated_candidate(site):
    """Validate the six-file no-ML candidate plus the external source manifest."""
    site = Path(site)
    require(verify_no_model_candidate(site), "Invalid no-ML baseline site or source commit")
    manifest_file = site.parent / "MANIFEST.json"
    require(manifest_file.is_file() and not manifest_file.is_symlink() and
            manifest_file.stat().st_size < 16384, "Missing or oversized manifest")
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as error:
        raise AuditError("Invalid candidate manifest") from error
    require(isinstance(manifest, dict) and
            manifest.get("kind") == "NON_DISTRIBUTED_INTERNAL_BASELINE_CANDIDATE" and
            manifest.get("containsMediaPipeAssets") is False and
            manifest.get("hasHandMlMenuOption") is False and
            manifest.get("hostingApproved") is False and
            manifest.get("deviceValidationCompleted") is False and
            isinstance(manifest.get("sourceCommit"), str) and
            re.fullmatch(r"[0-9a-f]{40}", manifest["sourceCommit"]) and
            isinstance(manifest.get("files"), dict) and
            set(manifest["files"]) == set(SITE_FILES),
            "Baseline manifest is invalid or claims pre-approved distribution")
    expected = {}
    for name in SITE_FILES:
        digest = sha256(site / name)
        require(manifest["files"][name] == digest, "Baseline manifest hash mismatch: " + name)
        expected["/" + name] = (site / name).read_bytes()
    return expected


def check_headers(response, path):
    require(response.header("cache-control").lower().find("no-store") >= 0,
            "Preview response can be cached: " + path)
    require(response.header("x-content-type-options").lower() == "nosniff",
            "Missing nosniff: " + path)
    require(response.header("x-frame-options").upper() == "DENY",
            "Framing is not prohibited: " + path)
    require(response.header("cross-origin-resource-policy").lower() == "same-origin",
            "Cross-origin resource policy is not restrictive: " + path)
    require(response.header("referrer-policy").lower() == "no-referrer",
            "Referrer policy can leak the preview URL: " + path)
    policy = response.header("content-security-policy").lower()
    require(all(part in policy for part in REQUIRED_POLICY),
            "CSP is missing an essential restriction: " + path)
    permissions = response.header("permissions-policy").replace(" ", "").lower()
    require("camera=(self)" in permissions and "microphone=()" in permissions and
            "geolocation=()" in permissions, "Permissions policy is too broad: " + path)
    require(not response.header("access-control-allow-origin"),
            "Unexpected third-party CORS permission: " + path)
    hsts = response.header("strict-transport-security").lower()
    match = re.search(r"(?:^|;)\s*max-age=(\d+)(?:;|$)", hsts)
    require(match is not None and int(match.group(1)) >= 86400,
            "HTTPS HSTS minimum not met: " + path)


def audit_responses(expected, fetch):
    """Pure audit: fetch(method, path, authorized) returns Evidence; no network itself."""
    require(set(expected) == {"/" + name for name in SITE_FILES},
            "Expected files must match the exact six-file site inventory")

    # Verify that access control covers every static file, not only /index.html.
    for path in sorted(expected):
        denied = fetch("GET", path, False)
        require(denied.status in (401, 403), "Unauthorised request exposed or redirected: " + path)
        require(not denied.body or b"ANIMATE v0.7" not in denied.body,
                "Unauthorised response disclosed application content: " + path)

        granted = fetch("GET", path, True)
        require(granted.status == 200, "Authenticated static file unavailable: " + path)
        require(len(granted.body) <= MAX_RESPONSE and
                hashlib.sha256(granted.body).digest() == hashlib.sha256(expected[path]).digest(),
                "Hosted content differs from reviewed candidate: " + path)
        check_headers(granted, path)

    for path in FORBIDDEN_PATHS:
        for authorized in (False, True):
            response = fetch("GET", path, authorized)
            require(response.status in (403, 404),
                    "Hosted preview exposes model, manifest or research data"
                    + (" to an unauthorised visitor: " if not authorized else ": ") + path)
    post = fetch("POST", "/", True)
    require(post.status in (403, 404, 405, 501),
            "Host unexpectedly accepts browser uploads")
    return {
        "technicalPreflight": "PASS",
        "checkedStaticFiles": len(expected),
        "accessControl": "Verified on all six static assets, with supplied credentials",
        "canonicalSensitivePaths": "Denied in both authenticated and unauthenticated sessions",
        "deploymentApproved": False,
        "privacyOperatorApproved": False,
        "physicalIphoneVerified": False,
        "limitations": ("A successful server-response audit does not verify hosting logs, "
                        "DNS/identity operations, revocation, browser camera behaviour, "
                        "legally approved privacy wording or model redistribution rights."),
    }


def ensure_public_dns(host):
    """Reject current non-public DNS destinations before making an approved request."""
    try:
        records = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as error:
        raise AuditError("Approved preview hostname failed DNS lookup") from error
    require(bool(records), "Approved preview host has no DNS records")
    approved_addresses = []
    for entry in records:
        try:
            address = ipaddress.ip_address(entry[4][0])
        except ValueError as error:
            raise AuditError("Invalid preview DNS address") from error
        require(address.is_global, "Preview DNS resolves to a private or reserved address")
        approved_addresses.append(str(address))
    return approved_addresses[0]


class PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to a previously checked global IP, with the approved DNS name as TLS SNI."""
    def __init__(self, host, pinned_ip):
        super().__init__(host, port=443, timeout=12, context=ssl.create_default_context())
        self._pinned_ip = pinned_ip

    def connect(self):
        raw = socket.create_connection((self._pinned_ip, 443), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(raw, server_hostname=self.host)
        except Exception:
            raw.close()
            raise


def make_network_fetch(host, cookie, pinned_ip):
    """Strict TLS pinned to a public address; never follow redirects or log tokens."""
    require(bool(cookie) and "\r" not in cookie and "\n" not in cookie and
            len(cookie) <= 4096, "Approved cookie must be supplied via environment")
    def fetch(method, path, authorized):
        require(method in ("GET", "POST") and path.startswith("/") and
                "?" not in path and "#" not in path, "Unexpected audit HTTP request")
        conn = PinnedHTTPSConnection(host, pinned_ip)
        headers = {"Accept": "text/html,application/javascript,text/css,*/*",
                   "User-Agent": "ANIMATE-private-preview-audit/1",
                   "Cache-Control": "no-store"}
        if authorized:
            headers["Cookie"] = cookie
        try:
            conn.request(method, path, headers=headers)
            response = conn.getresponse()
            data = response.read(MAX_RESPONSE + 1)
            if len(data) > MAX_RESPONSE:
                raise AuditError("Preview response exceeded bounded audit limit")
            pairs = [(name.lower(), value) for name, value in response.getheaders()]
            # Duplicate security headers can produce contradictory gateway behaviour.
            names = [name for name, _ in pairs]
            for sensitive in ("content-security-policy", "permissions-policy",
                              "access-control-allow-origin"):
                require(names.count(sensitive) <= 1,
                        "Repeated security header in preview response")
            return Evidence(response.status, dict(pairs), data)
        except (OSError, ssl.SSLError, http.client.HTTPException) as error:
            raise AuditError("HTTPS preview request failed TLS or network validation") from error
        finally:
            conn.close()
    return fetch


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origin", required=True,
                        help="Owner-approved https://hostname only; never include a token")
    parser.add_argument("--site-dir", type=Path, required=True,
                        help="Exact six-file candidate staged outside checkout")
    parser.add_argument("--allow-network-audit", action="store_true",
                        help="Explicitly permit read-only requests to the approved host")
    args = parser.parse_args()
    try:
        host = validate_origin(args.origin)
        require(args.allow_network_audit,
                "Network audit disabled; owner must explicitly authorise the host and run")
        require(os.environ.get("ANIMATE_APPROVED_PREVIEW_HOST", "").lower() == host,
                "Approval gate: host does not match ANIMATE_APPROVED_PREVIEW_HOST")
        cookie = os.environ.get("ANIMATE_PREVIEW_AUTH_COOKIE", "")
        expected = validated_candidate(args.site_dir)
        pinned_ip = ensure_public_dns(host)
        report = audit_responses(expected, make_network_fetch(host, cookie, pinned_ip))
        print(json.dumps(report, indent=2, sort_keys=True))
        print("PASS: server-response preflight only; no deployment or release approval")
    except (AuditError, OSError, ValueError) as error:
        raise SystemExit("BLOCKED: " + str(error))


if __name__ == "__main__":
    main()
