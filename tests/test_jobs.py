"""Job search: strict, domain-agnostic query parsing + hard-filter validation.

Every retrieved job is validated against the parsed constraints BEFORE ranking,
so wrong-country / wrong-domain / wrong-type jobs are removed (never shown at a
lower match score). These tests exercise the pure functions offline (no network).
"""

from app.api.jobs import (
    JobItem,
    dedup,
    employment_matches,
    extract_skills,
    job_matches,
    normalize_location,
    parse_query,
    role_matches,
    strip_html,
    validate_and_rank,
)


def J(
    title,
    *,
    company="Acme",
    country=None,
    city=None,
    emp=None,
    wt=None,
    remote_ww=False,
    url="https://x/1",
    source="Adzuna",
):
    return JobItem(
        id=title + (country or ""),
        title=title,
        company=company,
        country=country,
        city=city,
        employment_type=emp,
        workplace_type=wt,
        remote_worldwide=remote_ww,
        source=source,
        application_url=url,
        sources=[source],
    )


# --- parsing ---------------------------------------------------------------
def test_parse_role_and_country_and_type():
    c = parse_query("ML Engineer Internship India")
    assert c.country == "India" and c.location_scope == "STRICT_COUNTRY"
    assert c.employment_type == "Internship"
    assert "ml" in c.role_terms and "machine learning" in c.role_terms


def test_parse_is_domain_agnostic_hr():
    c = parse_query("HR jobs India")
    assert c.country == "India"
    # HR expands within its own domain, and never into software/AI terms.
    assert "human resources" in c.role_terms
    assert "software" not in c.role_terms and "machine learning" not in c.role_terms


def test_parse_city_scope():
    c = parse_query("Marketing internships in Mumbai")
    assert c.city == "Mumbai" and c.country == "India"
    assert c.location_scope == "STRICT_CITY" and c.employment_type == "Internship"
    assert "marketing" in c.role_terms


def test_parse_worldwide_clears_country():
    c = parse_query("AI Engineer jobs worldwide")
    assert c.location_scope == "WORLDWIDE" and c.country is None


def test_parse_anywhere_is_worldwide():
    assert parse_query("AI Engineer anywhere").location_scope == "WORLDWIDE"


def test_parse_no_location_is_any():
    c = parse_query("Data Scientist jobs")
    assert c.location_scope == "ANY" and c.country is None


def test_parse_remote_and_experience():
    c = parse_query("ML Engineer remote India with 0-2 years experience")
    assert c.remote is True and c.country == "India"
    assert c.experience == "0–2 years"


def test_parse_does_not_inject_ai_for_generic_domains():
    c = parse_query("Mechanical Engineer jobs India")
    assert "mechanical" in c.role_terms
    assert "software" not in c.role_terms and "ml" not in c.role_terms


# --- location normalization ------------------------------------------------
def test_normalize_location_variants():
    assert normalize_location("Bengaluru, India")[0] == "India"
    assert normalize_location("Dubai")[0] == "United Arab Emirates"
    assert normalize_location("Remote - Worldwide")[3] is True  # remote_worldwide
    assert normalize_location("Remote - India")[0] == "India"
    assert normalize_location("San Francisco, CA")[0] == "United States"
    assert normalize_location(None)[0] is None


# --- role matching (strict domain, flexible terminology) -------------------
def test_role_matches_flexible_within_domain():
    c = parse_query("ML Engineer India")
    assert role_matches("Machine Learning Engineer", c) is True
    assert role_matches("ML Engineer, Research", c) is True
    assert role_matches("Software Engineer", c) is False  # generic 'engineer' alone never qualifies


def test_role_matches_hr_excludes_software():
    c = parse_query("HR jobs India")
    assert role_matches("Human Resources Specialist", c) is True
    assert role_matches("Talent Acquisition Partner", c) is True
    assert role_matches("Software Engineer", c) is False


def test_mechanical_excludes_software():
    c = parse_query("Mechanical Engineer jobs India")
    assert role_matches("Mechanical Design Engineer", c) is True
    assert role_matches("Software Engineer", c) is False


# --- employment matching ---------------------------------------------------
def test_internship_required_excludes_fulltime():
    c = parse_query("ML Engineer Internship India")
    assert employment_matches(J("ML Engineer Intern"), c) is True
    assert employment_matches(J("ML Engineer"), c) is False


def test_fulltime_excludes_internship():
    c = parse_query("Data Scientist full-time Germany")
    assert employment_matches(J("Data Science Intern"), c) is False
    assert employment_matches(J("Data Scientist"), c) is True


