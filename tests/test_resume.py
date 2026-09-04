"""Resume parsing, candidate matching, storage, and constraint safety (offline)."""

from app.api.jobs import JobItem, parse_query, personalize_with_resume, validate_and_rank
from app.resume import store
from app.resume.match import score_candidate, suggested_roles
from app.resume.parser import (
    ResumeParseError,
    normalize_profile,
    parse_profile,
    profile_is_sparse,
)


# --- profile normalization (no fabrication) --------------------------------
def test_normalize_fills_missing_with_empty():
    p = normalize_profile({"skills": ["Python", "python", "SQL"]})
    assert p["skills"] == ["Python", "SQL"]  # de-duped, order kept
    assert p["job_titles"] == [] and p["experience_years"] is None
    assert p["summary"] == "" and p["education"] == []


def test_experience_years_coercion():
    assert normalize_profile({"experience_years": 2})["experience_years"] == 2.0
    assert normalize_profile({"experience_years": "about 3 years"})["experience_years"] == 3.0
    assert normalize_profile({"experience_years": 999})["experience_years"] is None


def test_profile_is_sparse():
    assert profile_is_sparse(normalize_profile({})) is True
    assert profile_is_sparse(normalize_profile({"skills": ["Python"]})) is False


# --- LLM parse with a fake chat fn -----------------------------------------
async def test_parse_profile_from_fake_llm():
    async def fake(_text):
        return '{"skills":["Python","SQL"],"job_titles":["Data Analyst"],"experience_years":2}'

    p = await parse_profile("x" * 50, fake)
    assert p["skills"] == ["Python", "SQL"] and p["experience_years"] == 2.0


async def test_parse_profile_bad_json_raises():
    async def bad(_text):
        return "sorry I cannot"

    try:
        await parse_profile("x" * 50, bad)
        raise AssertionError("expected ResumeParseError")
    except ResumeParseError:
        pass


async def test_parse_profile_llm_error_raises():
    async def boom(_text):
        raise RuntimeError("no key")

    try:
        await parse_profile("x" * 50, boom)
        raise AssertionError("expected ResumeParseError")
    except ResumeParseError:
        pass


async def test_parse_profile_too_short():
    async def fake(_text):
        return "{}"

    try:
        await parse_profile("hi", fake)
        raise AssertionError("expected ResumeParseError")
    except ResumeParseError:
        pass


# --- candidate matching -----------------------------------------------------
def test_score_matched_and_missing():
    prof = normalize_profile({"skills": ["Python", "PyTorch"], "experience_years": 1})
    m = score_candidate(prof, job_skills=["Python", "PyTorch", "AWS"], job_title="ML Engineer")
    assert m["matched_skills"] == ["Python", "PyTorch"]
    assert m["missing_skills"] == ["AWS"]
    assert "Matches Python" in m["reason"]


def test_score_experience_underqualified_lower():
    prof = normalize_profile({"skills": [], "experience_years": 1})
    under = score_candidate(prof, job_skills=[], job_title="X", job_exp_min=5)
    ok = score_candidate(prof, job_skills=[], job_title="X", job_exp_min=0, job_exp_max=2)
    assert under["breakdown"]["experience"] < ok["breakdown"]["experience"]


def test_reason_never_generic_hype():
    prof = normalize_profile({"skills": [], "job_titles": []})
    m = score_candidate(prof, job_skills=["Go"], job_title="Backend Engineer")
    assert "perfect" not in m["reason"].lower()
    assert "not directly listed" in m["reason"].lower()


def test_suggested_roles_domain_agnostic():
    prof = normalize_profile({"job_titles": ["HR Coordinator", "Recruiter"]})
    assert suggested_roles(prof) == ["HR Coordinator", "Recruiter"]
    assert suggested_roles(normalize_profile({})) == []  # no fabrication


# --- storage CRUD -----------------------------------------------------------
def test_store_roundtrip(tmp_path):
    store.DB_PATH = tmp_path / "r.db"
    assert store.load_profile() is None
    store.save_profile({"skills": ["Python"]}, "cv.pdf")
    rec = store.load_profile()
    assert rec["filename"] == "cv.pdf" and rec["profile"]["skills"] == ["Python"]
    store.save_profile({"skills": ["SQL"]}, "cv2.pdf")  # replace
    assert store.load_profile()["profile"]["skills"] == ["SQL"]
    assert store.delete_profile() is True and store.load_profile() is None


# --- resume must NOT override hard constraints ------------------------------
def _J(title, **kw):
    return JobItem(
        id=title + str(kw), title=title, company="Acme", source="Adzuna", application_url="u", **kw
    )


def test_resume_cannot_resurrect_excluded_jobs(tmp_path):
    store.DB_PATH = tmp_path / "r2.db"
    # A senior candidate; query strictly asks 0–2 years in India.
    store.save_profile({"skills": ["Python"], "experience_years": 8}, "cv.pdf")
    c = parse_query("ML Engineer India 0-2 years")
    jobs = [
        _J("ML Engineer", country="India", experience_min=0, experience_max=2, skills=["Python"]),
        _J("ML Engineer", country="India", experience_min=7, experience_max=12, seniority="senior"),
    ]
    valid = validate_and_rank(jobs, c, 50)
    assert len(valid) == 1  # 7–12 excluded despite the senior resume
    personalized = personalize_with_resume(valid)
    assert len(personalized) == 1 and personalized[0].experience_min == 0
    assert personalized[0].candidate_score is not None  # personalization attached
