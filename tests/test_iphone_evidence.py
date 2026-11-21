#!/usr/bin/env python3
"""Adversarial tests for the no-network, self-reported iPhone evidence gate.

All reports are SYNTHETIC. Never imply that this represents a physical device.
"""
import copy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from audit_iphone_evidence import (
    BUILD, DEVICE_CONTENTS, DEVICE_LIMITS, ZONE_LIMITS, EvidenceError,
    MAX_BYTES, audit_packet, parse_packet
)

LIGHTS = ("bright", "ordinary", "dim")
ZONES = ("absent", "left", "middle", "right")
SHA = "a" * 40


def histogram(value, samples=60):
    return {"samples": samples, "min": value, "median": value,
            "p95": value, "max": value}


def device(status="timed"):
    complete = status == "timed"
    return {
        "kind": "ANIMATE_LOCAL_DEVICE_PERFORMANCE_SAMPLE",
        "build": BUILD, "detector": "colour", "status": status,
        "complete": complete, "plannedMs": 60000, "observedMs": 60000,
        "sampleWindows": 60,
        "coverage": {
            "requiredWindows": 48, "positiveAnalysedWindows": 60,
            "largestGapMs": 1000, "rejectedWindows": 0,
            "sufficient": complete
        },
        "analysedFps": histogram(20), "animationLoopFps": histogram(60),
        "inferenceMs": histogram(5),
        "inferredFrames": 60, "unmeasuredLatencySamples": 0,
        "interruptions": 0,
        "evidenceType": "UNVERIFIED_LOCAL_PERFORMANCE_PROXY",
        "recognitionAccuracyMeasured": False, "commercialDemandMeasured": False,
        "contents": DEVICE_CONTENTS, "limitations": DEVICE_LIMITS
    }


def zone(label, status="timed"):
    complete = status == "timed"
    absent = label == "absent"
    return {
        "kind": "ANIMATE_SELF_LABELLED_ZONE_CONTROL",
        "build": BUILD, "detector": "colour", "expectedCondition": label,
        "evidenceType": "OPERATOR_LABELLED_PROXY_NOT_VERIFIED_GROUND_TRUTH",
        "status": status, "complete": complete,
        "plannedMs": 10000, "elapsedMs": 10000,
        "coverage": {
            "sampledSeconds": 10, "secondsWithThreeFreshFrames": 10,
            "requiredSeconds": 8, "maxGapMs": 100,
            "rejectedSamples": 0, "adequate": complete
        },
        "analysedFrames": 100, "detectedFrames": 0 if absent else 100,
        "undetectedFrames": 100 if absent else 0,
        "ambiguousFrames": 0, "correctZoneFrames": 0 if absent else 100,
        "wrongZoneFrames": 0, "expectedDwellEvents": 0 if absent else 3,
        "unexpectedDwellEvents": 0,
        "independentlyVerified": False, "userDemandMeasured": False,
        "limitations": ZONE_LIMITS
    }


def packet():
    return {
        "schema": "ANIMATE_IPHONE_OPERATOR_PACKET_V1",
        "sourceCommit": SHA, "deviceClaim": "self-reported-physical-iphone",
        "registeredBeforeTesting": True, "detector": "colour",
        "performanceTrials": [{"lighting": light, "report": device()} for light in LIGHTS],
        "zoneTrials": [
            {"lighting": light, "report": zone(label)}
            for label in ZONES for light in LIGHTS
        ],
    }


