#!/usr/bin/env python3
"""Offline ANIMATE iPhone operator-report packet auditor.

Does not establish device authenticity, independent ground truth, recognition
accuracy, willingness to pay, ownership of any report, or licensed distribution.
No network operations, uploads, identifiers, camera frames or raw logs.
"""
import argparse
import json
import math
from pathlib import Path
import re

MAX_BYTES = 256 * 1024
BUILD = "0.7.0"
LIGHTS = {"bright", "ordinary", "dim"}
ZONES = ("absent", "left", "middle", "right")
DETECTORS = {"colour", "foreground"}  # Hand-ML redistribution remains blocked.
FINAL_STATUSES = {"timed", "manual", "camera_stopped", "interrupted", "insufficient_coverage"}

DEVICE_CONTENTS = "Numeric performance only. No video, coordinates, IDs, user agent or network upload."
DEVICE_LIMITS = ("Duration alone cannot pass: requires 80% observed and positive analysed "
                 "windows, inference calls and no sampling gaps over 2.5 seconds. "
                 "This does not establish sensor FPS, detection accuracy, battery, "
                 "thermals, real-device provenance or commercial demand.")
ZONE_LIMITS = ("Requires three analysed frames in each of 80% of seconds. One manually "
               "labelled static condition. Dwell events are proxy activations, not "
               "observed task completions. An absent-labelled false alarm is an "
               "operator-reported proxy, not independently verified accuracy.")


class EvidenceError(ValueError):
    """Unsafe, malformed, inconsistent or unreviewable operator report."""


def require(predicate, message):
    if not predicate:
        raise EvidenceError(message)


def exact_keys(value, keys, context):
    require(isinstance(value, dict) and set(value) == set(keys),
            "Unexpected or missing fields in " + context)


def integer(value, low, high, name):
    require(type(value) is int and low <= value <= high, "Invalid count: " + name)


def number(value, low, high, name):
    require(type(value) in (int, float) and math.isfinite(value) and low <= value <= high,
            "Invalid measurement: " + name)


def distribution(value, limit, name):
    exact_keys(value, {"samples", "min", "median", "p95", "max"}, name)
    integer(value["samples"], 0, 4096, name + ".samples")
    values = [value[k] for k in ("min", "median", "p95", "max")]
    if value["samples"] == 0:
        require(all(v is None for v in values), "Empty distribution has numeric values")
    else:
        for k, v in zip(("min", "median", "p95", "max"), values):
            number(v, 0, limit, name + "." + k)
        require(values == sorted(values), "Impossible distribution order: " + name)


