"""Job Search — strict, domain-agnostic query matching over real job boards.

The user's natural-language query is the source of truth. We parse it into
structured constraints (role/domain, employment type, country/city, remote,
experience, and a location *scope*), fetch real postings, then apply those
constraints as HARD FILTERS before ranking — invalid-location or wrong-domain
jobs are removed, never merely down-ranked. Nothing is fabricated.

Sources (all official; none require scraping):
  * Adzuna       — country-scoped, domain-agnostic aggregator (India + most
                   countries, every occupation). Active only when ADZUNA_APP_ID
                   and ADZUNA_APP_KEY are set. This is what makes "HR jobs in
                   India" or "Accountant in London" return real results.
  * Greenhouse   — https://boards-api.greenhouse.io/v1/boards/{token}/jobs
  * Lever        — https://api.lever.co/v0/postings/{company}

Coverage note: Greenhouse/Lever only expose the curated companies' own tech
postings. Broad/non-tech/most-country coverage comes from Adzuna once its free
keys are configured; without them those queries honestly return few/zero rows.
"""

from __future__ import annotations

import asyncio
import html
import re
from datetime import UTC, datetime

import httpx
from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.core.config import get_settings

router = APIRouter(prefix="/jobs", tags=["jobs"])

_UA = "AgenticAIOS-JobSearch/1.0 (+https://github.com/zda25m005-netizen/agentic-ai-os)"

GREENHOUSE_BOARDS: list[tuple[str, str]] = [
    ("anthropic", "Anthropic"),
    ("databricks", "Databricks"),
    ("scaleai", "Scale AI"),
    ("cohere", "Cohere"),
    ("figma", "Figma"),
    ("gitlab", "GitLab"),
    ("cloudflare", "Cloudflare"),
    ("stripe", "Stripe"),
    ("dropbox", "Dropbox"),
    ("airtable", "Airtable"),
    ("discord", "Discord"),
    ("robinhood", "Robinhood"),
]
LEVER_BOARDS: list[tuple[str, str]] = [
    ("mistral", "Mistral AI"),
    ("huggingface", "Hugging Face"),
    ("netlify", "Netlify"),
    ("plaid", "Plaid"),
]

# --------------------------------------------------------------------------- #
# Location normalization (country + city), used for BOTH parsing and validation
# --------------------------------------------------------------------------- #
COUNTRY_ALIASES: dict[str, list[str]] = {
    "India": ["india", "bharat"],
    "United States": [
        "united states",
        "usa",
        "u.s.a",
        "u.s.",
        " us ",
        "america",
        "united states of america",
    ],
    "United Kingdom": [
        "united kingdom",
        " uk ",
        "u.k.",
        "britain",
        "great britain",
        "england",
        "scotland",
        "wales",
    ],
    "Germany": ["germany", "deutschland"],
    "Switzerland": ["switzerland", "schweiz", "suisse", "svizzera"],
    "United Arab Emirates": ["united arab emirates", " uae ", "u.a.e"],
    "Singapore": ["singapore"],
    "France": ["france"],
    "Netherlands": ["netherlands", "holland"],
    "Canada": ["canada"],
    "Ireland": ["ireland"],
    "Spain": ["spain", "españa", "espana"],
    "Italy": ["italy", "italia"],
    "Australia": ["australia"],
    "Austria": ["austria"],
    "Belgium": ["belgium"],
    "Poland": ["poland"],
    "Brazil": ["brazil", "brasil"],
    "New Zealand": ["new zealand"],
    "South Africa": ["south africa"],
    "Mexico": ["mexico", "méxico"],
    "Japan": ["japan"],
}
CITY_TO_COUNTRY: dict[str, tuple[str, str]] = {
    "mumbai": ("Mumbai", "India"),
    "bengaluru": ("Bengaluru", "India"),
    "bangalore": ("Bengaluru", "India"),
    "new delhi": ("New Delhi", "India"),
    "delhi": ("Delhi", "India"),
    "hyderabad": ("Hyderabad", "India"),
    "pune": ("Pune", "India"),
    "chennai": ("Chennai", "India"),
    "kolkata": ("Kolkata", "India"),
    "gurgaon": ("Gurgaon", "India"),
    "gurugram": ("Gurugram", "India"),
    "noida": ("Noida", "India"),
    "ahmedabad": ("Ahmedabad", "India"),
    "dubai": ("Dubai", "United Arab Emirates"),
    "abu dhabi": ("Abu Dhabi", "United Arab Emirates"),
    "london": ("London", "United Kingdom"),
    "manchester": ("Manchester", "United Kingdom"),
    "cambridge": ("Cambridge", "United Kingdom"),
    "zurich": ("Zurich", "Switzerland"),
    "zürich": ("Zurich", "Switzerland"),
    "geneva": ("Geneva", "Switzerland"),
    "lausanne": ("Lausanne", "Switzerland"),
    "basel": ("Basel", "Switzerland"),
    "berlin": ("Berlin", "Germany"),
    "munich": ("Munich", "Germany"),
    "münchen": ("Munich", "Germany"),
    "hamburg": ("Hamburg", "Germany"),
    "frankfurt": ("Frankfurt", "Germany"),
    "cologne": ("Cologne", "Germany"),
    "paris": ("Paris", "France"),
    "amsterdam": ("Amsterdam", "Netherlands"),
    "toronto": ("Toronto", "Canada"),
    "vancouver": ("Vancouver", "Canada"),
    "montreal": ("Montreal", "Canada"),
    "dublin": ("Dublin", "Ireland"),
    "madrid": ("Madrid", "Spain"),
    "barcelona": ("Barcelona", "Spain"),
    "singapore": ("Singapore", "Singapore"),
    "sydney": ("Sydney", "Australia"),
    "melbourne": ("Melbourne", "Australia"),
    "new york": ("New York", "United States"),
    "san francisco": ("San Francisco", "United States"),
    "seattle": ("Seattle", "United States"),
    "boston": ("Boston", "United States"),
    "austin": ("Austin", "United States"),
    "chicago": ("Chicago", "United States"),
    "los angeles": ("Los Angeles", "United States"),
}
# US state tokens that reliably imply the country in board location strings.
_US_HINTS = re.compile(
    r"\b(usa|united states|u\.s\.|,\s*(ca|ny|wa|tx|ma|il|co|ga|va|nj|fl))\b", re.I
)


