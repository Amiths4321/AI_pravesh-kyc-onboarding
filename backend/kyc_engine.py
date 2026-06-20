"""
kyc_engine.py
-------------
Combines document validation, name/address consistency, and risk
categorization into a single decision for a KYC/account-opening
application — following the same two-layer pattern as the other demos
in this portfolio:

  1. HARD GATES — a malformed PAN or a failed Aadhaar checksum means the
     documents themselves are unusable. No amount of good name-matching
     or photo confidence can override that; the customer must resubmit.

  2. SOFT SCORECARD — for applications with valid documents, a weighted
     score (name match, address consistency, photo match) drives whether
     the application can be auto-verified or needs a human reviewer.
     High-risk customers (per the risk categorization) always route to
     manual review regardless of score — enhanced due diligence isn't
     something a good score should be able to skip.
"""

import mock_data
from validation_engine import (
    validate_aadhaar, validate_pan, name_match_score,
    check_pincode_consistency, derive_risk_category,
)

WEIGHTS = {
    "name_match_high": 40, "name_match_medium": 22, "name_match_low": 5,
    "pincode_consistent": 25, "pincode_unknown": 12,
    "photo_match_high": 35, "photo_match_medium": 18,
}

AUTO_VERIFY_THRESHOLD = 80
MANUAL_REVIEW_THRESHOLD = 50


def _name_match_points(score: int):
    if score >= 90:
        return WEIGHTS["name_match_high"], f"Name match {score}% — strong agreement across documents"
    if score >= 70:
        return WEIGHTS["name_match_medium"], f"Name match {score}% — minor variation, likely a formatting difference"
    return WEIGHTS["name_match_low"], f"Name match {score}% — significant mismatch between application and ID name"


def _pincode_points(result: dict):
    if result["consistent"] is True:
        return WEIGHTS["pincode_consistent"], result["reason"]
    if result["consistent"] is None:
        return WEIGHTS["pincode_unknown"], result["reason"]
    return 0, result["reason"]


def _photo_points(score: int):
    if score >= 85:
        return WEIGHTS["photo_match_high"], f"Photo match {score}% against Aadhaar record — high confidence"
    if score >= 70:
        return WEIGHTS["photo_match_medium"], f"Photo match {score}% — acceptable but worth a second look"
    return 0, f"Photo match {score}% — low confidence, recommend in-branch verification"


def evaluate_kyc_application(app: "mock_data.KYCApplication") -> dict:
    pan_result = validate_pan(app.pan)
    aadhaar_result = validate_aadhaar(app.aadhaar)
    pincode_result = check_pincode_consistency(app.pincode, app.stated_city)
    risk_result = derive_risk_category(
        app.occupation_type, app.is_pep, app.cash_intensive_business,
        app.is_nri_or_foreign, app.annual_income,
    )

    gate_failures = []
    if not pan_result["valid"]:
        gate_failures.append(f"PAN invalid: {pan_result['reason']}")
    if not aadhaar_result["valid"]:
        gate_failures.append(f"Aadhaar invalid: {aadhaar_result['reason']}")

    name_score = name_match_score(app.applicant_name, app.id_linked_name)

    reasons = []
    score = 0

    pts, why = _name_match_points(name_score)
    score += pts; reasons.append({"label": why, "points": pts})

    pts, why = _pincode_points(pincode_result)
    score += pts; reasons.append({"label": why, "points": pts})

    pts, why = _photo_points(app.photo_match_score)
    score += pts; reasons.append({"label": why, "points": pts})

    score = min(100, score)

    if gate_failures:
        decision = "RESUBMIT_DOCUMENTS"
    elif risk_result["category"] == "HIGH":
        decision = "MANUAL_REVIEW"
    elif score >= AUTO_VERIFY_THRESHOLD:
        decision = "AUTO_VERIFY"
    elif score >= MANUAL_REVIEW_THRESHOLD:
        decision = "MANUAL_REVIEW"
    else:
        decision = "RESUBMIT_DOCUMENTS"

    return {
        "app_id": app.app_id,
        "score": score,
        "decision": decision,
        "gate_failures": gate_failures,
        "reasons": sorted(reasons, key=lambda r: -r["points"]),
        "pan_result": pan_result,
        "aadhaar_result": aadhaar_result,
        "name_match_score": name_score,
        "pincode_result": pincode_result,
        "risk_category": risk_result["category"],
        "risk_reasons": risk_result["reasons"],
    }
