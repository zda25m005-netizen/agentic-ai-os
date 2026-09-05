"""Eligibility engine — conservative, never overclaims.

Produces one of: eligible | likely | unclear | not_eligible, with human-readable
reasons. When the source doesn't establish a requirement, the status stays
'unclear' and the UI tells the user to verify on the official page.
"""

from __future__ import annotations

from app.scholarships.models import Scholarship, ScholarshipIntent

COMMONWEALTH = {
    "India",
    "Pakistan",
    "Bangladesh",
    "Sri Lanka",
    "Nigeria",
    "Kenya",
    "Ghana",
    "South Africa",
    "Malaysia",
    "Singapore",
    "Canada",
    "Australia",
    "New Zealand",
    "United Kingdom",
    "Uganda",
    "Tanzania",
    "Nepal",
}
DEVELOPING = {
    "India",
    "Pakistan",
    "Bangladesh",
    "Sri Lanka",
    "Nigeria",
    "Kenya",
    "Ghana",
    "Vietnam",
    "Indonesia",
    "Egypt",
    "Nepal",
    "Philippines",
    "Uganda",
    "Tanzania",
    "Ethiopia",
    "Brazil",
    "Colombia",
    "Peru",
}
EU = {
    "Germany",
    "France",
    "Netherlands",
    "Sweden",
    "Finland",
    "Italy",
    "Denmark",
    "Austria",
    "Belgium",
    "Ireland",
    "Spain",
    "Poland",
    "Portugal",
    "Greece",
}


def eligibility_status(sch: Scholarship, intent: ScholarshipIntent) -> tuple[str, list[str]]:
    nationality = intent.nationality
    tag = sch.nationality_eligibility
    reasons: list[str] = []
    status = "likely"

    if tag == "international":
        status = "eligible"
        reasons.append("Open to international students.")
    elif tag == "commonwealth":
        if nationality is None:
            status = "unclear"
            reasons.append("Commonwealth citizens only — confirm your country is eligible.")
        elif nationality in COMMONWEALTH:
            status = "eligible"
            reasons.append(f"{nationality} is a Commonwealth country — nationality criterion met.")
        else:
            status = "not_eligible"
            reasons.append(f"Restricted to Commonwealth citizens; {nationality} is not eligible.")
    elif tag == "developing":
        if nationality is None:
            status = "unclear"
            reasons.append("Limited to listed (mostly developing) countries — confirm eligibility.")
        elif nationality in DEVELOPING:
            status = "eligible"
            reasons.append(f"{nationality} is typically on the eligible-country list.")
        else:
            status = "not_eligible"
            reasons.append(
                f"Restricted to listed developing countries; {nationality} likely not eligible."
            )
    elif tag == "eu":
        if nationality is None:
            status = "unclear"
        elif nationality in EU:
            status = "eligible"
            reasons.append(f"{nationality} is an EU country.")
        else:
            status = "not_eligible"
    else:  # specific
        status = "unclear"
        reasons.append(
            sch.nationality_note
            or "Nationality/country eligibility varies — verify the country list."
        )

    # language caveat
    if (
        intent.no_ielts
        and sch.language_requirements
        and "ielts" in sch.language_requirements.lower()
    ):
        reasons.append("May require IELTS/TOEFL — verify whether a waiver applies.")
        if status == "eligible":
            status = "likely"

    if sch.work_experience_requirement:
        reasons.append(sch.work_experience_requirement)

    reasons.append(
        "Final eligibility depends on GPA, language scores and deadlines — "
        "verify on the official page."
    )
    return status, reasons