def normalize_location(text: str | None) -> tuple[str | None, str | None, bool, bool]:
    """Return (country, city, is_remote, remote_worldwide) from a location string.

    Only structured location text is inspected — never a job description.
    """
    if not text:
        return None, None, False, False
    t = f" {text.lower()} "
    is_remote = bool(re.search(r"\b(remote|work from home|wfh|distributed)\b", t))
    remote_worldwide = is_remote and bool(
        re.search(r"\b(worldwide|global|anywhere|international)\b", t)
    )

    city = country = None
    for key, (cname, ccountry) in CITY_TO_COUNTRY.items():
        if re.search(rf"\b{re.escape(key)}\b", t):
            city, country = cname, ccountry
            break
    if country is None:
        for norm, aliases in COUNTRY_ALIASES.items():
            if any(a in t for a in aliases):
                country = norm
                break
    if country is None and _US_HINTS.search(text):
        country = "United States"
    return country, city, is_remote, remote_worldwide


# --------------------------------------------------------------------------- #
# Query parsing -> structured constraints (domain-agnostic)
# --------------------------------------------------------------------------- #
_WORLDWIDE = re.compile(
    r"\b(worldwide|world wide|global(?:ly)?|anywhere|any country|all countries|international)\b",
    re.I,
)
_REMOTE = re.compile(r"\bremote\b|\bwork from home\b|\bwfh\b", re.I)
_HYBRID = re.compile(r"\bhybrid\b", re.I)
_ONSITE = re.compile(r"\bon[- ]?site\b|\bin[- ]?office\b", re.I)
_EMPLOYMENT = [
    (
        "Internship",
        re.compile(r"\b(intern(ship)?s?|apprentice(ship)?|working student|trainee)\b", re.I),
    ),
    ("Part-time", re.compile(r"\bpart[- ]?time\b", re.I)),
    ("Full-time", re.compile(r"\bfull[- ]?time\b", re.I)),
    ("Contract", re.compile(r"\bcontract(or)?\b", re.I)),
    ("Freelance", re.compile(r"\bfreelance(r)?\b", re.I)),
]
_EXPERIENCE = [
    re.compile(r"\b(\d)\s*[-–to]+\s*(\d)\s*years?\b", re.I),
    re.compile(r"\b(\d)\+?\s*years?\b", re.I),
    re.compile(r"\b(fresh(er)?|new\s*grad(uate)?|entry[- ]?level|graduate)\b", re.I),
    re.compile(r"\b(senior|sr\.?|lead|principal|staff)\b", re.I),
]
# Title words too generic to establish a role/domain on their own.
GENERIC_ROLE = {
    "engineer",
    "manager",
    "analyst",
    "specialist",
    "developer",
    "scientist",
    "coordinator",
    "executive",
    "associate",
    "assistant",
    "lead",
    "senior",
    "junior",
    "intern",
    "consultant",
    "officer",
    "director",
    "administrator",
    "representative",
    "agent",
    "staff",
    "principal",
    "head",
}
# Synonym groups — expand terminology WITHIN a domain, never across domains.
SYNONYM_GROUPS: list[set[str]] = [
    {"hr", "human resources", "people operations", "talent acquisition", "recruiter", "recruiting"},
    {"ml", "machine learning"},
    {"ai", "artificial intelligence"},
    {"swe", "sde", "software engineer", "software developer", "software"},
    {"pm", "product manager", "product management", "product"},
    {"qa", "quality assurance", "test"},
    {"ux", "user experience"},
    {"ui", "user interface"},
    {"devops", "site reliability", "sre"},
    {"data scientist", "data science"},
    {"finance", "financial", "accounting", "accountant"},
    {"marketing", "growth", "brand"},
    {"sales", "business development", "account executive"},
    {"design", "designer", "graphic design"},
    {"teacher", "teaching", "educator", "education", "tutor"},
    {"operations", "ops"},
    {"mechanical", "mechanical engineering"},
    {"civil", "civil engineering"},
    {"electrical", "electrical engineering"},
]
_FILLER = {
    "find",
    "search",
    "show",
    "get",
    "give",
    "me",
    "my",
    "all",
    "any",
    "some",
    "jobs",
    "job",
    "roles",
    "role",
    "opportunity",
    "opportunities",
    "opening",
    "openings",
    "position",
    "positions",
    "vacancy",
    "vacancies",
    "listing",
    "listings",
    "in",
    "at",
    "on",
    "for",
    "with",
    "and",
    "or",
    "of",
    "the",
    "a",
    "an",
    "to",
    "near",
    "around",
    "based",
    "hiring",
    "hire",
    "that",
    "looking",
    "look",
    "want",
    "need",
    "please",
    "career",
    "careers",
    "work",
    "working",
    "who",
    "are",
    "is",
    "available",
    "within",
    "across",
}