# --- the 14 scenario acceptance tests --------------------------------------
def test_1_ml_internship_india():
    c = parse_query("ML Engineer internship India")
    jobs = [
        J("ML Engineer Intern", country="India"),
        J("ML Engineer Intern", country="United States"),  # wrong country
        J("ML Engineer", country="India"),  # wrong type
        J("HR Intern", country="India"),  # wrong role
    ]
    out = validate_and_rank(jobs, c, 50)
    assert len(out) == 1 and out[0].country == "India" and "Intern" in out[0].title


def test_2_data_scientist_germany():
    c = parse_query("Data Scientist Germany")
    jobs = [
        J("Data Scientist", country="Germany"),
        J("Data Scientist", country="India"),
        J("Sales Manager", country="Germany"),
    ]
    out = validate_and_rank(jobs, c, 50)
    assert [j.country for j in out] == ["Germany"] and out[0].title == "Data Scientist"


def test_3_ml_switzerland_only():
    c = parse_query("ML Engineer Switzerland")
    jobs = [J("ML Engineer", country="Switzerland"), J("ML Engineer", country="Germany")]
    out = validate_and_rank(jobs, c, 50)
    assert len(out) == 1 and out[0].country == "Switzerland"


def test_4_ml_remote_india():
    c = parse_query("ML Engineer remote India")
    jobs = [
        J("ML Engineer", country="India", wt="Remote"),
        J("ML Engineer", country="United States", wt="Remote"),  # remote but US
        J("ML Engineer", country="India", wt="Onsite"),  # india but not remote
    ]
    out = validate_and_rank(jobs, c, 50)
    assert len(out) == 1 and out[0].country == "India" and out[0].workplace_type == "Remote"


def test_5_ml_worldwide_allows_many_countries():
    c = parse_query("ML Engineer worldwide")
    jobs = [
        J("ML Engineer", country="India"),
        J("ML Engineer", country="Germany"),
        J("ML Engineer", country="United States"),
    ]
    out = validate_and_rank(jobs, c, 50)
    assert len(out) == 3


def test_6_ai_engineer_anywhere():
    c = parse_query("AI Engineer anywhere")
    jobs = [J("AI Engineer", country="Japan"), J("AI Engineer", country="Brazil")]
    assert len(validate_and_rank(jobs, c, 50)) == 2


def test_7_india_query_excludes_us_remote():
    c = parse_query("ML Engineer India")
    assert job_matches(J("ML Engineer", country="United States", wt="Remote"), c) is False


def test_8_india_query_excludes_us_job_mentioning_india():
    # Description mentions India but the LOCATION is US -> country parsed as US -> excluded.
    c = parse_query("ML Engineer India")
    job = J("ML Engineer", country="United States")
    job.description = "Work with our India team; candidates from India may apply."
    assert job_matches(job, c) is False


def test_9_india_query_excludes_worldwide_remote():
    c = parse_query("ML Engineer India")
    assert job_matches(J("ML Engineer", country=None, wt="Remote", remote_ww=True), c) is False


def test_10_no_location_keeps_all_countries():
    c = parse_query("Data Scientist")
    jobs = [J("Data Scientist", country="India"), J("Data Scientist", country="United States")]
    assert len(validate_and_rank(jobs, c, 50)) == 2


def test_count_reflects_survivors_only():
    c = parse_query("HR jobs India")
    jobs = [J("HR Specialist", country="India")] + [
        J("Software Engineer", country="India") for _ in range(190)
    ]
    out = validate_and_rank(jobs, c, 200)
    assert len(out) == 1  # 191 fetched, 1 valid


def test_wrong_country_excluded_not_scored():
    c = parse_query("ML Engineer Internship India")
    us = J("ML Engineer Intern", country="United States")
    assert job_matches(us, c) is False  # excluded, never given a 42% score


# --- misc ------------------------------------------------------------------
def test_strip_html():
    assert strip_html("<p>Hello&nbsp;World</p>") == "Hello World"


def test_extract_skills_real_text_only():
    sk = extract_skills("We use Python, SQL and Excel.")
    assert "Python" in sk and "SQL" in sk and "Excel" in sk and "PyTorch" not in sk


def test_dedup_merges_sources():
    a = J("ML Engineer", country="India", source="Greenhouse")
    b = J("ML  Engineer", company="acme", country="India", source="Lever")
    out = dedup([a, b])
    assert len(out) == 1 and set(out[0].sources) == {"Greenhouse", "Lever"}