class OfflineEvidenceAuditTests(unittest.TestCase):
    def assert_blocked(self, obj):
        with self.assertRaises(EvidenceError):
            audit_packet(obj)

    def test_only_self_reported_completeness_not_device_or_ground_truth(self):
        result = audit_packet(packet())
        self.assertEqual(result["status"], "OPERATOR_PROXY_COMPLETE_UNVERIFIED")
        self.assertTrue(result["minimumOperatorCoverageMet"])
        for field in ("deviceAuthenticityVerified", "buildProvenanceIndependentlyVerified",
                      "groundTruthRecognitionAccuracyMeasured", "userDemandMeasured",
                      "acquisitionReadinessEstablished"):
            self.assertIs(result[field], False, field)
        self.assertEqual(result["performance"]["adequate"], 3)
        self.assertEqual(result["zoneControls"]["absent"]["adequate"], 3)

    def test_missing_attempt_remains_visible_in_denominator(self):
        p = packet()
        p["zoneTrials"].pop()
        r = audit_packet(p)
        self.assertEqual(r["status"], "INSUFFICIENT_OPERATOR_PROXY_COVERAGE")
        self.assertEqual(r["zoneControls"]["right"]["attempts"], 2)

    def test_failure_is_counted_not_silently_excluded(self):
        p = packet()
        report = p["zoneTrials"][0]["report"]
        report["status"] = "insufficient_coverage"
        report["complete"] = False
        report["coverage"].update({
            "sampledSeconds": 2, "secondsWithThreeFreshFrames": 1,
            "maxGapMs": 4000, "adequate": False
        })
        report["detectedFrames"] = 50
        report["undetectedFrames"] = 50
        report["unexpectedDwellEvents"] = 2
        r = audit_packet(p)
        self.assertEqual(r["status"], "INSUFFICIENT_OPERATOR_PROXY_COVERAGE")
        self.assertEqual(r["zoneControls"]["absent"]["attempts"], 3)
        self.assertEqual(r["zoneControls"]["absent"]["incomplete"], 1)
        self.assertEqual(r["zoneControls"]["absent"]["unexpectedDwellProxies"], 2)

    def test_hand_model_is_blocked_from_the_distributed_baseline(self):
        p = packet()
        p["detector"] = "hand"
        self.assert_blocked(p)

    def test_operator_did_not_register_protocol(self):
        p = packet()
        p["registeredBeforeTesting"] = False
        self.assertEqual(audit_packet(p)["status"], "INSUFFICIENT_OPERATOR_PROXY_COVERAGE")

    def test_missing_lighting_condition_cannot_pass(self):
        p = packet()
        p["performanceTrials"][2]["lighting"] = "bright"
        self.assertEqual(audit_packet(p)["status"], "INSUFFICIENT_OPERATOR_PROXY_COVERAGE")

    def test_unknown_field_is_refused_to_avoid_hidden_identity_or_video(self):
        p = packet()
        p["zoneTrials"][0]["report"]["cameraFrame"] = "secret"
        self.assert_blocked(p)
        p = packet()
        p["deviceSerialNumber"] = "secret"
        self.assert_blocked(p)

    def test_incorrect_detector_or_build_cannot_be_pooled(self):
        p = packet()
        p["performanceTrials"][0]["report"]["detector"] = "foreground"
        self.assert_blocked(p)
        p = packet()
        p["zoneTrials"][0]["report"]["build"] = "0.5.0"
        self.assert_blocked(p)

    def test_impossible_frame_and_zone_totals_are_refused(self):
        p = packet()
        p["zoneTrials"][0]["report"]["detectedFrames"] = 50
        self.assert_blocked(p)
        p = packet()
        p["zoneTrials"][3]["report"]["correctZoneFrames"] = 101
        self.assert_blocked(p)

    def test_fake_timed_status_or_coverage_cannot_be_marked_complete(self):
        p = packet()
        p["zoneTrials"][0]["report"]["coverage"]["adequate"] = False
        self.assert_blocked(p)
        p = packet()
        p["performanceTrials"][0]["report"]["coverage"]["sufficient"] = False
        self.assert_blocked(p)
        p = packet()
        p["performanceTrials"][0]["report"]["sampleWindows"] = 1
        self.assert_blocked(p)

    def test_absent_dwell_without_detected_frames_is_refused(self):
        p = packet()
        p["zoneTrials"][0]["report"]["unexpectedDwellEvents"] = 1
        self.assert_blocked(p)

    def test_bad_json_arithmetic_field_is_refused_without_crash(self):
        p = packet()
        p["zoneTrials"][0]["report"]["unexpectedDwellEvents"] = {}
        self.assert_blocked(p)

    def test_invalid_inference_count_or_distribution_is_refused(self):
        p = packet()
        p["performanceTrials"][0]["report"]["inferredFrames"] = 2
        self.assert_blocked(p)
        p = packet()
        p["performanceTrials"][0]["report"]["analysedFps"]["p95"] = 1
        self.assert_blocked(p)

    def test_bool_counts_nan_and_infinity_are_refused(self):
        p = packet()
        p["zoneTrials"][0]["report"]["analysedFrames"] = True
        self.assert_blocked(p)
        p = packet()
        p["performanceTrials"][0]["report"]["inferenceMs"]["median"] = float("nan")
        self.assert_blocked(p)
        p = packet()
        p["performanceTrials"][0]["report"]["inferenceMs"]["p95"] = float("inf")
        self.assert_blocked(p)

    def test_unhashable_input_types_are_refused_without_traceback(self):
        for key, value in (("detector", []), ("detector", {}),
                           ("deviceClaim", [])):
            p = packet()
            p[key] = value
            self.assert_blocked(p)
        p = packet()
        p["performanceTrials"][0]["lighting"] = []
        self.assert_blocked(p)
        p = packet()
        p["zoneTrials"][0]["report"]["status"] = []
        self.assert_blocked(p)

    def test_json_duplicate_fields_nonfinite_numbers_and_oversize_fail(self):
        for raw in (b'{"a":1,"a":2}', b'{"a":NaN}', b"\xff",
                    b"x" * (MAX_BYTES + 1), b""):
            with self.subTest(raw=raw[:12]):
                with self.assertRaises(EvidenceError):
                    parse_packet(raw)

    def test_valid_json_input_uses_same_auditor_without_external_access(self):
        raw = json.dumps(packet()).encode()
        self.assertEqual(
            parse_packet(raw)["status"], "OPERATOR_PROXY_COMPLETE_UNVERIFIED"
        )

    def test_incomplete_trial_is_not_rejected_as_fraud_but_cannot_count_as_success(self):
        p = packet()
        report = p["performanceTrials"][0]["report"]
        report["status"] = "manual"
        report["complete"] = False
        report["observedMs"] = 5000
        report["coverage"]["sufficient"] = False
        result = audit_packet(p)
        self.assertEqual(result["performance"]["incomplete"], 1)
        self.assertEqual(result["status"], "INSUFFICIENT_OPERATOR_PROXY_COVERAGE")

    def test_source_report_contract_strings_match_application(self):
        source = (ROOT / "site" / "core.js").read_text(encoding="utf-8")
        for exact_disclaimer in (DEVICE_CONTENTS, DEVICE_LIMITS, ZONE_LIMITS):
            self.assertIn(exact_disclaimer, source)

    def test_forged_adequate_seconds_without_frames_is_refused(self):
        p = packet()
        p["zoneTrials"][0]["report"]["analysedFrames"] = 7
        p["zoneTrials"][0]["report"]["undetectedFrames"] = 7
        self.assert_blocked(p)

    def test_false_positive_window_count_is_refused(self):
        p = packet()
        p["performanceTrials"][0]["report"]["analysedFps"] = histogram(0)
        self.assert_blocked(p)

    def test_inventory_limits_and_unapproved_metadata_are_refused(self):
        p = packet()
        p["zoneTrials"] *= 6
        self.assert_blocked(p)
        p = packet()
        p["sourceCommit"] = "n" * 40
        self.assert_blocked(p)


if __name__ == "__main__":
    unittest.main(verbosity=2)