def audit_device(sample, method):
    keys = {"kind", "build", "detector", "status", "complete", "plannedMs",
            "observedMs", "sampleWindows", "coverage", "analysedFps",
            "animationLoopFps", "inferenceMs", "inferredFrames",
            "unmeasuredLatencySamples", "interruptions", "evidenceType",
            "recognitionAccuracyMeasured", "commercialDemandMeasured",
            "contents", "limitations"}
    exact_keys(sample, keys, "device sample")
    require(sample["kind"] == "ANIMATE_LOCAL_DEVICE_PERFORMANCE_SAMPLE" and
            sample["build"] == BUILD and sample["detector"] == method and
            sample["evidenceType"] == "UNVERIFIED_LOCAL_PERFORMANCE_PROXY" and
            sample["recognitionAccuracyMeasured"] is False and
            sample["commercialDemandMeasured"] is False and
            sample["contents"] == DEVICE_CONTENTS and
            sample["limitations"] == DEVICE_LIMITS, "Invalid device provenance/disclaimer")
    require(type(sample["status"]) is str and sample["status"] in FINAL_STATUSES and
            sample["complete"] is (sample["status"] == "timed"),
            "Unfinished or inconsistent device trial")
    integer(sample["plannedMs"], 60000, 60000, "device duration")
    integer(sample["observedMs"], 0, 60000, "observed device time")
    for field, limit in (("sampleWindows", 120), ("inferredFrames", 1000000),
                         ("unmeasuredLatencySamples", 1000000),
                         ("interruptions", 10000)):
        integer(sample[field], 0, limit, field)
    coverage = sample["coverage"]
    exact_keys(coverage, {"requiredWindows", "positiveAnalysedWindows",
                          "largestGapMs", "rejectedWindows", "sufficient"}, "device coverage")
    integer(coverage["requiredWindows"], 48, 48, "requiredWindows")
    integer(coverage["positiveAnalysedWindows"], 0, 120, "positiveAnalysedWindows")
    integer(coverage["rejectedWindows"], 0, 1000000, "rejectedWindows")
    number(coverage["largestGapMs"], 0, 60000, "largestGapMs")
    require(type(coverage["sufficient"]) is bool and
            coverage["positiveAnalysedWindows"] <= sample["sampleWindows"],
            "Impossible device coverage")
    for field, max_value in (("analysedFps", 240), ("animationLoopFps", 240),
                             ("inferenceMs", 120000)):
        distribution(sample[field], max_value, field)
    require(sample["analysedFps"]["samples"] == sample["sampleWindows"] and
            sample["animationLoopFps"]["samples"] == sample["sampleWindows"] and
            sample["inferenceMs"]["samples"] +
            sample["unmeasuredLatencySamples"] == sample["inferredFrames"],
            "Contradictory measurement sample counts")
    require((sample["analysedFps"]["min"] > 0) ==
            (coverage["positiveAnalysedWindows"] == sample["sampleWindows"])
            if sample["sampleWindows"] > 0 else
            coverage["positiveAnalysedWindows"] == 0,
            "Contradictory positive analysed window count")
    if coverage["sufficient"]:
        require(sample["observedMs"] == 60000 and
                sample["sampleWindows"] >= 48 and
                coverage["positiveAnalysedWindows"] >= 48 and
                sample["inferredFrames"] >= 48 and
                coverage["rejectedWindows"] == 0 and
                coverage["largestGapMs"] <= 2500,
                "Claimed device coverage is inconsistent")
    if sample["status"] == "timed":
        require(sample["observedMs"] == 60000 and coverage["sufficient"] and
                sample["sampleWindows"] >= 48 and
                coverage["positiveAnalysedWindows"] >= 48 and
                sample["inferredFrames"] >= 48 and
                coverage["rejectedWindows"] == 0 and
                coverage["largestGapMs"] <= 2500 and sample["interruptions"] == 0,
                "Timed device trial lacks the required observations")
    elif sample["status"] == "insufficient_coverage":
        require(not coverage["sufficient"], "Coverage failure claims sufficient coverage")
    return sample["status"] == "timed"


