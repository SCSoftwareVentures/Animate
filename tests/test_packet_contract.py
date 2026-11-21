#!/usr/bin/env python3
"""Cross-language contract: actual JS recorder packets must pass the Python auditor.

Generated reports are SYNTHETIC from deterministic core factories, not iPhone
measurements or physical-device evidence. No network, files or external services.
"""
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from audit_iphone_evidence import audit_packet, EvidenceError

NODE = r"""
const C = require('./site/core.js');
const recorder = C.createOperatorPacketRecorder();
const LIGHTS = ['bright','ordinary','dim'];
recorder.begin('a'.repeat(40),'colour',true,true);
for (const light of LIGHTS) {
  const perf = C.createDeviceBench();
  perf.begin(0,'colour');
  for(let i=1;i<=60;i++){perf.noteLatency(8);perf.noteWindow(i*1000,18,60);}
  const result=perf.snapshot(60000);
  if(!result.complete)throw Error('Deterministic 60-second performance fixture incomplete');
  recorder.add('performance',light,result);
}
for(const label of ['absent','left','middle','right']) {
  for(const light of LIGHTS) {
    const z=C.createZoneControlProbe();
    z.begin(0,label,'colour');
    for(let i=1;i<=100;i++) z.add(label==='absent'?null:
      {x:label==='left'?.1:label==='middle'?.5:.9,y:.5},i*100);
    const result=z.snapshot(10000);
    if(!result.complete)throw Error('Deterministic 10-second zone fixture incomplete');
    recorder.add('zone',light,result);
  }
}
console.log(JSON.stringify(recorder.packet()));
"""


class PacketContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        run = subprocess.run(["node", "-e", NODE], cwd=ROOT, capture_output=True,
                             text=True, timeout=20, check=True)
        cls.packet = json.loads(run.stdout)

    def test_actual_javascript_reports_pass_python_contract_without_accuracy_claim(self):
        result = audit_packet(self.packet)
        self.assertEqual(result["status"], "OPERATOR_PROXY_COMPLETE_UNVERIFIED")
        self.assertEqual(result["performance"]["attempts"], 3)
        self.assertEqual(result["zoneControls"]["absent"]["attempts"], 3)
        self.assertFalse(result["groundTruthRecognitionAccuracyMeasured"])
        self.assertFalse(result["deviceAuthenticityVerified"])

    def test_staged_packet_contains_no_identifying_or_raw_fields(self):
        payload = json.dumps(self.packet)
        for forbidden in ("participantId", "userAgent", "cameraFrame", "coordinates", "recordId"):
            self.assertNotIn('"' + forbidden + '":', payload)

    def test_python_diligence_gate_rejects_unjustified_completed_gap(self):
        packet = json.loads(json.dumps(self.packet))
        packet["performanceTrials"][0]["report"]["coverage"]["largestGapMs"] = 3000
        with self.assertRaises(EvidenceError):
            audit_packet(packet)

    def test_incomplete_attempt_stays_in_denominator(self):
        packet = json.loads(json.dumps(self.packet))
        zone = packet["zoneTrials"][0]["report"]
        zone["status"] = "manual"
        zone["complete"] = False
        # A manual finish at the full boundary can be data-adequate but
        # must never count as an automatic timed success.
        zone["elapsedMs"] = 10000
        zone["coverage"]["adequate"] = True
        summary = audit_packet(packet)
        self.assertEqual(summary["zoneControls"]["absent"]["incomplete"], 1)
        self.assertEqual(summary["status"], "INSUFFICIENT_OPERATOR_PROXY_COVERAGE")


if __name__ == "__main__":
    unittest.main(verbosity=2)