class Constraints(BaseModel):
    role: str | None = None  # display phrase, e.g. "Mechanical Engineer"
    role_terms: list[str] = Field(default_factory=list)  # match terms (incl. synonyms)
    employment_type: str | None = None
    country: str | None = None  # normalized
    city: str | None = None
    remote: bool = False
    hybrid: bool = False
    onsite: bool = False
    experience: str | None = None  # display, e.g. "0–2 years"
    exp_min: int | None = None  # requested candidate min years (hard constraint)
    exp_max: int | None = None  # requested candidate max years (hard constraint)
    seniority: str | None = None  # "entry" | "senior" (from the request)
    location_scope: str = "ANY"  # WORLDWIDE | STRICT_COUNTRY | STRICT_CITY | ANY
    raw: str = ""


def _match_terms(cons: Constraints) -> list[str]:
    """Terms that can establish the role: prefer non-generic; else fall back."""
    non_generic = [t for t in cons.role_terms if t not in GENERIC_ROLE]
    return non_generic or cons.role_terms


def parse_query(query: str) -> Constraints:
    raw = (query or "").strip()
    work = f" {raw} "
    matched_spans: list[str] = []

    # scope / location
    worldwide = bool(_WORLDWIDE.search(raw))
    city = country = None
    lower = work.lower()
    for key, (cname, ccountry) in CITY_TO_COUNTRY.items():
        if re.search(rf"\b{re.escape(key)}\b", lower):
            city, country = cname, ccountry
            matched_spans.append(key)
            break
    if country is None:
        for norm, aliases in COUNTRY_ALIASES.items():
            hit = next((a for a in aliases if a in lower), None)
            if hit:
                country = norm
                matched_spans.append(hit.strip())
                break

    if worldwide:
        scope, country, city = "WORLDWIDE", None, None
    elif city:
        scope = "STRICT_CITY"
    elif country:
        scope = "STRICT_COUNTRY"
    else:
        scope = "ANY"

    remote = bool(_REMOTE.search(raw))
    hybrid = bool(_HYBRID.search(raw))
    onsite = bool(_ONSITE.search(raw))

    employment_type = None
    for label, rx in _EMPLOYMENT:
        m = rx.search(raw)
        if m:
            employment_type = label
            matched_spans.append(m.group(0))
            break

    experience = None
    exp_min = exp_max = None
    seniority = None
    for rx in _EXPERIENCE:
        m = rx.search(raw)
        if m:
            g = m.group(0)
            matched_spans.append(g)
            exp_min, exp_max, seniority, experience = exp_bounds(g)
            break

    # role phrase = query minus every matched location/type/experience/worldwide span
    role_src = raw
    for span in matched_spans + (
        [
            "worldwide",
            "global",
            "globally",
            "anywhere",
            "international",
            "remote",
            "hybrid",
            "onsite",
            "on-site",
            "work from home",
            "wfh",
        ]
    ):
        role_src = re.sub(rf"\b{re.escape(span)}\b", " ", role_src, flags=re.I)
    tokens = re.findall(r"[a-zA-Z][a-zA-Z0-9+#]*", role_src)
    role_tokens = [t for t in tokens if t.lower() not in _FILLER and not t.isdigit()]
    role = " ".join(role_tokens).strip()

    role_terms: list[str] = []
    seen: set[str] = set()
    for t in role_tokens:
        tl = t.lower()
        if tl not in seen:
            seen.add(tl)
            role_terms.append(tl)
    role_l = role.lower()
    for group in SYNONYM_GROUPS:
        if any(re.search(rf"\b{re.escape(g)}\b", role_l) for g in group):
            for g in group:
                if g not in role_terms:
                    role_terms.append(g)

    return Constraints(
        role=(role if role else None),
        role_terms=role_terms,
        employment_type=employment_type,
        country=country,
        city=city,
        remote=remote,
        hybrid=hybrid,
        onsite=onsite,
        experience=experience,
        exp_min=exp_min,
        exp_max=exp_max,
        seniority=seniority,
        location_scope=scope,
        raw=raw,
    )


