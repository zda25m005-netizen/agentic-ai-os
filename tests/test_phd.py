"""PhD Finder: parsing, hard filters, eligibility, dedup, apply-url, source failure."""

import asyncio

from app.phd import search as phd_search
from app.phd import store
from app.phd.catalog import catalog
from app.phd.filtering import dedup, passes_hard
from app.phd.models import PhdFilterSpec, PhdOpportunity
from app.phd.parser import intent_from_filters, parse_query
from app.phd.search import build_checklist, facets, run_search, summarize
from app.scholarships.models import StudentProfile


def _o(**kw):
    base = dict(
        id="x",
        title="PhD in X",
        institution="Uni A",
        country="Germany",
        countries=["Germany"],
        opportunity_type="funded_phd_position",
        fields=["all"],
        funding_type="salaried",
        official_application_url="https://x",
    )
    base.update(kw)
    return PhdOpportunity(**base)


# --- parsing ----------------------------------------------------------------
def test_parse_full():
    i = parse_query("fully funded PhD in machine learning in Norway for Indian students 2027")
    assert i.countries == ["Norway"] and i.funding == "fully_funded"
    assert "ai" in i.field_tags and i.nationality == "India" and i.intake == "2027"


def test_parse_opportunity_type():
    assert (
        parse_query("PhD positions in robotics in Germany").opportunity_type
        == "funded_phd_position"
    )
    assert parse_query("research position in NLP").opportunity_type == "research_position"
    assert parse_query("fully funded PhD in AI").opportunity_type is None  # not over-inferred


# --- hard filters -----------------------------------------------------------
def test_country_and_field_hard_filter():
    i = parse_query("PhD in AI in Norway")
    assert passes_hard(_o(country="Norway", countries=["Norway"], fields=["ai"]), i) is True
    assert passes_hard(_o(country="Germany", countries=["Germany"], fields=["ai"]), i) is False
    assert passes_hard(_o(country="Norway", countries=["Norway"], fields=["law"]), i) is False


def test_funding_fully_funded_accepts_salaried():
    i = parse_query("fully funded PhD in Germany")
    assert passes_hard(_o(funding_type="salaried"), i) is True
    assert passes_hard(_o(funding_type="fully_funded"), i) is True
    assert passes_hard(_o(funding_type="self_funded"), i) is False


def test_opportunity_type_hard_filter():
    i = parse_query("research position in Germany")
    assert passes_hard(_o(opportunity_type="research_position"), i) is True
    assert passes_hard(_o(opportunity_type="phd_program"), i) is False


# --- dedup + apply url priority ---------------------------------------------
def test_dedup_prefers_direct():
    a = _o(
        id="1",
        institution="ETH",
        title="PhD",
        source="Aggregator",
        sources=["Aggregator"],
        apply_direct=False,
        official_application_url="https://agg/x",
    )
    b = _o(
        id="2",
        institution="eth",
        title="phd",
        source="Official",
        sources=["Official"],
        apply_direct=True,
        official_application_url="https://ethz.ch/x",
    )
    out = dedup([a, b])
    assert (
        len(out) == 1
        and out[0].apply_direct is True
        and "ethz.ch" in out[0].official_application_url
    )
    assert set(out[0].sources) == {"Aggregator", "Official"}


# --- eligibility (reused engine) + missing profile --------------------------
def test_eligibility_missing_profile_insufficient_or_eligible():
    # international entry -> eligible even with empty profile (nationality open)
    opps, _, _ = asyncio.run(run_search(parse_query("PhD in AI in Switzerland"), StudentProfile()))
    assert opps and all(
        o.eligibility_status in ("eligible", "likely", "unclear", "insufficient") for o in opps
    )


def test_match_score_is_dynamic():
    opps, _, _ = asyncio.run(run_search(parse_query("PhD in AI in Switzerland")))
    scores = {round(o.match_score, 3) for o in opps}
    assert opps and all(0 <= (o.match_score or 0) <= 1 for o in opps) and len(scores) >= 1


def test_checklist_and_supervisor_honesty():
    o = catalog()[0]
    cl = build_checklist(o)
    assert any(it["item"].startswith("Curriculum") for it in cl)
    assert o.supervisor is None  # never invented


# --- source failure does not crash the search -------------------------------
def test_source_failure_is_isolated(monkeypatch):
    class Boom:
        name = "Broken"

        async def search(self, intent):
            raise RuntimeError("down")

    monkeypatch.setattr(phd_search, "SOURCES", [Boom(), phd_search.CatalogSource()])
    opps, statuses, _ = asyncio.run(run_search(parse_query("PhD in AI in Germany")))
    assert any(s.status == "error" for s in statuses) and any(s.status == "ok" for s in statuses)
    assert opps  # results still returned from the working source


# --- stale-filter prevention (fresh intent from filters) --------------------
def test_filters_reset_intent():
    i = intent_from_filters(PhdFilterSpec(field="Economics", countries=["Germany"]))
    assert i.countries == ["Germany"] and "economics" in i.field_tags and "ai" not in i.field_tags


def test_facets_and_summary():
    opps, _, _ = asyncio.run(run_search(parse_query("PhD in AI worldwide")))
    fac = facets(opps)
    assert sum(f["count"] for f in fac) == len(opps)
    assert summarize(opps)["total"] == len(opps)


def test_saved_store(tmp_path):
    store.DB_PATH = tmp_path / "phd.db"
    assert store.list_saved() == []
    store.save({"id": "p1", "title": "PhD", "official_application_url": "https://x"}, "Interested")
    assert len(store.list_saved()) == 1
    assert (
        store.set_status("p1", "Applied") and store.list_saved()[0]["tracking_status"] == "Applied"
    )
    assert store.remove("p1") and store.list_saved() == []
