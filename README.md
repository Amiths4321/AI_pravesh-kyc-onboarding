# Pravesh — KYC Verification Queue (Demo)

A working demo of a digital KYC verification and account-opening review
tool for bank staff — built as the natural extension of something DNS
Bank has already announced publicly.

> **This is a sales/portfolio demo, not production software.** All PAN
> numbers, Aadhaar numbers, names, and addresses are synthetically
> generated for demonstration only — no real identity documents are used,
> stored, or required. This is also **not** a compliance product; the
> risk-categorization logic is illustrative, modeled loosely on the kind
> of Low/Medium/High customer risk tiering RBI's KYC Master Direction
> describes, and would need sign-off from the bank's own compliance team
> before resembling anything used in production.

## Why this demo, why this bank

DNS Bank was recognised at the Cooperative Banks Top 100 Summit (Jan
2026) specifically for <em>an online KYC verification portal</em> and a
centralised account-opening system for CASA and loan products. **Pravesh
is built to look like the staff-facing side of exactly that system** —
the screen a back-office reviewer would actually work from when an
account-opening submission needs a second look.

Specific choices that matter for the pitch:

- **Real validation, not invented stand-ins.** Aadhaar numbers are
  checked with the actual Verhoeff checksum algorithm UIDAI uses for the
  12th digit — this was tested against 1,000 generated numbers (100%
  valid) and confirmed to catch every single-digit corruption (108/108
  in testing), which is the actual point of that algorithm. PAN format
  validation follows the real 5-letter/4-digit/1-letter structure,
  including the 4th-letter holder-type code.
- **Two-layer decisioning**, consistent with the rest of this portfolio:
  a malformed PAN or failed Aadhaar checksum is a hard gate — no score
  can override unusable documents. High-risk customers (PEP status,
  cash-intensive business, NRI/foreign, high income) always route to
  manual review regardless of score, the same way enhanced due diligence
  isn't something a good score should be able to skip.
- **Explainable scoring.** Name-match, address/pincode consistency, and
  photo-match confidence each contribute visible, reasoned points — not
  a single opaque "risk score."

## What it does

A staff member works through a queue of account-opening applications.
For each one:

| Layer | What's checked |
|---|---|
| Hard gates | PAN format + holder-type code; Aadhaar Verhoeff checksum |
| Risk categorization | PEP status, cash-intensive business, NRI/foreign status, declared income |
| Scorecard | Name match (application vs. ID-linked name), pincode/city consistency, photo match confidence |
| Decision | AUTO_VERIFY / MANUAL_REVIEW (incl. all HIGH-risk customers) / RESUBMIT_DOCUMENTS |
| Staff action | Verify & open account, request resubmission, or reject |

## Project structure

```
pravesh-kyc-onboarding/
├── backend/
│   ├── app.py               # FastAPI app: queue, detail, decide endpoints
│   ├── kyc_engine.py          # two-layer evaluation — combines everything below
│   ├── validation_engine.py   # Verhoeff (Aadhaar), PAN format, name match, risk rules
│   ├── mock_data.py           # synthetic applicant + document generator
│   └── requirements.txt
└── frontend/
    ├── index.html             # queue + detail layout
    ├── style.css
    └── app.js                 # queue, document cards, decision + stamp animation
```

## Running it locally

**1. Backend**
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8003
```

**2. Frontend** (separate terminal)
```bash
cd frontend
python3 -m http.server 8087
```

Then open **http://localhost:8087**. The dashboard talks to
`http://127.0.0.1:8003` by default — change the "API base" field in the
top bar if you run the backend elsewhere.

No database, no API keys, no external services required.

## Using it in a pitch

1. Open a **RESUBMIT_DOCUMENTS** application where the score is actually
   high — this is the clearest way to show that a failed Aadhaar
   checksum or malformed PAN overrides everything else, the same way a
   human reviewer's judgment would.
2. Open a **HIGH risk** application and point out it routes to manual
   review regardless of score — this is the enhanced-due-diligence point
   regulators care about.
3. Click **Verify & open account** on a clean application to show the
   stamp confirmation — a small but deliberate touch that mirrors the
   physical "stamped and approved" moment this digitizes.

## What this demo intentionally does not cover

Scoped for a sales conversation, not a finished product. It doesn't
include: actual UIDAI/NSDL API integration (this only validates
checksums/format locally — it cannot confirm a number is real or
currently active), document image upload/OCR, liveness detection for the
photo match, persistence across restarts, or audit logging of who
reviewed what and when. Those are the natural next-conversation talking
points — and the risk-categorization rules specifically would need the
bank's own compliance team to define before this resembled anything
production-ready.

## License

MIT — see `LICENSE`.
