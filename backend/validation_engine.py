"""
validation_engine.py
---------------------
Document and identity validation logic for KYC verification.

Aadhaar numbers use the Verhoeff checksum algorithm for their final check
digit — this is the actual algorithm UIDAI uses (publicly documented), not
an invented stand-in, which matters for credibility in a banking pitch.
PAN format follows the real structure (5 letters, 4 digits, 1 letter,
where the 4th letter encodes holder type).

Risk categorization is modeled loosely on the kind of customer risk
tiering (Low/Medium/High) that RBI's KYC Master Direction expects banks
to apply — illustrative only, not a compliance product. A real deployment
would need sign-off from the bank's own compliance team on the actual
rules used.
"""

import difflib

# ---------------------------------------------------------------------
# Verhoeff algorithm — the standard checksum tables (dihedral group D5).
# Used by UIDAI for the 12th (final) digit of every Aadhaar number.
# ---------------------------------------------------------------------

_D_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0],
]

_P_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8],
]

_INV_TABLE = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def verhoeff_checksum_digit(number_without_check_digit: str) -> int:
    """Given an 11-digit string, returns the check digit that makes the
    full 12-digit Aadhaar number valid."""
    c = 0
    digits = [int(ch) for ch in reversed(number_without_check_digit)]
    for i, digit in enumerate(digits):
        c = _D_TABLE[c][_P_TABLE[(i + 1) % 8][digit]]
    return _INV_TABLE[c]


def verhoeff_validate(full_number: str) -> bool:
    """Validates a complete number (including its check digit) — returns
    True if the Verhoeff checksum comes out to 0, the validity condition."""
    if not full_number.isdigit():
        return False
    c = 0
    digits = [int(ch) for ch in reversed(full_number)]
    for i, digit in enumerate(digits):
        c = _D_TABLE[c][_P_TABLE[i % 8][digit]]
    return c == 0


def validate_aadhaar(aadhaar: str) -> dict:
    aadhaar = aadhaar.replace(" ", "")
    if len(aadhaar) != 12 or not aadhaar.isdigit():
        return {"valid": False, "reason": "Aadhaar number must be exactly 12 digits"}
    if not verhoeff_validate(aadhaar):
        return {"valid": False, "reason": "Aadhaar checksum (Verhoeff) failed — likely a mistyped digit"}
    return {"valid": True, "reason": "Aadhaar checksum verified"}


# ---------------------------------------------------------------------
# PAN — 5 letters, 4 digits, 1 letter. The 4th letter encodes holder type.
# ---------------------------------------------------------------------

_PAN_HOLDER_TYPES = {
    "P": "Individual", "C": "Company", "H": "Hindu Undivided Family",
    "A": "Association of Persons", "B": "Body of Individuals",
    "G": "Government", "J": "Artificial Juridical Person",
    "L": "Local Authority", "F": "Firm", "T": "Trust",
}


def validate_pan(pan: str) -> dict:
    pan = pan.strip().upper()
    if len(pan) != 10 or not (pan[:5].isalpha() and pan[5:9].isdigit() and pan[9].isalpha()):
        return {"valid": False, "reason": "PAN must be 5 letters, 4 digits, 1 letter (e.g. ABCDE1234F)", "holder_type": None}
    holder_code = pan[3]
    holder_type = _PAN_HOLDER_TYPES.get(holder_code)
    if not holder_type:
        return {"valid": False, "reason": f"4th character '{holder_code}' is not a recognized PAN holder-type code", "holder_type": None}
    return {"valid": True, "reason": "PAN format and holder-type code valid", "holder_type": holder_type}


# ---------------------------------------------------------------------
# Name matching — fuzzy comparison between the name on the application
# and the name on file with each ID document.
# ---------------------------------------------------------------------

def name_match_score(name_a: str, name_b: str) -> int:
    """Returns a 0-100 similarity score. difflib's SequenceMatcher ratio
    is good enough for catching typos/spelling variants without needing
    an external fuzzy-matching library."""
    a = name_a.strip().lower()
    b = name_b.strip().lower()
    if not a or not b:
        return 0
    ratio = difflib.SequenceMatcher(None, a, b).ratio()
    return round(ratio * 100)


# ---------------------------------------------------------------------
# Pincode -> city/state consistency check (small illustrative lookup)
# ---------------------------------------------------------------------

PINCODE_LOOKUP = {
    "421201": ("Dombivli", "Maharashtra"),
    "400601": ("Thane", "Maharashtra"),
    "421301": ("Kalyan", "Maharashtra"),
    "456001": ("Ujjain", "Madhya Pradesh"),
    "400001": ("Mumbai", "Maharashtra"),
    "411001": ("Pune", "Maharashtra"),
    "422001": ("Nashik", "Maharashtra"),
}


def check_pincode_consistency(pincode: str, stated_city: str) -> dict:
    entry = PINCODE_LOOKUP.get(pincode)
    if not entry:
        return {"consistent": None, "reason": f"Pincode {pincode} not in lookup — cannot verify automatically"}
    city, state = entry
    consistent = city.lower() == stated_city.strip().lower()
    if consistent:
        return {"consistent": True, "reason": f"Pincode {pincode} matches stated city {stated_city}"}
    return {"consistent": False, "reason": f"Pincode {pincode} maps to {city}, {state} — does not match stated city '{stated_city}'"}


# ---------------------------------------------------------------------
# Risk categorization — illustrative, modeled loosely on RBI-style
# Low/Medium/High customer risk tiering. NOT a compliance product.
# ---------------------------------------------------------------------

def derive_risk_category(occupation_type: str, is_pep: bool, cash_intensive_business: bool,
                          is_nri_or_foreign: bool, annual_income: float) -> dict:
    reasons = []

    if is_pep:
        return {"category": "HIGH", "reasons": ["Politically Exposed Person — mandates enhanced due diligence"]}

    if is_nri_or_foreign:
        reasons.append("Non-resident / foreign national status")

    if cash_intensive_business:
        reasons.append("Cash-intensive business activity")

    if annual_income > 2_000_000:
        reasons.append(f"High declared annual income (₹{annual_income:,.0f})")

    high_risk_flags = sum([is_nri_or_foreign, cash_intensive_business, annual_income > 2_000_000])

    if high_risk_flags >= 2:
        return {"category": "HIGH", "reasons": reasons}
    if high_risk_flags == 1:
        return {"category": "MEDIUM", "reasons": reasons}

    if occupation_type in ("Salaried", "Government Employee", "Homemaker", "Student", "Retired"):
        return {"category": "LOW", "reasons": [f"{occupation_type} with no elevated risk indicators"]}

    return {"category": "MEDIUM", "reasons": [f"{occupation_type} — moderate risk by default occupation category"]}
