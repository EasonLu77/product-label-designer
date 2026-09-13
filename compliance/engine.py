"""Validated declarative rules, three-valued logic, reproducible reports.

None means unknown, never false. No eval, executable rule strings or network IO.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
ENGINE_VERSION = "0.1.0"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def validate_fact(value, spec):
    if value is None:
        return
    kind = spec["type"]
    if kind == "boolean" and type(value) is not bool:
        raise ValueError("Expected boolean or null")
    if kind == "enum" and value not in spec["options"]:
        raise ValueError(f"Expected one of {spec['options']}")
    if kind == "number":
        import math
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError("Expected a finite nonnegative number or null")


def validate_expression(expr, fields):
    for op in ("all", "any"):
        if op in expr:
            for child in expr[op]:
                validate_expression(child, fields)
            return
    if "not" in expr:
        validate_expression(expr["not"], fields)
        return
    name = expr["field"]
    if name not in fields:
        raise ValueError(f"Unknown rule field: {name}")
    if expr["op"] in ("gte", "lte") and fields[name]["type"] != "number":
        raise ValueError(f"Numeric operator on nonnumeric field: {name}")
    values = expr["value"] if expr["op"] == "in" else [expr["value"]]
    for value in values:
        if value is None:
            raise ValueError("Rules cannot compare against null; unknown is handled by the engine")
        validate_fact(value, fields[name])


def load_bundle(root=ROOT):
    data = Path(root) / "data"
    bundle = {key: read_json(data / f"{key}.json") for key in ("rules", "fields", "markets", "coverage")}
    schema = read_json(data / "rules.schema.json")
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(bundle["rules"])
    ids = set()
    for rule in bundle["rules"]["rules"]:
        if rule["id"] in ids:
            raise ValueError(f"Duplicate rule ID: {rule['id']}; one revision per ID per pack")
        ids.add(rule["id"])
        if not set(rule["markets"]) <= bundle["markets"].keys():
            raise ValueError(f"Unknown market in {rule['id']}")
        validate_expression(rule["when"], bundle["fields"])
        for location in rule["locations"]:
            if "when" in location:
                validate_expression(location["when"], bundle["fields"])
        start, end = rule["effective_from"], rule["effective_to"]
        if start and end and start > end:
            raise ValueError(f"Reversed effective dates: {rule['id']}")
        review = rule["review"]
        if review["status"] != "draft":
            if not review["last_reviewed_on"] or not review["reviewer"] or not any(s["retrieval_status"] == "read" for s in rule["sources"]):
                raise ValueError(f"Checked rules need reviewer, review date and read source: {rule['id']}")
    if set(bundle["coverage"]) != set(bundle["markets"]):
        raise ValueError("Every market must have an explicit coverage record")
    return bundle


def validate_profile(profile, bundle):
    if not isinstance(profile, dict) or set(profile) != {"schema_version", "name", "markets", "facts", "evidence_notes"}:
        raise ValueError("Profile must contain schema_version, name, markets, facts and evidence_notes only")
    if profile["schema_version"] != "1.0":
        raise ValueError("Unsupported profile schema_version")
    if not isinstance(profile["name"], str) or not profile["name"].strip():
        raise ValueError("Product name is required")
    if not isinstance(profile["evidence_notes"], str):
        raise ValueError("Evidence notes must be text")
    selected = profile["markets"]
    if not isinstance(selected, list) or not selected or any(not isinstance(m, str) or m not in bundle["markets"] for m in selected) or len(set(selected)) != len(selected):
        raise ValueError("Select at least one supported market without duplicates")
    facts = profile["facts"]
    if not isinstance(facts, dict):
        raise ValueError("facts must be an object")
    for key, value in facts.items():
        if key not in bundle["fields"]:
            raise ValueError(f"Unknown product field: {key}")
        try:
            validate_fact(value, bundle["fields"][key])
        except ValueError as exc:
            raise ValueError(f"{key}: {exc}") from exc
    lo, hi = facts.get("voltage_min"), facts.get("voltage_max")
    if lo is not None and hi is not None and lo > hi:
        raise ValueError("Minimum voltage cannot exceed maximum voltage")


def evaluate(expr, facts):
    """Return (True/False/None, unresolved fields, full expression trace)."""
    for op in ("all", "any"):
        if op in expr:
            children = [evaluate(e, facts) for e in expr[op]]
            values = [c[0] for c in children]
            if op == "all":
                value = False if False in values else None if None in values else True
            else:
                value = True if True in values else None if None in values else False
            missing = sorted({f for c in children for f in c[1]}) if value is None else []
            return value, missing, {"operator": op, "result": value, "children": [c[2] for c in children]}
    if "not" in expr:
        value, missing, trace = evaluate(expr["not"], facts)
        result = None if value is None else not value
        return result, missing, {"operator": "not", "result": result, "child": trace}
    key, op, expected = expr["field"], expr["op"], expr["value"]
    actual = facts.get(key)
    if actual is None:
        result = None
    elif op == "eq":
        result = actual == expected
    elif op == "in":
        result = actual in expected
    elif op == "gte":
        result = actual >= expected
    elif op == "lte":
        result = actual <= expected
    else:
        raise ValueError(f"Unsupported operator: {op}")
    return result, [key] if result is None else [], {"field": key, "operator": op, "expected": expected, "actual": actual, "result": result}


def assess(profile, bundle, assessed_on=None):
    validate_profile(profile, bundle)
    today = assessed_on or date.today()
    facts = profile["facts"]
    results = []
    for market in profile["markets"]:
        for rule in bundle["rules"]["rules"]:
            if market not in rule["markets"]:
                continue
            matched, missing, trace = evaluate(rule["when"], facts)
            reviewed = rule["review"]["last_reviewed_on"]
            stale = bool(reviewed and (today - date.fromisoformat(reviewed)).days > 180)
            outside = bool((rule["effective_from"] and today.isoformat() < rule["effective_from"]) or (rule["effective_to"] and today.isoformat() > rule["effective_to"]))
            future_review = bool(reviewed and reviewed > today.isoformat())
            unresolved_rule = rule["review"]["status"] == "draft" or stale or future_review
            if outside:
                status, reason = "Conditional", "Rule version outside its effective window; assess the applicable version."
            elif rule["kind"] == "review_task":
                status, reason = "Conditional", "Review task; this row does not prescribe a marking."
                if matched is False:
                    status, reason = "Not applicable", "Review trigger is false for supplied facts."
            elif unresolved_rule:
                status, reason = "Conditional", "Draft, stale or temporally unverified rule; not a definitive requirement or exclusion."
            elif matched is None:
                status, reason = "Conditional", "More product/applicability information is required."
            elif matched:
                status, reason = "Required", "Source-checked rule matches the supplied facts; not authorization to affix a mark."
            else:
                status, reason = "Not applicable", "This checked rule's applicability expression is false; other rules may still apply."
            locations = []
            for location in rule["locations"]:
                value, gaps, loc_trace = evaluate(location["when"], facts) if "when" in location else (True, [], None)
                locations.append({**deepcopy(location), "eligibility": "Unresolved" if value is None else "Condition met" if value else "Condition not met", "missing_fields": gaps, "trace": loc_trace})
            results.append({"market": market, "rule_id": rule["id"], "revision": rule["revision"], "marking": rule["title"], "kind": rule["kind"], "status": status, "reason": reason, "applicability": matched, "missing_fields": missing, "locations": locations, "sources": deepcopy(rule["sources"]), "notes": rule["notes"], "review": deepcopy(rule["review"]), "stale": stale, "trace": trace})
    return {"report_schema_version": "1.0", "engine_version": ENGINE_VERSION, "assessed_on": today.isoformat(), "created_at": datetime.now(timezone.utc).isoformat(), "pack_version": bundle["rules"]["pack_version"], "bundle_sha256": digest(bundle), "profile_sha256": digest(profile), "profile": deepcopy(profile), "coverage": {m: deepcopy(bundle["coverage"][m]) for m in profile["markets"]}, "rule_bundle_snapshot": deepcopy(bundle), "results": results, "limitation": "Partial starter coverage. Required means a rule matches, not that the product is approved. Draft candidates cannot clear a marking. Location alternatives require their stated conditions and source review."}


def flat_rows(report):
    return [{"Market": row["market"], "Marking": row["marking"], "Status": row["status"], "Type": row["kind"], "Location options": " | ".join(f"{l['place']} [{l['role']}; {l['eligibility']}]: {l['condition']}" for l in row["locations"]), "Reference": " | ".join(s["section"] for s in row["sources"]), "Source URL": " | ".join(s["url"] for s in row["sources"]), "Notes": row["notes"], "Reason": row["reason"], "Missing inputs": ", ".join(row["missing_fields"]), "Last reviewed": row["review"]["last_reviewed_on"] or "Not reviewed", "Review status": row["review"]["status"], "Rule ID": row["rule_id"], "Rule revision": row["revision"], "Pack version": report["pack_version"], "Assessed on": report["assessed_on"], "Coverage": report["coverage"][row["market"]]["status"], "Coverage gaps": "; ".join(report["coverage"][row["market"]]["gaps"]), "Bundle SHA256": report["bundle_sha256"]} for row in report["results"]]


def export_csv(report):
    rows = flat_rows(report)
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=list(rows[0]) if rows else ["Market", "Marking", "Status"])
    writer.writeheader()
    # Avoid spreadsheet formula interpretation in downloaded CSV values.
    for row in rows:
        writer.writerow({k: "'" + v if isinstance(v, str) and v.lstrip().startswith(("=", "+", "-", "@")) else v for k, v in row.items()})
    return "\ufeff" + out.getvalue()