# --------------------------------------------------------------------------- #
# Models
# --------------------------------------------------------------------------- #
class SearchRequest(BaseModel):
    query: str = ""
    limit: int = 200
    # legacy hints (ignored; query is authoritative) — kept for compatibility
    roles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
    experience: str | None = None
    remote: bool = False


class JobItem(BaseModel):
    id: str
    title: str
    company: str
    location: str | None = None
    country: str | None = None
    city: str | None = None
    employment_type: str | None = None
    experience: str | None = None  # display, from the posting
    experience_min: int | None = None  # required years (from posting), if stated
    experience_max: int | None = None
    seniority: str | None = None  # "entry" | "senior"
    workplace_type: str | None = None
    remote_worldwide: bool = False
    salary: str | None = None
    salary_type: str | None = None
    skills: list[str] = Field(default_factory=list)
    description: str = ""
    posted_at: str | None = None
    source: str
    source_url: str | None = None
    application_url: str
    match_score: float | None = None
    match_breakdown: dict[str, float] = Field(default_factory=dict)
    sources: list[str] = Field(default_factory=list)


class SourceStatus(BaseModel):
    source: str
    status: str
    count: int = 0
    note: str | None = None


class JobSearchResponse(BaseModel):
    jobs: list[JobItem]
    sources: list[SourceStatus]
    constraints: Constraints
    total_fetched: int
    total_after_filter: int


# --------------------------------------------------------------------------- #
# Text helpers + skill extraction
# --------------------------------------------------------------------------- #
_SKILLS = [
    "Python",
    "PyTorch",
    "TensorFlow",
    "JAX",
    "Scikit-learn",
    "Pandas",
    "NumPy",
    "SQL",
    "Spark",
    "Kafka",
    "Airflow",
    "Snowflake",
    "AWS",
    "GCP",
    "Azure",
    "Kubernetes",
    "Docker",
    "Terraform",
    "Java",
    "Scala",
    "C++",
    "Go",
    "Rust",
    "TypeScript",
    "JavaScript",
    "React",
    "NLP",
    "Transformers",
    "LLM",
    "LLMs",
    "Machine Learning",
    "Deep Learning",
    "MLOps",
    "Excel",
    "Tableau",
    "Power BI",
    "SAP",
    "Salesforce",
    "Figma",
    "SEO",
    "AutoCAD",
    "SolidWorks",
]


