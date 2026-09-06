"""Curated catalog of REAL doctoral opportunities & official discovery portals.

Genuine programs/portals with official URLs and stable facts. Per-position details
that change (specific supervisor, exact deadline) are left null — never invented.
Extend this list or add live source adapters (EURAXESS, university APIs) later.
"""

from __future__ import annotations

from app.phd.models import PhdOpportunity

_RAW: list[dict] = [
    {
        "title": "Doctoral studies at ETH Zurich",
        "institution": "ETH Zurich",
        "country": "Switzerland",
        "city": "Zurich",
        "opportunity_type": "phd_program",
        "fields": ["all"],
        "funding_type": "salaried",
        "nationality_eligibility": "international",
        "description": "Doctorate at ETH Zurich; doctoral students are typically employed with a salary.",
        "official_application_url": "https://ethz.ch/en/doctorate.html",
    },
    {
        "title": "EPFL Doctoral School (EDOC) programs",
        "institution": "EPFL",
        "country": "Switzerland",
        "city": "Lausanne",
        "opportunity_type": "phd_program",
        "fields": ["engineering", "cs", "ai", "data_science", "natural_sciences"],
        "funding_type": "salaried",
        "nationality_eligibility": "international",
        "description": "Doctoral programs at EPFL with salaried research assistant positions.",
        "official_application_url": "https://www.epfl.ch/education/phd/",
    },
    {
        "title": "Funded PhD positions (Norwegian universities)",
        "institution": "Norwegian universities",
        "country": "Norway",
        "opportunity_type": "funded_phd_position",
        "fields": ["all"],
        "funding_type": "salaried",
        "nationality_eligibility": "international",
        "deadline_note": "Rolling — advertised as vacancies.",
        "description": "In Norway PhD positions are salaried employment advertised as vacancies.",
        "official_application_url": "https://www.jobbnorge.no/en/search?Category=PhD",
    },
    {
        "title": "EURAXESS — European researcher & PhD vacancies",
        "institution": "European Commission",
        "country": "Europe (multi-country)",
        "countries": [
            "Germany",
            "France",
            "Netherlands",
            "Sweden",
            "Italy",
            "Belgium",
            "Spain",
            "Austria",
        ],
        "opportunity_type": "research_position",
        "fields": ["all"],
        "funding_type": "funded",
        "nationality_eligibility": "international",
        "source": "EURAXESS (portal)",
        "apply_direct": False,
        "description": "Official EU portal listing funded PhD and research positions across Europe.",
        "official_application_url": "https://euraxess.ec.europa.eu/jobs/search",
    },
    {
        "title": "IMPRS — Max Planck doctoral programs",
        "institution": "Max Planck Society",
        "country": "Germany",
        "opportunity_type": "funded_phd_position",
        "fields": ["all"],
        "funding_type": "funded",
        "nationality_eligibility": "international",
        "description": "International Max Planck Research Schools — structured, funded doctoral programs.",
        "official_application_url": "https://www.imprs.mpg.de/",
    },
    {
        "title": "DAAD doctoral research grants",
        "institution": "DAAD",
        "country": "Germany",
        "opportunity_type": "doctoral_scholarship",
        "fields": ["all"],
        "funding_type": "fully_funded",
        "nationality_eligibility": "international",
        "language_requirements": "IELTS/TOEFL or German, programme-dependent.",
        "description": "Doctoral research grants for international PhD candidates in Germany.",
        "official_application_url": "https://www.daad.de/en/study-and-research-in-germany/scholarships/",
    },
    {
        "title": "Marie Skłodowska-Curie Doctoral Networks",
        "institution": "European Commission",
        "country": "Europe (multi-country)",
        "countries": ["Germany", "France", "Netherlands", "Sweden", "Italy", "Belgium", "Spain"],
        "opportunity_type": "fellowship",
        "fields": ["all"],
        "funding_type": "salaried",
        "nationality_eligibility": "international",
        "description": "MSCA-funded doctoral positions across European host institutions (salaried).",
        "official_application_url": "https://marie-sklodowska-curie-actions.ec.europa.eu/actions/doctoral-networks",
    },
    {
        "title": "PhD programmes at TU Delft",
        "institution": "TU Delft",
        "country": "Netherlands",
        "city": "Delft",
        "opportunity_type": "funded_phd_position",
        "fields": ["engineering", "cs", "ai", "natural_sciences"],
        "funding_type": "salaried",
        "nationality_eligibility": "international",
        "description": "PhD candidates at TU Delft are salaried employees; positions advertised as vacancies.",
        "official_application_url": "https://www.tudelft.nl/en/about-tu-delft/working-at-tu-delft/vacancies",
    },
    {
        "title": "Cambridge PhD (DPhil-level doctoral study)",
        "institution": "University of Cambridge",
        "country": "United Kingdom",
        "city": "Cambridge",
        "opportunity_type": "phd_program",
        "fields": ["all"],
        "funding_type": "funded",
        "nationality_eligibility": "international",
        "description": "Doctoral study at Cambridge; funding via studentships (e.g. Gates Cambridge).",
        "official_application_url": "https://www.postgraduate.study.cam.ac.uk/",
    },
    {
        "title": "Oxford DPhil programmes",
        "institution": "University of Oxford",
        "country": "United Kingdom",
        "city": "Oxford",
        "opportunity_type": "phd_program",
        "fields": ["all"],
        "funding_type": "funded",
        "nationality_eligibility": "international",
        "description": "Doctoral (DPhil) study at Oxford; various funded studentships.",
        "official_application_url": "https://www.ox.ac.uk/admissions/graduate/courses",
    },
    {
        "title": "MIT PhD programs (fully funded)",
        "institution": "MIT",
        "country": "United States",
        "city": "Cambridge",
        "opportunity_type": "phd_program",
        "fields": ["all"],
        "funding_type": "fully_funded",
        "nationality_eligibility": "international",
        "description": "MIT doctoral programs typically fund PhD students with tuition + stipend.",
        "official_application_url": "https://gradadmissions.mit.edu/",
    },
    {
        "title": "Stanford PhD programs (fully funded)",
        "institution": "Stanford University",
        "country": "United States",
        "city": "Stanford",
        "opportunity_type": "phd_program",
        "fields": ["all"],
        "funding_type": "fully_funded",
        "nationality_eligibility": "international",
        "description": "Stanford doctoral programs fund admitted PhD students.",
        "official_application_url": "https://gradadmissions.stanford.edu/",
    },
    {
        "title": "Vanier Canada Graduate Scholarships (doctoral)",
        "institution": "Government of Canada",
        "country": "Canada",
        "opportunity_type": "doctoral_scholarship",
        "fields": ["all"],
        "funding_type": "fully_funded",
        "nationality_eligibility": "international",
        "description": "CAD 50,000/yr doctoral scholarships at Canadian universities (nominated).",
        "official_application_url": "https://vanier.gc.ca/en/home-accueil.html",
    },
    {
        "title": "Australian Government Research Training Program (RTP)",
        "institution": "Australian universities",
        "country": "Australia",
        "opportunity_type": "doctoral_scholarship",
        "fields": ["all"],
        "funding_type": "fully_funded",
        "nationality_eligibility": "international",
        "description": "RTP stipend + fee offset scholarships for domestic and international PhD candidates.",
        "official_application_url": "https://www.education.gov.au/research-training-program",
    },
    {
        "title": "SINGA — Singapore International Graduate Award (PhD)",
        "institution": "A*STAR",
        "country": "Singapore",
        "opportunity_type": "doctoral_scholarship",
        "fields": ["engineering", "natural_sciences", "cs", "ai", "data_science", "medicine"],
        "funding_type": "fully_funded",
        "nationality_eligibility": "international",
        "description": "Fully-funded PhD in science/engineering at Singapore universities.",
        "official_application_url": "https://www.a-star.edu.sg/Scholarships/for-graduate-studies/singapore-international-graduate-award-singa",
    },
    {
        "title": "MEXT scholarship — doctoral (Japan)",
        "institution": "Government of Japan (MEXT)",
        "country": "Japan",
        "opportunity_type": "doctoral_scholarship",
        "fields": ["all"],
        "funding_type": "fully_funded",
        "nationality_eligibility": "international",
        "description": "Japanese government scholarship covering doctoral tuition, stipend and travel.",
        "official_application_url": "https://www.studyinjapan.go.jp/en/planning/scholarship/",
    },
]


def catalog() -> list[PhdOpportunity]:
    out: list[PhdOpportunity] = []
    for i, d in enumerate(_RAW):
        d = dict(d)
        title = d["title"]
        slug = "".join(ch if ch.isalnum() else "-" for ch in title.lower()).strip("-")[:40]
        countries = d.pop("countries", None) or [d["country"]]
        url = d["official_application_url"]
        d.setdefault("source", "Curated · official")
        out.append(
            PhdOpportunity(
                id=f"phd-{i}-{slug}",
                countries=countries,
                source_url=url,
                official_university_url=url,
                sources=[d["source"]],
                **d,
            )
        )
    return out