def audit_zone(sample, method, label):
    keys = {"kind", "build", "detector", "expectedCondition", "evidenceType",
            "status", "complete", "elapsedMs", "plannedMs", "coverage",
            "analysedFrames", "detectedFrames", "undetectedFrames", "ambiguousFrames",
            "correctZoneFrames", "wrongZoneFrames", "expectedDwellEvents",
            "unexpectedDwellEvents", "independentlyVerified", "userDemandMeasured",
            "limitations"}
    exact_keys(sample, keys, "zone control")
    require(sample["kind"] == "ANIMATE_SELF_LABELLED_ZONE_CONTROL" and
            sample["build"] == BUILD and sample["detector"] == method and
            sample["expectedCondition"] == label and
            sample["evidenceType"] == "OPERATOR_LABELLED_PROXY_NOT_VERIFIED_GROUND_TRUTH" and
            sample["independentlyVerified"] is False and
            sample["userDemandMeasured"] is False and
            sample["limitations"] == ZONE_LIMITS, "Invalid zone provenance/disclaimer")
    require(type(sample["status"]) is str and sample["status"] in FINAL_STATUSES and
            sample["complete"] is (sample["status"] == "timed"),
            "Unfinished or inconsistent zone trial")
    integer(sample["plannedMs"], 10000, 10000, "zone duration")
    integer(sample["elapsedMs"], 0, 10000, "zone elapsed time")
    for field in ("analysedFrames", "detectedFrames", "undetectedFrames",
                  "ambiguousFrames", "correctZoneFrames", "wrongZoneFrames",
                  "expectedDwellEvents", "unexpectedDwellEvents"):
        integer(sample[field], 0, 100000, field)
    require(sample["analysedFrames"] ==
            sample["detectedFrames"] + sample["undetectedFrames"] and
            sample["ambiguousFrames"] <= sample["undetectedFrames"] and
            sample["expectedDwellEvents"] + sample["unexpectedDwellEvents"] <=
            sample["analysedFrames"] and
            sample["expectedDwellEvents"] + sample["unexpectedDwellEvents"] <=
            sample["detectedFrames"], "Inconsistent zone frame/event counts")
    if label == "absent":
        require(sample["correctZoneFrames"] == 0 and
                sample["wrongZoneFrames"] == 0 and
                sample["expectedDwellEvents"] == 0,
                "Absent-labelled trial has impossible expected hits")
    else:
        require(sample["correctZoneFrames"] + sample["wrongZoneFrames"] ==
                sample["detectedFrames"], "Zone-labelled sample lost detected frames")
    coverage = sample["coverage"]
    exact_keys(coverage, {"sampledSeconds", "secondsWithThreeFreshFrames",
                          "requiredSeconds", "maxGapMs", "rejectedSamples",
                          "adequate"}, "zone coverage")
    for field, low, high in (("sampledSeconds", 0, 10),
                             ("secondsWithThreeFreshFrames", 0, 10),
                             ("requiredSeconds", 8, 8),
                             ("rejectedSamples", 0, 100000)):
        integer(coverage[field], low, high, field)
    number(coverage["maxGapMs"], 0, 10000, "maxGapMs")
    require(type(coverage["adequate"]) is bool and
            coverage["secondsWithThreeFreshFrames"] <= coverage["sampledSeconds"] and
            sample["analysedFrames"] >= 3 * coverage["secondsWithThreeFreshFrames"] and
            sample["analysedFrames"] >= coverage["sampledSeconds"],
            "Impossible zone coverage")
    if coverage["adequate"]:
        require(sample["elapsedMs"] == 10000 and
                coverage["secondsWithThreeFreshFrames"] >= 8 and
                coverage["rejectedSamples"] == 0 and coverage["maxGapMs"] <= 2500,
                "Claimed zone coverage is inconsistent")
    if sample["status"] == "timed":
        require(sample["elapsedMs"] == 10000 and coverage["adequate"] and
                coverage["secondsWithThreeFreshFrames"] >= 8 and
                coverage["rejectedSamples"] == 0 and coverage["maxGapMs"] <= 2500,
                "Timed zone trial lacks fresh-frame coverage")
    elif sample["status"] == "insufficient_coverage":
        require(not coverage["adequate"], "Zone coverage failure marked adequate")
    return sample["status"] == "timed"