def strip_html(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def summarize(text: str, limit: int = 320) -> str:
    text = strip_html(text)
    if len(text) <= limit:
        return text
    cut = text[:limit]
    sp = cut.rfind(" ")
    return (cut[:sp] if sp > 40 else cut).rstrip(" ,;.") + "…"


def extract_skills(text: str, limit: int = 8) -> list[str]:
    blob = strip_html(text)
    out: list[str] = []
    for s in _SKILLS:
        if re.search(rf"(?<![\w+]){re.escape(s)}(?![\w+])", blob, re.I):
            v = "LLM" if s == "LLMs" else s
            if v not in out:
                out.append(v)
        if len(out) >= limit:
            break
    return out


def _iso_date(value) -> str | None:
    if value is None:
        return None
    try:
        if isinstance(value, int | float):
            dt = datetime.fromtimestamp(value / 1000, tz=UTC)
        else:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.date().isoformat()
    except Exception:
        return None


def _intern_title(title: str) -> bool:
    return bool(re.search(r"\b(intern(ship)?|apprentice|working student|trainee)\b", title, re.I))


# --------------------------------------------------------------------------- #
# Experience parsing — the single canonical implementation used by both the
# query (what the candidate has / wants) and each job (what it requires).
# --------------------------------------------------------------------------- #
def exp_bounds(text: str | None) -> tuple[int | None, int | None, str | None, str | None]:
    """Parse an experience expression -> (min, max, seniority, display).

    Handles "0-2", "0–2 years", "0 to 2 years", "5+ years", "fresher",
    "entry level", "graduate", "junior", "senior/lead/principal/staff".
    """
    t = (text or "").lower()
    m = re.search(r"(\d{1,2})\s*(?:-|–|—|to)\s*(\d{1,2})", t)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if a <= b <= 50:
            sen = "entry" if b <= 2 else "senior" if a >= 5 else None
            return a, b, sen, f"{a}–{b} years"
    m = re.search(r"(\d{1,2})\s*\+", t)
    if m:
        a = int(m.group(1))
        return a, None, ("senior" if a >= 5 else "entry" if a <= 2 else None), f"{a}+ years"
    if re.search(
        r"\b(fresher|freshers|fresh|new\s*grad(uate)?|entry[- ]?level|entry|graduate|junior)\b", t
    ):
        return 0, 2, "entry", "0–2 years"
    if re.search(r"\b(senior|sr\.?|lead|principal|staff)\b", t):
        return 5, None, "senior", "Senior"
    m = re.search(r"(\d{1,2})\s*years?", t)
    if m:
        a = int(m.group(1))
        return a, a, ("entry" if a <= 2 else "senior" if a >= 5 else None), f"{a} years"
    return None, None, None, None


def _exp_display(mn: int | None, mx: int | None, sen: str | None) -> str | None:
    if mn is not None and mx is not None:
        return f"{mn} years" if mn == mx else f"{mn}–{mx} years"
    if mn is not None:
        return f"{mn}+ years"
    if sen == "entry":
        return "Entry level"
    if sen == "senior":
        return "Senior"
    return None


def job_experience_fields(
    title: str, body: str
) -> tuple[int | None, int | None, str | None, str | None]:
    """Extract a job's REQUIRED experience from its title + description.

    Reads structured phrasing ("7 to 12 years", "min 5 years", "3+ years",
    "5 years of experience") and title seniority. Returns
    (experience_min, experience_max, seniority, display); all None when the
    posting doesn't state it (never inferred as entry-level).
    """
    text = f"{title}\n{strip_html(body)[:2000]}".lower()
    m = re.search(r"(\d{1,2})\s*(?:-|–|—|to)\s*(\d{1,2})\s*\+?\s*(?:years?|yrs?)", text)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        if a <= b <= 50:
            sen = "entry" if b <= 2 else "senior" if a >= 5 else None
            return a, b, sen, _exp_display(a, b, sen)
    m = re.search(r"(?:min(?:imum)?(?:\s+of)?|at least)\s*(\d{1,2})\s*\+?\s*(?:years?|yrs?)", text)
    if not m:
        m = re.search(r"(\d{1,2})\s*\+\s*(?:years?|yrs?)", text)
    if not m:
        m = re.search(r"(\d{1,2})\s*(?:years?|yrs?)\s+(?:of\s+)?(?:experience|exp)", text)
    if m:
        a = int(m.group(1))
        sen = "senior" if a >= 5 else "entry" if a <= 2 else None
        return a, None, sen, _exp_display(a, None, sen)
    if _intern_title(title) or re.search(
        r"\b(fresher|freshers|graduate|entry[- ]?level|new grad|junior)\b", text
    ):
        return 0, 2, "entry", "Entry level"
    if re.search(r"\b(senior|sr\.?|lead|principal|staff|head of|director|vp)\b", title.lower()):
        return None, None, "senior", "Senior"
    return None, None, None, None


# --------------------------------------------------------------------------- #
# Strict validation (hard filters) — runs BEFORE ranking
# --------------------------------------------------------------------------- #
def role_matches(title: str, cons: Constraints) -> bool:
    terms = _match_terms(cons)
    if not terms:
        return True  # no role specified -> any role
    tl = title.lower()
    return any(re.search(rf"\b{re.escape(t)}\b", tl) for t in terms)


def employment_matches(job: JobItem, cons: Constraints) -> bool:
    if not cons.employment_type:
        return True
    want = cons.employment_type
    is_intern = _intern_title(job.title) or (job.employment_type or "").lower().startswith("intern")
    jt = (job.employment_type or "").lower()
    if want == "Internship":
        return is_intern
    if is_intern:
        return False  # a non-internship search must exclude internships
    if want == "Part-time":
        return "part" in jt
    if want == "Contract":
        return "contract" in jt
    if want == "Freelance":
        return "freelance" in jt or "contract" in jt
    if want == "Full-time":
        return jt in ("", "full-time", "full time", "permanent") or "full" in jt
    return True


def location_matches(job: JobItem, cons: Constraints) -> bool:
    scope = cons.location_scope
    if scope in ("ANY", "WORLDWIDE"):
        return True
    if scope == "STRICT_COUNTRY":
        if job.country and job.country == cons.country:
            return True  # onsite or remote-in-country both fine
        return False  # unknown / other country / remote-worldwide -> exclude
    if scope == "STRICT_CITY":
        return bool(job.city and cons.city and job.city.lower() == cons.city.lower())
    return True


def workplace_matches(job: JobItem, cons: Constraints) -> bool:
    wt = (job.workplace_type or "").lower()
    if cons.remote:
        return "remote" in wt or "hybrid" in wt
    if cons.onsite:
        return wt in ("", "onsite", "on-site") or "onsite" in wt
    return True


def experience_matches(job: JobItem, cons: Constraints) -> bool:
    """HARD filter: a job whose required experience exceeds the requested range
    is REMOVED (not down-ranked). Jobs that don't state experience are kept, to
    avoid false negatives — unknown is not treated as too-senior.
    """
    if cons.exp_min is None and cons.exp_max is None and cons.seniority is None:
        return True  # user set no experience constraint
    jmin, jmax, jsen = job.experience_min, job.experience_max, job.seniority
    # Entry-level request must exclude clearly senior/lead/principal roles.
    if cons.seniority == "entry" and jsen == "senior":
        return False
    # Job's minimum required years exceeds what the candidate has (requested max).
    if cons.exp_max is not None and jmin is not None and jmin > cons.exp_max:
        return False
    # Senior request should drop clearly entry-level/junior roles.
    if cons.seniority == "senior" and jsen == "entry":
        return False
    # Job's ceiling is below the requested floor (e.g. want 5+, job caps at 2).
    if cons.exp_min is not None and jmax is not None and jmax < cons.exp_min:
        return False
    return True


def job_matches(job: JobItem, cons: Constraints) -> bool:
    return (
        role_matches(job.title, cons)
        and employment_matches(job, cons)
        and location_matches(job, cons)
        and workplace_matches(job, cons)
        and experience_matches(job, cons)
    )


def compute_score(job: JobItem, cons: Constraints) -> tuple[float, dict[str, float]]:
    """Relevance among jobs that already PASSED the hard filters."""
    parts: dict[str, float] = {}
    tl = job.title.lower()
    terms = _match_terms(cons)
    if terms:
        exact = cons.role and re.search(rf"\b{re.escape(cons.role.lower())}\b", tl)
        parts["role"] = 1.0 if exact else 0.8
    if cons.location_scope in ("STRICT_COUNTRY", "STRICT_CITY"):
        parts["location"] = 1.0
    if cons.experience:
        je = (job.experience or "").lower()
        want = cons.experience.lower()
        if not je:
            parts["experience"] = 0.6
        elif ("0" in want or "entry" in want or "grad" in want) and (
            "entry" in je or "intern" in je
        ):
            parts["experience"] = 1.0
        elif "senior" in want and "senior" in je:
            parts["experience"] = 1.0
        else:
            parts["experience"] = 0.4
    if not parts:
        return 0.6, {}
    score = sum(parts.values()) / len(parts)
    return round(score, 3), {k: round(v, 2) for k, v in parts.items()}


def dedup(jobs: list[JobItem]) -> list[JobItem]:
    by_key: dict[tuple[str, str], JobItem] = {}
    for j in jobs:
        key = (j.company.lower().strip(), re.sub(r"\s+", " ", j.title.lower()).strip())
        if key in by_key:
            for s in j.sources:
                if s not in by_key[key].sources:
                    by_key[key].sources.append(s)
        else:
            by_key[key] = j
    return list(by_key.values())


def validate_and_rank(jobs: list[JobItem], cons: Constraints, limit: int) -> list[JobItem]:
    kept: list[JobItem] = []
    for j in jobs:
        if not job_matches(j, cons):
            continue
        j.match_score, j.match_breakdown = compute_score(j, cons)
        kept.append(j)
    kept.sort(key=lambda x: x.match_score or 0, reverse=True)
    return kept[:limit]


# --------------------------------------------------------------------------- #
# Providers
# --------------------------------------------------------------------------- #
def normalize_greenhouse(raw: dict, company: str) -> JobItem | None:
    title = (raw.get("title") or "").strip()
    url = raw.get("absolute_url") or ""
    if not title or not url:
        return None
    loc = ((raw.get("location") or {}).get("name") or "").strip() or None
    country, city, is_remote, worldwide = normalize_location(loc)
    body = raw.get("content") or ""
    emn, emx, esen, edisp = job_experience_fields(title, body)
    return JobItem(
        id=f"gh-{company}-{raw.get('id')}",
        title=title,
        company=company,
        location=loc,
        country=country,
        city=city,
        employment_type="Internship" if _intern_title(title) else None,
        experience=edisp,
        experience_min=emn,
        experience_max=emx,
        seniority=esen,
        workplace_type="Remote" if is_remote else None,
        remote_worldwide=worldwide,
        skills=extract_skills(body),
        description=summarize(body),
        posted_at=_iso_date(raw.get("updated_at") or raw.get("first_published")),
        source="Greenhouse",
        source_url=url,
        application_url=url,
        sources=["Greenhouse"],
    )


def normalize_lever(raw: dict, company: str) -> JobItem | None:
    title = (raw.get("text") or "").strip()
    url = raw.get("hostedUrl") or raw.get("applyUrl") or ""
    if not title or not url:
        return None
    cats = raw.get("categories") or {}
    loc = (cats.get("location") or "").strip() or None
    country, city, is_remote, worldwide = normalize_location(
        f"{loc or ''} {cats.get('workplaceType') or ''}"
    )
    body = raw.get("descriptionPlain") or raw.get("description") or ""
    wt = (cats.get("workplaceType") or "").title() or ("Remote" if is_remote else None)
    emn, emx, esen, edisp = job_experience_fields(title, body)
    return JobItem(
        id=f"lv-{company}-{raw.get('id')}",
        title=title,
        company=company,
        location=loc,
        country=country,
        city=city,
        employment_type="Internship" if _intern_title(title) else (cats.get("commitment") or None),
        experience=edisp,
        experience_min=emn,
        experience_max=emx,
        seniority=esen,
        workplace_type=wt,
        remote_worldwide=worldwide,
        skills=extract_skills(body),
        description=summarize(body),
        posted_at=_iso_date(raw.get("createdAt")),
        source="Lever",
        source_url=url,
        application_url=url,
        sources=["Lever"],
    )


ADZUNA_CC = {
    "India": "in",
    "United States": "us",
    "United Kingdom": "gb",
    "Germany": "de",
    "Switzerland": "ch",
    "France": "fr",
    "Netherlands": "nl",
    "Canada": "ca",
    "Singapore": "sg",
    "Australia": "au",
    "Spain": "es",
    "Italy": "it",
    "Austria": "at",
    "Belgium": "be",
    "Poland": "pl",
    "Brazil": "br",
    "New Zealand": "nz",
    "South Africa": "za",
    "Mexico": "mx",
}


def normalize_adzuna(raw: dict, cc: str) -> JobItem | None:
    title = (raw.get("title") or "").strip()
    url = raw.get("redirect_url") or ""
    if not title or not url:
        return None
    loc_obj = raw.get("location") or {}
    loc = (loc_obj.get("display_name") or "").strip() or None
    country, city, is_remote, worldwide = normalize_location(loc)
    if country is None:  # trust Adzuna's country endpoint
        country = next((k for k, v in ADZUNA_CC.items() if v == cc), None)
    ct = raw.get("contract_time") or ""
    cty = raw.get("contract_type") or ""
    emp = (
        "Internship"
        if _intern_title(title)
        else "Part-time"
        if ct == "part_time"
        else "Contract"
        if cty == "contract"
        else "Full-time"
        if ct == "full_time"
        else None
    )
    smin, smax = raw.get("salary_min"), raw.get("salary_max")
    salary = None
    if smin and smax and not raw.get("salary_is_predicted", "0") == "1":
        salary = f"{int(smin):,}–{int(smax):,}"
    body = raw.get("description") or ""
    emn, emx, esen, edisp = job_experience_fields(title, body)
    return JobItem(
        id=f"az-{raw.get('id')}",
        title=title,
        company=((raw.get("company") or {}).get("display_name") or "—").strip(),
        location=loc,
        country=country,
        city=city,
        employment_type=emp,
        experience=edisp,
        experience_min=emn,
        experience_max=emx,
        seniority=esen,
        workplace_type="Remote" if is_remote else None,
        remote_worldwide=worldwide,
        salary=salary,
        salary_type="disclosed" if salary else None,
        skills=extract_skills(body),
        description=summarize(body),
        posted_at=_iso_date(raw.get("created")),
        source="Adzuna",
        source_url=url,
        application_url=url,
        sources=["Adzuna"],
    )


async def _fetch_greenhouse(c: httpx.AsyncClient, token: str, name: str) -> list[JobItem]:
    r = await c.get(f"https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true")
    r.raise_for_status()
    return [j for j in (normalize_greenhouse(x, name) for x in r.json().get("jobs", [])) if j]


async def _fetch_lever(c: httpx.AsyncClient, handle: str, name: str) -> list[JobItem]:
    r = await c.get(f"https://api.lever.co/v0/postings/{handle}?mode=json")
    r.raise_for_status()
    data = r.json()
    return [
        j for j in (normalize_lever(x, name) for x in (data if isinstance(data, list) else [])) if j
    ]


async def _fetch_adzuna(
    c: httpx.AsyncClient, cc: str, cons: Constraints, app_id: str, app_key: str
) -> list[JobItem]:
    what = cons.role or cons.raw
    where = cons.city or cons.country or ""
    params = {
        "app_id": app_id,
        "app_key": app_key,
        "results_per_page": 50,
        "content-type": "application/json",
        "what": what[:100],
    }
    if where:
        params["where"] = where
    if cons.employment_type == "Full-time":
        params["full_time"] = 1
    elif cons.employment_type == "Part-time":
        params["part_time"] = 1
    elif cons.employment_type == "Contract":
        params["contract"] = 1
    r = await c.get(f"https://api.adzuna.com/v1/api/jobs/{cc}/search/1", params=params)
    r.raise_for_status()
    return [j for j in (normalize_adzuna(x, cc) for x in r.json().get("results", [])) if j]


def _adzuna_country_codes(cons: Constraints) -> list[str]:
    if cons.location_scope == "STRICT_COUNTRY" and cons.country in ADZUNA_CC:
        return [ADZUNA_CC[cons.country]]
    if cons.location_scope == "STRICT_CITY" and cons.country in ADZUNA_CC:
        return [ADZUNA_CC[cons.country]]
    if cons.location_scope == "WORLDWIDE":
        return ["gb", "us", "in", "de", "au", "ca"]
    return ["us", "gb", "in"]  # ANY -> a few large markets


async def gather_jobs(cons: Constraints) -> tuple[list[JobItem], list[SourceStatus]]:
    jobs: list[JobItem] = []
    sources: list[SourceStatus] = []
    _s = get_settings()
    az_id, az_key = _s.adzuna_app_id, _s.adzuna_app_key

    async with httpx.AsyncClient(
        timeout=12, headers={"user-agent": _UA}, follow_redirects=True
    ) as client:
        gh = await asyncio.gather(
            *(_fetch_greenhouse(client, t, n) for t, n in GREENHOUSE_BOARDS), return_exceptions=True
        )
        lv = await asyncio.gather(
            *(_fetch_lever(client, h, n) for h, n in LEVER_BOARDS), return_exceptions=True
        )
        az_results: list = []
        codes: list[str] = []
        if az_id and az_key:
            codes = _adzuna_country_codes(cons)
            az_results = await asyncio.gather(
                *(_fetch_adzuna(client, cc, cons, az_id, az_key) for cc in codes),
                return_exceptions=True,
            )

    gh_ok = sum(1 for r in gh if not isinstance(r, Exception))
    lv_ok = sum(1 for r in lv if not isinstance(r, Exception))
    for r in gh + lv:
        if not isinstance(r, Exception):
            jobs.extend(r)
    sources.append(
        SourceStatus(
            source="Greenhouse",
            status="ok" if gh_ok else "error",
            count=gh_ok,
            note=f"{gh_ok}/{len(GREENHOUSE_BOARDS)} boards reachable",
        )
    )
    sources.append(
        SourceStatus(
            source="Lever",
            status="ok" if lv_ok else "error",
            count=lv_ok,
            note=f"{lv_ok}/{len(LEVER_BOARDS)} boards reachable",
        )
    )
    if az_id and az_key:
        az_ok = sum(1 for r in az_results if not isinstance(r, Exception))
        for r in az_results:
            if not isinstance(r, Exception):
                jobs.extend(r)
        sources.append(
            SourceStatus(
                source="Adzuna",
                status="ok" if az_ok else "error",
                count=az_ok,
                note=f"{az_ok}/{len(codes)} country markets queried",
            )
        )
    else:
        sources.append(
            SourceStatus(
                source="Adzuna",
                status="error",
                count=0,
                note="not configured — set ADZUNA_APP_ID / ADZUNA_APP_KEY for broad, "
                "country-scoped coverage (free key at developer.adzuna.com)",
            )
        )
    return jobs, sources


@router.post("/search", response_model=JobSearchResponse)
async def search_jobs(req: SearchRequest) -> JobSearchResponse:
    q = req.query.strip()
    if not q and (req.roles or req.locations):  # legacy compatibility
        q = " ".join([*req.roles, *req.locations, *(req.keywords or [])]).strip()
    cons = parse_query(q)
    # An explicit experience selection (e.g. the UI's "0–2 years" filter) is a
    # hard constraint and overrides whatever the free-text query implied.
    if req.experience:
        emn, emx, esen, edisp = exp_bounds(req.experience)
        if emn is not None or emx is not None or esen is not None:
            cons.exp_min, cons.exp_max, cons.seniority, cons.experience = emn, emx, esen, edisp
    raw, sources = await gather_jobs(cons)
    deduped = dedup(raw)
    valid = validate_and_rank(deduped, cons, req.limit)
    return JobSearchResponse(
        jobs=valid,
        sources=sources,
        constraints=cons,
        total_fetched=len(raw),
        total_after_filter=len(valid),
    )
