"""Profile-driven eligibility engine — deterministic, never fabricates.

evaluate(scholarship, student_profile) checks each structured requirement against
the user's actual profile and returns per-check PASS / FAIL / UNKNOWN /
NOT_APPLICABLE plus an overall status. Missing user data never becomes a PASS.
"""

from __future__ import annotations

from app.scholarships.models import EligibilityCheck, Scholarship, StudentProfile

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
_DEGREE_ORDER = {"diploma": 0, "bachelor": 1, "master": 2, "phd": 3, "postdoc": 4}


def _nationality_check(sch: Scholarship, p: StudentProfile) -> EligibilityCheck:
    tag = sch.nationality_eligibility
    nat = p.nationality
    req = {
        "international": "International students",
        "commonwealth": "Commonwealth citizens",
        "developing": "Listed (mostly developing) countries",
        "eu": "EU citizens",
        "specific": sch.nationality_note or "Specific eligible countries",
    }.get(tag, "See official page")
    if tag == "international":
        return EligibilityCheck(
            requirement="Nationality",
            required_value=req,
            user_value=nat or None,
            status="PASS",
            explanation="Open to international students.",
        )
    if nat is None:
        return EligibilityCheck(
            requirement="Nationality",
            required_value=req,
            user_value=None,
            status="UNKNOWN",
            explanation="Add your nationality to determine eligibility.",
        )
    table = {"commonwealth": COMMONWEALTH, "developing": DEVELOPING, "eu": EU}
    if tag in table:
        ok = nat in table[tag]
        return EligibilityCheck(
            requirement="Nationality",
            required_value=req,
            user_value=nat,
            status="PASS" if ok else "FAIL",
            explanation=f"{nat} {'is' if ok else 'is not'} in the eligible group.",
        )
    return EligibilityCheck(
        requirement="Nationality",
        required_value=req,
        user_value=nat,
        status="UNKNOWN",
        explanation="Verify the eligible-country list on the official page.",
    )


def _degree_check(sch: Scholarship, p: StudentProfile) -> EligibilityCheck:
    req = ", ".join(sch.degree_levels) or "Any"
    if not sch.degree_levels:
        return EligibilityCheck(
            requirement="Degree level", required_value="Any", status="NOT_APPLICABLE"
        )
    if p.degree is None:
        return EligibilityCheck(
            requirement="Degree level",
            required_value=req,
            status="UNKNOWN",
            explanation="Add your current/target degree to your profile.",
        )
    # A scholarship for degree X is applied for while holding the prior degree; accept if
    # the user's degree is at or below the highest offered level.
    ok = any(
        _DEGREE_ORDER.get(p.degree, 0) <= _DEGREE_ORDER.get(d, 9) + 1 for d in sch.degree_levels
    )
    ok = p.degree in sch.degree_levels or ok
    return EligibilityCheck(
        requirement="Degree level",
        required_value=req,
        user_value=p.degree,
        status="PASS" if ok else "FAIL",
    )


def _field_check(sch: Scholarship, p: StudentProfile) -> EligibilityCheck:
    if "all" in sch.fields or not sch.fields:
        return EligibilityCheck(
            requirement="Study field",
            required_value="Any field",
            status="PASS",
            explanation="Open to all study fields.",
        )
    req = ", ".join(sch.fields)
    if not p.field_tags:
        return EligibilityCheck(
            requirement="Study field",
            required_value=req,
            user_value=p.field,
            status="UNKNOWN",
            explanation="Add your field of study to your profile.",
        )
    ok = bool(set(p.field_tags) & set(sch.fields))
    return EligibilityCheck(
        requirement="Study field",
        required_value=req,
        user_value=p.field,
        status="PASS" if ok else "FAIL",
    )


