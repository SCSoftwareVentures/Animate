#!/usr/bin/env python3
"""Zero-network boundary tests for optional manual Codespaces iPhone baseline.

CI does NOT create a Codespace, forward a port, start a remote preview, or
grant GitHub visibility permissions. Only ephemeral 127.0.0.1 requests are made.
"""
import http.client
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from threading import Thread

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from build_baseline_preview import build
from serve_codespaces_baseline import PORT, prepare_server, validate_preview_intent

ENV = {"CODESPACES": "true", "CODESPACE_NAME": "unit-codespace",
       "ANIMATE_OWNER_PREVIEW_APPROVED": "YES"}
HOST = "unit-codespace-8765.app.github.dev"
count = 0


def check(label, outcome):
    global count
    if not outcome:
        raise AssertionError(label)
    count += 1
    print("PASS " + label, flush=True)


def reject(label, f):
    try:
        f()
    except (OSError, ValueError):
        check(label, True)
    else:
        raise AssertionError(label)


def fetch(port, method, path, host=HOST):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        conn.request(method, path, headers={"Host":host})
        response = conn.getresponse()
        return response.status, dict(response.getheaders()), response.read()
    finally:
        conn.close()


def main():
    cfg = json.loads((ROOT / ".devcontainer/devcontainer.json").read_text())
    check("Codespaces never automatically starts the ANIMATE preview",
          not cfg.get("postStartCommand") and not cfg.get("postCreateCommand") and
          not cfg.get("postAttachCommand"))
    check("Codespaces does not automatically forward a preview port",
          cfg["forwardPorts"] == [] and
          cfg["portsAttributes"][str(PORT)]["onAutoForward"] == "ignore" and
          cfg["otherPortsAttributes"]["onAutoForward"] == "ignore")
    check("Optional Codespaces port visibility is requested as private",
          cfg["portsAttributes"][str(PORT)]["visibility"] == "private")
    reject("No owner approval flag means no preview",
           lambda: validate_preview_intent(HOST, {**ENV, "ANIMATE_OWNER_PREVIEW_APPROVED": "NO"}, True))
    reject("No separate private-port acknowledgement means no preview",
           lambda: validate_preview_intent(HOST, ENV, False))
    reject("No Codespaces environment means no preview",
           lambda: validate_preview_intent(HOST, {**ENV, "CODESPACES": "false"}, True))
    reject("Missing Codespaces identity means no preview",
           lambda: validate_preview_intent(HOST, {**ENV, "CODESPACE_NAME": ""}, True))
    reject("Unexpected forwarded hostname is rejected",
           lambda: validate_preview_intent("attacker.example.com", ENV, True))
    reject("Misleading alternate port is rejected",
           lambda: validate_preview_intent("unit-codespace-9999.app.github.dev", ENV, True))
    reject("URL credentials or pathname are rejected",
           lambda: validate_preview_intent("user@"+HOST+"/foo", ENV, True))
    check("Exact owner-acknowledged forwarded hostname is accepted",
          validate_preview_intent(HOST, ENV, True) == HOST)
    with TemporaryDirectory(prefix="animate-iphone-preflight-") as tmp:
        path = Path(tmp) / "preview"
        build(path)
        reject("Raw checkout cannot replace a reviewed staged candidate",
               lambda: prepare_server(ROOT/"site", HOST, ENV, True, port=0))
        reject("Unexpected serving port is not permitted",
               lambda: prepare_server(path/"site", HOST, ENV, True, port=9999))
        source = path/"site"
        server = prepare_server(source, HOST, ENV, True, port=0)
        check("Server binds on loopback only, never a public interface",
              server.server_address[0] == "127.0.0.1")
        check("Only known forwarded Host headers are approved",
              server.allowed_hosts == {HOST, HOST+":443"})
        t = Thread(target=server.serve_forever, kwargs={"poll_interval":.1}, daemon=True)
        t.start()
        try:
            port = server.server_port
            status, headers, html = fetch(port,"GET","/index.html")
            check("Six-file baseline works on approved operator Host",
                  status==200 and b"baselineDisclosure" in html and b'<option value="hand"' not in html)
            check("Browser security policies apply to forwarded page",
                  headers.get("Content-Security-Policy","").find("frame-ancestors 'none'")>=0 and
                  headers.get("Cache-Control")=="no-store" and
                  headers.get("Permissions-Policy","").find("camera=(self)")>=0)
            reject_host, _, _ = fetch(port,"GET","/",host="public.example.com")
            check("Unapproved Host is rejected even on forwarded loopback",reject_host==400)
            missing, _, _ = fetch(port,"GET","/vendor/mediapipe/models/hand_landmarker.task")
            check("Direct MediaPipe model URL remains inaccessible",missing==404)
            private, _, _ = fetch(port,"GET","/MANIFEST.json")
            check("Manifest stays outside the served six-file root",private==404)
            method, _, _ = fetch(port,"POST","/")
            check("Preview refuses data uploads",method==501)
        finally:
            server.shutdown();server.server_close();t.join(timeout=3)
        manifest = path/"MANIFEST.json"
        doc=json.loads(manifest.read_text())
        doc["sourceCommit"]="0"*40
        manifest.write_text(json.dumps(doc))
        reject("Tampered candidate cannot start the preview",
               lambda: prepare_server(source,HOST,ENV,True,port=0))
    print(f"PASS {count}/{count} private-port preview safety checks",flush=True)


if __name__ == "__main__":
    main()
