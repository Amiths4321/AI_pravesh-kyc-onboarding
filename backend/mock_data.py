"""
mock_data.py
------------
Synthetic KYC/account-opening applications sitting in a staff review
queue. All PAN, Aadhaar, names, and addresses are randomly generated for
demo purposes — no real identity documents or numbers are used.
"""

import random
import string
import uuid
from dataclasses import dataclass

from validation_engine import verhoeff_checksum_digit, PINCODE_LOOKUP

FIRST_NAMES = ["Rohan", "Priya", "Sanjay", "Anita", "Vikram", "Sunita", "Aniket",
               "Kavita", "Suresh", "Meera", "Rajesh", "Pooja", "Nitin", "Sneha",
               "Amol", "Deepa"]
LAST_NAMES = ["Patil", "Joshi", "Deshmukh", "Kulkarni", "Shah", "Naik", "Pawar",
              "Bhosale", "Gokhale", "Rane"]

OCCUPATIONS = ["Salaried", "Government Employee", "Self-Employed Professional",
               "Business Owner", "Homemaker", "Student", "Retired"]

PAN_HOLDER_LETTER = "P"  # generate mostly Individual-type PAN for retail account opening


@dataclass
class KYCApplication:
    app_id: str
    applicant_name: str
    age: int
    occupation_type: str
    annual_income: float
    is_pep: bool
    cash_intensive_business: bool
    is_nri_or_foreign: bool
    pan: str
    aadhaar: str
    id_linked_name: str       # name as it appears on the PAN/Aadhaar records
    pincode: str
    stated_city: str
    photo_match_score: int     # simulated face-match against Aadhaar photo, 0-100
    status: str = "PENDING"


def _random_valid_pan():
    letters5 = "".join(random.choices(string.ascii_uppercase, k=3)) + PAN_HOLDER_LETTER + \
               random.choice(string.ascii_uppercase)
    digits4 = "".join(random.choices(string.digits, k=4))
    last_letter = random.choice(string.ascii_uppercase)
    return letters5 + digits4 + last_letter


def _random_invalid_pan():
    # Same length/shape but with an unrecognized 4th-letter holder code,
    # or wrong overall shape — either is a realistic data-entry mistake.
    if random.random() < 0.5:
        bad = list(_random_valid_pan())
        bad[3] = random.choice("IOUXYZ")  # not a recognized holder-type code
        return "".join(bad)
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=10))


def _random_valid_aadhaar():
    base = "".join(str(random.randint(0, 9)) for _ in range(11))
    check_digit = verhoeff_checksum_digit(base)
    return base + str(check_digit)


def _random_invalid_aadhaar():
    valid = _random_valid_aadhaar()
    pos = random.randint(0, 11)
    wrong_digit = str((int(valid[pos]) + random.randint(1, 9)) % 10)
    return valid[:pos] + wrong_digit + valid[pos + 1:]


def _vary_name_spelling(name: str) -> str:
    """Produces a plausible spelling/format variant, the kind a genuine
    data-entry mismatch between two ID documents might look like. Each
    branch guarantees an actual character-level difference — an earlier
    version relied on .replace() substrings that were a no-op for most
    surnames, and a case-only variant that the (case-insensitive) match
    scorer would have treated as identical anyway, making real mismatches
    far rarer in practice than intended."""
    parts = name.split()
    first, last = parts[0], parts[-1]
    choice = random.choice(["initial", "typo", "reordered"])

    if choice == "initial":
        return f"{first[0]}. {last}"  # "R. Shah" instead of "Rohan Shah"

    if choice == "typo" and len(last) > 3:
        i = random.randint(0, len(last) - 2)
        chars = list(last)
        chars[i], chars[i + 1] = chars[i + 1], chars[i]  # adjacent-letter swap, a classic typo
        return f"{first} {''.join(chars)}"

    return f"{last} {first}"  # surname-first, a real formatting mismatch between documents


def generate_application() -> KYCApplication:
    name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
    age = random.randint(18, 70)
    occupation = random.choice(OCCUPATIONS)
    income = round(random.uniform(150000, 3500000), -3)

    is_pep = random.random() < 0.04
    cash_intensive = occupation == "Business Owner" and random.random() < 0.5
    is_nri = random.random() < 0.08

    pan = _random_valid_pan() if random.random() < 0.85 else _random_invalid_pan()
    aadhaar = _random_valid_aadhaar() if random.random() < 0.85 else _random_invalid_aadhaar()

    # Most applicants' ID-linked name matches well; a minority show a
    # spelling mismatch, which is exactly the kind of thing this tool
    # exists to catch.
    id_linked_name = _vary_name_spelling(name) if random.random() < 0.25 else name

    pincode = random.choice(list(PINCODE_LOOKUP.keys()))
    correct_city = PINCODE_LOOKUP[pincode][0]
    stated_city = correct_city if random.random() < 0.85 else random.choice(
        [c for c, _ in PINCODE_LOOKUP.values() if c != correct_city]
    )

    photo_match_score = random.randint(88, 99) if random.random() < 0.85 else random.randint(35, 70)

    return KYCApplication(
        app_id="KYC-" + str(uuid.uuid4())[:8].upper(),
        applicant_name=name,
        age=age,
        occupation_type=occupation,
        annual_income=income,
        is_pep=is_pep,
        cash_intensive_business=cash_intensive,
        is_nri_or_foreign=is_nri,
        pan=pan,
        aadhaar=aadhaar,
        id_linked_name=id_linked_name,
        pincode=pincode,
        stated_city=stated_city,
        photo_match_score=photo_match_score,
    )


def seed_applications(n: int = 22):
    return [generate_application() for _ in range(n)]
