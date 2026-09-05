"""Scholarship Finder: parsing, hard filtering, eligibility, dedup, storage (offline)."""

import asyncio

from app.scholarships import store
from app.scholarships.catalog import catalog
from app.scholarships.eligibility import eligibility_status
from app.scholarships.filtering import dedup, passes_hard
from app.scholarships.models import FilterSpec, Scholarship
from app.scholarships.parser import intent_from_filters, parse_query
from app.scholarships.search import run_search, summarize


# --- parsing ----------------------------------------------------------------
def test_parse_full_intent():
    i = parse_query("fully funded master's AI scholarships in Switzerland for Indian students 2027")
    assert i.degree == "master" and i.funding == "fully_funded"
    assert i.countries == ["Switzerland"] and i.nationality == "India" and i.intake == "2027"
    assert "ai" in i.field_tags


def test_parse_phd_norway():
    i = parse_query("PhD scholarships in Norway")
    assert i.degree == "phd" and i.countries == ["Norway"] and i.funding is None


def test_parse_no_ielts():
    i = parse_query("masters scholarships in Switzerland without IELTS")
    assert i.no_ielts is True and i.degree == "master"


def test_parse_is_domain_agnostic_hr():
    i = parse_query("HR scholarships in Germany")
    assert i.countries == ["Germany"] and "social_sciences" in i.field_tags
    assert "ai" not in i.field_tags and "cs" not in i.field_tags


# --- catalog integrity (no fake / unsafe URLs) ------------------------------
def test_catalog_urls_are_official_https():
    for s in catalog():
        assert s.application_url.startswith("https://")
        assert s.apply_direct is True
        assert s.deadline is None  # exact dates are not fabricated


# --- hard filtering ---------------------------------------------------------
def _mk(**kw):
    base = dict(
        id="x",
        title="T",
        provider="P",
        country="Germany",
        countries=["Germany"],
        degree_levels=["master"],
        fields=["all"],
        funding_type="fully_funded",
        application_url="https://x",
    )
    base.update(kw)
    return Scholarship(**base)


def test_country_hard_filter():
    i = parse_query("PhD scholarships in Norway")
    de = _mk(country="Germany", countries=["Germany"], degree_levels=["phd"])
    no = _mk(country="Norway", countries=["Norway"], degree_levels=["phd"])
    assert passes_hard(no, i) is True and passes_hard(de, i) is False


def test_degree_hard_filter():
    i = parse_query("PhD scholarships in Germany")
    assert (
        passes_hard(_mk(country="Germany", countries=["Germany"], degree_levels=["master"]), i)
        is False
    )
    assert (
        passes_hard(_mk(country="Germany", countries=["Germany"], degree_levels=["phd"]), i) is True
    )


def test_field_hard_filter_excludes_offdomain():
    i = parse_query("AI scholarships in Germany")
    all_field = _mk(fields=["all"])
    ai_field = _mk(fields=["ai", "cs"])
    hr_field = _mk(fields=["social_sciences"])
    assert passes_hard(all_field, i) is True  # open to any field
    assert passes_hard(ai_field, i) is True
    assert passes_hard(hr_field, i) is False  # off-domain excluded


def test_funding_fully_funded_hard():
    i = parse_query("fully funded masters in Germany")
    assert passes_hard(_mk(funding_type="fully_funded"), i) is True
    assert passes_hard(_mk(funding_type="partial"), i) is False


# --- eligibility ------------------------------------------------------------
def test_eligibility_international():
    s = _mk(nationality_eligibility="international")
    status, reasons = eligibility_status(s, parse_query("masters in Germany"))
    assert status == "eligible" and any("international" in r.lower() for r in reasons)


def test_eligibility_commonwealth_indian_ok_but_us_not():
    s = _mk(nationality_eligibility="commonwealth")
    ok, _ = eligibility_status(s, parse_query("masters in UK for Indian students"))
    no, _ = eligibility_status(s, parse_query("masters in UK for American students"))
    assert ok == "eligible" and no == "not_eligible"


def test_eligibility_unclear_when_unknown():
    s = _mk(nationality_eligibility="specific")
    status, _ = eligibility_status(s, parse_query("masters in UK"))
    assert status == "unclear"


# --- dedup + apply url -------------------------------------------------------
def test_dedup_merges_and_prefers_direct():
    a = _mk(
        id="1",
        provider="DAAD",
        title="DAAD Study",
        source="Aggregator",
        sources=["Aggregator"],
        apply_direct=False,
        application_url="https://agg/x",
    )
    b = _mk(
        id="2",
        provider="daad",
        title="daad  study",
        source="Official",
        sources=["Official"],
        apply_direct=True,
        application_url="https://daad.de/x",
    )
    out = dedup([a, b])
    assert len(out) == 1 and out[0].apply_direct is True
    assert "daad.de" in out[0].application_url and set(out[0].sources) == {"Aggregator", "Official"}


# --- fresh intent from filters (bug prevention) -----------------------------
def test_filters_reset_intent():
    # user removed AI + Switzerland; only HR + Germany remain
    i = intent_from_filters(FilterSpec(field="HR", countries=["Germany"]))
    assert i.countries == ["Germany"] and "social_sciences" in i.field_tags
    assert "ai" not in i.field_tags


# --- end-to-end + empty -----------------------------------------------------
def test_search_e2e_and_summary():
    schs, statuses, fetched = asyncio.run(
        run_search(parse_query("fully funded masters in Switzerland"))
    )
    assert fetched > 0 and all(s.country == "Switzerland" for s in schs)
    assert all(s.funding_type == "fully_funded" for s in schs)
    s = summarize(schs)
    assert s["total"] == len(schs) and s["fully_funded"] == len(schs)


def test_search_empty_when_impossible():
    schs, _, fetched = asyncio.run(run_search(parse_query("PhD scholarships in Finland")))
    assert fetched > 0 and schs == []  # no Finland program in catalog -> honest empty


# --- saved store ------------------------------------------------------------
def test_saved_store_roundtrip(tmp_path):
    store.DB_PATH = tmp_path / "s.db"
    assert store.list_saved() == []
    store.save({"id": "sch-1", "title": "DAAD", "application_url": "https://daad.de"}, "Interested")
    saved = store.list_saved()
    assert len(saved) == 1 and saved[0]["tracking_status"] == "Interested"
    assert store.set_status("sch-1", "Applied") is True
    assert store.list_saved()[0]["tracking_status"] == "Applied"
    assert store.remove("sch-1") is True and store.list_saved() == []