def _gpa_check(sch: Scholarship, p: StudentProfile) -> EligibilityCheck:
    if sch.min_gpa is None:
        return EligibilityCheck(
            requirement="Minimum GPA", required_value=None, status="NOT_APPLICABLE"
        )
    req = f"{sch.min_gpa}/{sch.gpa_scale or '?'}"
    if p.gpa is None:
        return EligibilityCheck(
            requirement="Minimum GPA",
            required_value=req,
            user_value=None,
            status="UNKNOWN",
            explanation="Your GPA is not in your profile.",
        )
    # normalize to a common scale when both scales are known
    uval = p.gpa
    if p.gpa_scale and sch.gpa_scale and p.gpa_scale != sch.gpa_scale:
        uval = p.gpa / p.gpa_scale * sch.gpa_scale
    ok = uval >= sch.min_gpa
    return EligibilityCheck(
        requirement="Minimum GPA",
        required_value=req,
        user_value=f"{p.gpa}/{p.gpa_scale or '?'}",
        status="PASS" if ok else "FAIL",
    )


def _ielts_check(sch: Scholarship, p: StudentProfile) -> EligibilityCheck:
    if sch.min_ielts is None:
        return EligibilityCheck(requirement="IELTS", required_value=None, status="NOT_APPLICABLE")
    if p.ielts is None:
        return EligibilityCheck(
            requirement="IELTS",
            required_value=str(sch.min_ielts),
            user_value=None,
            status="UNKNOWN",
            explanation="No IELTS score in your profile.",
        )
    ok = p.ielts >= sch.min_ielts
    return EligibilityCheck(
        requirement="IELTS",
        required_value=str(sch.min_ielts),
        user_value=str(p.ielts),
        status="PASS" if ok else "FAIL",
    )


def _experience_check(sch: Scholarship, p: StudentProfile) -> EligibilityCheck:
    if sch.min_work_experience_years is None:
        return EligibilityCheck(
            requirement="Work experience", required_value=None, status="NOT_APPLICABLE"
        )
    req = f"{sch.min_work_experience_years}+ years"
    if p.experience_years is None:
        return EligibilityCheck(
            requirement="Work experience",
            required_value=req,
            user_value=None,
            status="UNKNOWN",
            explanation="Work experience not in your profile.",
        )
    ok = p.experience_years >= sch.min_work_experience_years
    return EligibilityCheck(
        requirement="Work experience",
        required_value=req,
        user_value=f"{p.experience_years:g} years",
        status="PASS" if ok else "FAIL",
    )


_HARD = {"Nationality", "Degree level", "Study field"}


def evaluate(sch: Scholarship, profile: StudentProfile) -> tuple[str, list[EligibilityCheck]]:
    checks = [
        _nationality_check(sch, profile),
        _degree_check(sch, profile),
        _field_check(sch, profile),
        _gpa_check(sch, profile),
        _ielts_check(sch, profile),
        _experience_check(sch, profile),
    ]
    statuses = {c.requirement: c.status for c in checks}
    applicable = [c for c in checks if c.status != "NOT_APPLICABLE"]

    if any(c.status == "FAIL" for c in applicable):
        return "not_eligible", checks
    hard_unknown = any(statuses.get(r) == "UNKNOWN" for r in _HARD)
    any_unknown = any(c.status == "UNKNOWN" for c in applicable)

    if profile.is_empty() and any_unknown:
        return "insufficient", checks
    if not any_unknown:
        return "eligible", checks
    if hard_unknown:
        return "unclear", checks
    return "likely", checks  # hard reqs pass, only soft (GPA/IELTS/exp) unknown


def profile_from_intent(intent) -> StudentProfile:
    """Explicit facts stated in the query ARE user facts (nationality/degree/field)."""
    return StudentProfile(
        nationality=intent.nationality,
        degree=intent.degree,
        field=intent.field,
        field_tags=list(intent.field_tags),
    )


def eligibility_status(sch: Scholarship, intent) -> tuple[str, list[str]]:
    """Backward-compatible wrapper: evaluate against query-derived facts only."""
    status, checks = evaluate(sch, profile_from_intent(intent))
    reasons = [
        c.explanation or f"{c.requirement}: {c.status.title()}"
        for c in checks
        if c.status != "NOT_APPLICABLE"
    ]
    return status, reasons
