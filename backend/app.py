"""
app.py
------
FastAPI backend for the Pravesh KYC verification demo.

Endpoints:
  GET  /api/applications              -> queue listing with status filter
  GET  /api/applications/{app_id}      -> full applicant detail + evaluation
  POST /api/applications/{app_id}/decide  -> staff member records a final action
  GET  /api/health

Run with:
  uvicorn app:app --reload --port 8003
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import mock_data
from kyc_engine import evaluate_kyc_application

app = FastAPI(title="Pravesh — KYC Verification Demo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

APPLICATIONS = {a.app_id: a for a in mock_data.seed_applications(22)}


class DecideRequest(BaseModel):
    decision: str  # VERIFIED / REJECTED / RESUBMISSION_REQUESTED


def _summary(a: "mock_data.KYCApplication") -> dict:
    ev = evaluate_kyc_application(a)
    return {
        "app_id": a.app_id,
        "applicant_name": a.applicant_name,
        "occupation_type": a.occupation_type,
        "risk_category": ev["risk_category"],
        "score": ev["score"],
        "decision": ev["decision"],
        "status": a.status,
        "has_gate_failure": len(ev["gate_failures"]) > 0,
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/applications")
def list_applications(status: str = "PENDING"):
    apps = list(APPLICATIONS.values())
    if status and status.upper() != "ALL":
        apps = [a for a in apps if a.status == status.upper()]
    return {"items": [_summary(a) for a in apps]}


@app.get("/api/applications/{app_id}")
def get_application(app_id: str):
    a = APPLICATIONS.get(app_id)
    if not a:
        raise HTTPException(404, f"No application with id {app_id}")
    ev = evaluate_kyc_application(a)
    return {
        "applicant": {
            "app_id": a.app_id,
            "name": a.applicant_name,
            "age": a.age,
            "occupation_type": a.occupation_type,
            "annual_income": a.annual_income,
            "is_pep": a.is_pep,
            "cash_intensive_business": a.cash_intensive_business,
            "is_nri_or_foreign": a.is_nri_or_foreign,
            "pan": a.pan,
            "aadhaar": a.aadhaar,
            "id_linked_name": a.id_linked_name,
            "pincode": a.pincode,
            "stated_city": a.stated_city,
            "photo_match_score": a.photo_match_score,
            "status": a.status,
        },
        "evaluation": ev,
    }


@app.post("/api/applications/{app_id}/decide")
def decide(app_id: str, req: DecideRequest):
    a = APPLICATIONS.get(app_id)
    if not a:
        raise HTTPException(404, f"No application with id {app_id}")
    valid_decisions = ("VERIFIED", "REJECTED", "RESUBMISSION_REQUESTED")
    if req.decision.upper() not in valid_decisions:
        raise HTTPException(400, f"decision must be one of {valid_decisions}")
    a.status = req.decision.upper()
    return {"app_id": app_id, "status": a.status}