def audit_packet(packet):
    exact_keys(packet, {"schema", "sourceCommit", "deviceClaim",
                        "registeredBeforeTesting", "detector",
                        "performanceTrials", "zoneTrials"}, "packet")
    require(packet["schema"] == "ANIMATE_IPHONE_OPERATOR_PACKET_V1" and
            isinstance(packet["sourceCommit"], str) and
            re.fullmatch(r"[0-9a-f]{40}", packet["sourceCommit"]) is not None,
            "Invalid self-declared build SHA")
    require(packet["deviceClaim"] == "self-reported-physical-iphone" and
            type(packet["registeredBeforeTesting"]) is bool and
            type(packet["detector"]) is str and
            packet["detector"] in DETECTORS, "Unsupported device/detector claim")
    perf, zones = packet["performanceTrials"], packet["zoneTrials"]
    require(type(perf) is list and 0 < len(perf) <= 64 and
            type(zones) is list and 0 < len(zones) <= 64,
            "Missing or unbounded trial inventory")
    method = packet["detector"]
    perf_adequate = 0
    perf_lights = set()
    for trial in perf:
        exact_keys(trial, {"lighting", "report"}, "performance attempt")
        require(type(trial["lighting"]) is str and trial["lighting"] in LIGHTS,
                "Unrecognised lighting label")
        if audit_device(trial["report"], method):
            perf_adequate += 1
            perf_lights.add(trial["lighting"])
    per_zone = {z: {"attempts": 0, "adequate": 0, "lighting": set(),
                    "unexpectedDwellProxies": 0} for z in ZONES}
    for trial in zones:
        exact_keys(trial, {"lighting", "report"}, "zone attempt")
        require(type(trial["lighting"]) is str and trial["lighting"] in LIGHTS,
                "Unrecognised lighting label")
        label = trial["report"].get("expectedCondition") if isinstance(trial["report"], dict) else None
        require(label in ZONES, "Unrecognised expected condition")
        # Validate every value before using it in arithmetic. Untrusted JSON
        # must produce a bounded rejection rather than a TypeError traceback.
        adequate = audit_zone(trial["report"], method, label)
        d = per_zone[label]
        d["attempts"] += 1
        d["unexpectedDwellProxies"] += trial["report"]["unexpectedDwellEvents"]
        if adequate:
            d["adequate"] += 1
            d["lighting"].add(trial["lighting"])
    sufficient = (packet["registeredBeforeTesting"] and
                  perf_adequate >= 3 and perf_lights == LIGHTS and
                  all(d["adequate"] >= 3 and d["lighting"] == LIGHTS
                      for d in per_zone.values()))
    return {
        "kind": "ANIMATE_SELF_REPORTED_IPHONE_PACKET_AUDIT",
        "status": ("OPERATOR_PROXY_COMPLETE_UNVERIFIED" if sufficient else
                   "INSUFFICIENT_OPERATOR_PROXY_COVERAGE"),
        "sourceCommitClaim": packet["sourceCommit"],
        "detector": method,
        "registeredBeforeTestingSelfDeclared": packet["registeredBeforeTesting"],
        "performance": {"attempts": len(perf), "adequate": perf_adequate,
                        "incomplete": len(perf) - perf_adequate},
        "zoneControls": {k: {
            "attempts": d["attempts"], "adequate": d["adequate"],
            "incomplete": d["attempts"] - d["adequate"],
            "unexpectedDwellProxies": d["unexpectedDwellProxies"]
        } for k, d in per_zone.items()},
        "minimumOperatorCoverageMet": bool(sufficient),
        "deviceAuthenticityVerified": False,
        "buildProvenanceIndependentlyVerified": False,
        "groundTruthRecognitionAccuracyMeasured": False,
        "userDemandMeasured": False,
        "acquisitionReadinessEstablished": False,
        "warning": ("Numeric self-reports, lighting labels, build SHA and registration "
                    "are not independently authenticated. False hits are operator-labelled "
                    "proxies, not a false-positive accuracy rate. All attempts are counted.")
    }


def unique_pairs(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            raise EvidenceError("Duplicate JSON field")
        obj[key] = value
    return obj


def invalid_constant(_value):
    raise EvidenceError("Non-finite JSON number")


def parse_packet(raw):
    require(type(raw) is bytes and 0 < len(raw) <= MAX_BYTES, "Missing or oversized packet")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=unique_pairs,
                           parse_constant=invalid_constant)
    except (ValueError, UnicodeDecodeError, RecursionError) as error:
        raise EvidenceError("Invalid JSON packet") from error
    return audit_packet(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="Local-only JSON operator packet; never commit participant data")
    args = parser.parse_args()
    try:
        raw = args.path.read_bytes()
        result = parse_packet(raw)
    except (OSError, EvidenceError) as error:
        parser.exit(1, "BLOCKED: " + str(error) + "\n")
    print(json.dumps(result, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
