"""Built-in agent templates.

These expose the existing specialized backends (job search, research, PhD, scholarships,
SOP, resume, interview) — plus a few generic ones — as ready-to-instantiate agents. A
template is NOT a persisted agent; creating from a template writes a new owner-scoped
`AgentRow` seeded with these defaults (name/purpose/tools/character), then the user edits it.

`route` names the existing capability the template maps to, so later phases can dispatch a
run to the right backend (jobs/phd/scholarships/sop/resume/research) rather than duplicating it.
"""

from __future__ import annotations

BUILTIN_TEMPLATES: list[dict] = [
    {
        "id": "job-search",
        "name": "Job Search",
        "route": "jobs",
        "description": "Find and rank real job openings from multiple sources.",
        "purpose": "Find and rank matching job opportunities against the user's profile.",
        "character_id": "peter",
        "personality": "Focused",
        "tools": ["job_search", "web_search", "resume_parser"],
        "memory_config": {"scopes": ["candidate_profile", "saved_jobs", "search_history"]},
    },
    {
        "id": "research",
        "name": "Research",
        "route": "research",
        "description": "Literature discovery and analysis with grounded citations.",
        "purpose": "Discover, read and synthesize research with cited evidence.",
        "character_id": "rory",
        "personality": "Analytical",
        "tools": ["web_search", "rag_search", "graph_search", "wikipedia"],
        "memory_config": {"scopes": ["papers", "findings"]},
    },
    {
        "id": "resume-optimizer",
        "name": "Resume Optimizer",
        "route": "resume",
        "description": "Tailor and strengthen a resume for a target role.",
        "purpose": "Optimize the user's resume for a specific job description.",
        "character_id": "ivy",
        "personality": "Analytical",
        "tools": ["resume_parser", "web_search"],
        "memory_config": {"scopes": ["resume", "target_roles"]},
    },
    {
        "id": "sop-builder",
        "name": "SOP Builder",
        "route": "sop",
        "description": "Draft and refine statements of purpose.",
        "purpose": "Draft a tailored statement of purpose for an application.",
        "character_id": "theo",
        "personality": "Concise",
        "tools": ["web_search"],
        "memory_config": {"scopes": ["profile", "programs"]},
    },
    {
        "id": "scholarship-finder",
        "name": "Scholarship Finder",
        "route": "scholarships",
        "description": "Find scholarships matching the user's eligibility.",
        "purpose": "Find and rank scholarships the user is eligible for.",
        "character_id": "coco",
        "personality": "Friendly",
        "tools": ["web_search"],
        "memory_config": {"scopes": ["student_profile", "saved_scholarships"]},
    },
    {
        "id": "phd-finder",
        "name": "PhD Finder",
        "route": "phd",
        "description": "Find funded PhD positions by country, area and funding.",
        "purpose": "Find and rank funded PhD positions against the user's profile.",
        "character_id": "luna",
        "personality": "Analytical",
        "tools": ["web_search"],
        "memory_config": {"scopes": ["profile", "saved_positions"]},
    },
    {
        "id": "interview-coach",
        "name": "Interview Coach",
        "route": "research",
        "description": "Prepare for interviews with tailored questions and feedback.",
        "purpose": "Coach the user through interview preparation for a target role.",
        "character_id": "milo",
        "personality": "Friendly",
        "tools": ["web_search"],
        "memory_config": {"scopes": ["target_roles", "practice_history"]},
    },
    {
        "id": "data-analyst",
        "name": "Data Analyst",
        "route": "research",
        "description": "Analyze data and produce structured findings.",
        "purpose": "Analyze provided data and produce a structured analysis.",
        "character_id": "echo",
        "personality": "Analytical",
        "tools": ["python_exec", "data_analysis", "calculator"],
        "memory_config": {"scopes": ["datasets", "analyses"]},
    },
    {
        "id": "sales-research",
        "name": "Sales Research",
        "route": "research",
        "description": "Research prospects and summarize opportunities.",
        "purpose": "Research prospects and surface the best opportunities.",
        "character_id": "nova",
        "personality": "Curious",
        "tools": ["web_search", "http_tool"],
        "memory_config": {"scopes": ["prospects", "notes"]},
    },
    {
        "id": "email-assistant",
        "name": "Email Assistant",
        "route": "research",
        "description": "Draft and organize email on the user's behalf.",
        "purpose": "Draft and organize email, requiring approval before sending.",
        "character_id": "momo",
        "personality": "Concise",
        "tools": ["web_search"],
        "memory_config": {"scopes": ["contacts", "threads"]},
        "approval_policy": {"require_approval": True},
    },
]

TEMPLATE_MAP: dict[str, dict] = {t["id"]: t for t in BUILTIN_TEMPLATES}
