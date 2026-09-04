"""Job search: strict, domain-agnostic query parsing + hard-filter validation.

Every retrieved job is validated against the parsed constraints BEFORE ranking,
so wrong-country / wrong-domain / wrong-type jobs are removed (never shown at a
lower match score). These tests exercise the pure functions offline (no network).
"""

from app.api.jobs import (
    JobItem,
    dedup,
    employment_matches,
    exp_bounds,
    experience_matches,
    extract_skills,
    job_experience_fields,
    job_matches,
    normalize_location,
    parse_query,
    role_matches,
    strip_html,
    validate_and_rank,
)


def JX(title, **kw):
    """Job with experience parsed from its own title+description (like a real feed)."""
    body = kw.pop("body", "")
    mn, mx, sen, disp = job_experience_fields(title, body)
    return J(title, exp_min=mn, exp_max=mx, sen=sen, **kw)


def J(
    title,
    *,
    company="Acme",
    country=None,
    city=None,
    emp=None,
    wt=None,
    remote_ww=False,
    exp_min=None,
    exp_max=None,
    sen=None,
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
        experience_min=exp_min,
        experience_max=exp_max,
        seniority=sen,
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


# --- experience: parsing ----------------------------------------------------
def test_exp_bounds_variants():
    assert exp_bounds("0-2 years")[:3] == (0, 2, "entry")
    assert exp_bounds("0–2")[:3] == (0, 2, "entry")
    assert exp_bounds("0 to 2 years")[:3] == (0, 2, "entry")
    assert exp_bounds("1-2 years")[:3] == (1, 2, "entry")
    assert exp_bounds("5+ years")[:3] == (5, None, "senior")
    assert exp_bounds("fresher")[:3] == (0, 2, "entry")
    assert exp_bounds("entry level")[:3] == (0, 2, "entry")
    assert exp_bounds("senior")[:3] == (5, None, "senior")
    assert exp_bounds("")[:3] == (None, None, None)


def test_job_experience_extracted_from_description():
    # The exact reported bug source string.
    assert job_experience_fields("ML Engineer", "Exp: 7 to 12yrs")[:3] == (7, 12, "senior")
    assert job_experience_fields("ML Engineer", "Minimum 5 years of experience")[0] == 5
    assert job_experience_fields("ML Engineer", "3+ years experience")[0] == 3
    assert job_experience_fields("Senior ML Engineer", "")[2] == "senior"
    assert job_experience_fields("ML Engineer Intern", "")[2] == "entry"
    assert job_experience_fields("ML Engineer", "Great team, fast pace")[:3] == (None, None, None)


# --- experience: HARD filter ------------------------------------------------
def test_experience_no_constraint_keeps_all():
    c = parse_query("ML Engineer India")  # no experience mentioned
    assert experience_matches(J("ML Engineer", exp_min=7, exp_max=12, sen="senior"), c) is True


def test_internship_is_not_an_experience_constraint():
    c = parse_query("ML Engineer internship India")
    assert c.exp_min is None and c.exp_max is None and c.seniority is None
    # a 7–12y internship posting is not excluded *by experience* (only role/loc/type apply)
    assert experience_matches(J("ML Engineer Intern", exp_min=7, exp_max=12), c) is True


def test_entry_request_excludes_senior_years():
    c = parse_query("ML Engineer India 0-2 years")
    assert c.exp_max == 2 and c.seniority == "entry"
    assert experience_matches(J("ML Engineer", exp_min=7, exp_max=12, sen="senior"), c) is False
    assert experience_matches(J("ML Engineer", exp_min=0, exp_max=2), c) is True
    assert experience_matches(J("ML Engineer", exp_min=1, exp_max=2), c) is True
    assert (
        experience_matches(J("ML Engineer", exp_min=None, exp_max=None), c) is True
    )  # unknown kept


def test_score_does_not_override_experience_hard_filter():
    # Job B has higher role relevance but wrong experience -> still excluded.
    c = parse_query("ML Engineer India 0-2 years")
    b = J("ML Engineer", country="India", exp_min=7, exp_max=12, sen="senior")
    assert job_matches(b, c) is False


def test_must_pass_experience_scenario():
    c = parse_query("ML Engineer jobs in India 0-2 years")
    jobs = [
        J("ML Engineer", country="India", exp_min=0, exp_max=2),  # A include
        J("ML Engineer", country="India", exp_min=1, exp_max=2),  # B include
        J("ML Engineer", country="India", exp_min=7, exp_max=12, sen="senior"),  # C exclude
        J("Senior ML Engineer", country="India", exp_min=8, sen="senior"),  # D exclude
        J("ML Engineer", country="United States", exp_min=0, exp_max=2),  # E exclude (country)
        J("ML Engineer", country="Germany", exp_min=1, exp_max=2),  # F exclude (country)
    ]
    out = validate_and_rank(jobs, c, 50)
    assert len(out) == 2
    assert all(j.country == "India" for j in out)


def test_exact_bug_via_experience_override():
    # "ML Engineer India" then apply the 0–2 years filter (request override).
    c = parse_query("ML Engineer India")
    mn, mx, sen, disp = exp_bounds("0-2")
    c.exp_min, c.exp_max, c.seniority, c.experience = mn, mx, sen, disp
    seven_to_twelve = JX("ML Engineer", country="India", body="Exp: 7 to 12yrs")
    assert seven_to_twelve.experience_min == 7
    assert job_matches(seven_to_twelve, c) is False  # disappears from results
    ok = JX("ML Engineer", country="India", body="0-2 years experience")
    assert job_matches(ok, c) is True


def test_senior_request_excludes_entry():
    c = parse_query("Senior ML Engineer India")
    assert c.seniority == "senior"
    assert experience_matches(J("ML Engineer", exp_min=0, exp_max=2, sen="entry"), c) is False


# --- structured filters (fresh intent, individually removable) --------------
def test_build_constraints_from_filters():
    from app.api.jobs import FilterSpec, build_constraints

    c = build_constraints(FilterSpec(role="HR", country="India", experience="0-2"))
    assert c.country == "India" and c.location_scope == "STRICT_COUNTRY"
    assert "human resources" in c.role_terms and c.exp_max == 2


def test_removing_country_filter_drops_location():
    from app.api.jobs import FilterSpec, build_constraints

    c = build_constraints(FilterSpec(role="HR"))  # country removed
    assert c.location_scope == "ANY" and c.country is None


def test_worldwide_filter_clears_country():
    from app.api.jobs import FilterSpec, build_constraints

    c = build_constraints(FilterSpec(role="HR", country="India", worldwide=True))
    assert c.location_scope == "WORLDWIDE" and c.country is None


def test_filters_role_is_hard_no_tech_leak():
    from app.api.jobs import FilterSpec, build_constraints

    c = build_constraints(FilterSpec(role="HR", country="India"))
    assert role_matches("Human Resources Specialist", c) is True
    assert role_matches("Talent Acquisition Partner", c) is True
    assert role_matches("Software Engineer", c) is False
    assert role_matches("Data Scientist", c) is False


def test_filters_hard_filter_end_to_end():
    from app.api.jobs import FilterSpec, build_constraints

    c = build_constraints(FilterSpec(role="HR", country="India", experience="0-2"))
    jobs = [
        J("HR Specialist", country="India", exp_min=0, exp_max=2),  # keep
        J("ML Engineer", country="India", exp_min=0, exp_max=2),  # wrong role
        J("HR Manager", country="Germany"),  # wrong country
        J("HR Manager", country="India", exp_min=7, exp_max=12, sen="senior"),  # wrong exp
    ]
    out = validate_and_rank(jobs, c, 50)
    assert [j.title for j in out] == ["HR Specialist"]
