# ROADMAP v3 — Governed Execution OS (10 days)

Evolve from "plan → research → answer" into a **governed action OS**: the LLM
*requests* an action; the OS validates, checks policy, gates on approval,
executes, **verifies**, persists an artifact, emits events, and continues the
mission. Real work (PDFs, job search, bookings) becomes governed **tools**, never
special cases.

## The invariant (never bypassed)

```
LLM request → Tool Registry → Input validation → Policy (risk) →
Approval (if required) → Budget check → Idempotency check →
Executor → Verifier → Persist (execution + artifact) → Event → Mission continues
```

## Design principles (carried from v2)

Depth over breadth · real numbers only · tests every day · reuse existing
architecture (registry, recovery, budgets, SSE, DB) · minimum new infra ·
**no real-world side effect without explicit approval** · sandbox vs live mode.

## Exists vs missing

| Area | Exists | To add |
| --- | --- | --- |
| Tool registry | `Tool`, `default_registry`, specs | risk_level, requires_approval, retry/verify metadata |
| Executor | tool dispatch | **governed ToolExecutor** (the pipeline above) |
| Policy | self-improving strategy engine | **action firewall** (ALLOW/DENY/REQUIRE_APPROVAL by risk) |
| Approval | — | `WAITING_FOR_APPROVAL` state + Approval model + resume |
| Persistence | Mission/Task + meta JSON | ToolExecution + Checkpoint + idempotency keys |
| Recovery/Budget | full | failure classifier + retryability classes |
| Verification | — | Verifier abstraction (pdf/reservation/url/…) |
| Artifacts | — | Artifact store + API + UI panel |
| Connectors | — | JobSearchProvider, hotel provider (sandbox) |
| Frontend | mission control UI | Jobs page, Hotels page, Approval card, Artifacts panel, Live/Sandbox badge |

## Sidebar additions (distinct entry points, as requested)

`Jobs` and `Hotels` become their own nav items — each launches a mission of that
**task type** (`job.search`, `hotel.book`). Plus `Artifacts` and `Approvals`.

---

## 10-day plan (daily commits, ~5–8/day; tests last; CI green)

**Day 1 — Governed tool metadata + ToolExecutor.**
Extend `Tool` with `risk_level`, `requires_approval`, `retry_policy`,
`idempotency`, `verification`. Build `app/exec/executor.py`: lookup → validate
args vs schema → (policy/budget/approval hooks stubbed) → execute → structured
`ToolResult`. Reuse the registry. Tests: schema validation, unknown tool, result
shape.

**Day 2 — Action firewall / policy.**
`app/exec/policy.py`: risk categories (LOW/MED/HIGH/CRITICAL) → ALLOW / DENY /
REQUIRE_APPROVAL; CRITICAL blocked by default; central config, no scattered
safety checks. Wire into the executor. Tests: each risk → decision, override
config.

**Day 3 — Approval gate + resume.**
Add `WAITING_FOR_APPROVAL` to the mission state machine; `Approval` model
(persisted: mission, task, tool, args, risk, status). API `POST
/missions/{id}/approve|deny`. Resume **exactly where it paused** (not restart).
Tests: high-risk → pause → approve → resume; deny → replan/terminate; approval
survives restart.

**Day 4 — Checkpoints + idempotency + failure classes.**
`ToolExecution` rows (input/output/status/duration/retry). Idempotency key =
`mission:task:attempt`; a NON_RETRYABLE tool that timed out is **not** blindly
re-run. `FailureType` classifier (timeout/rate_limit/auth/verification/…). Feed
the recovery engine. Tests: duplicate suppression, checkpoint resume, classifier.

**Day 5 — Verification + Artifact store.**
`Verifier` abstraction (returns VERIFIED / FAILED with reasons — HTTP 200 ≠
success). `Artifact` model (id, mission, type, filename, path, mime, size,
checksum, created_at). API list. Tests: verifier pass/fail, artifact roundtrip.

**Day 6 — `pdf.create` + "Download report".**
First real tool: local PDF (reportlab/fpdf, no paid API) → PDF verifier (file
exists, valid, page count, content) → artifact persisted. **Wire a Download-PDF
on the existing agent/mission result** (the immediate want). Tests: pdf created +
verified + artifact stored.

**Day 7 — `job.search` connector architecture.**
`JobSearchProvider` interface (`search`/`normalize`/`health_check`); normalized
`Job` schema; a **sandbox provider** (deterministic mock) + one permitted real
source; only permitted access, no CAPTCHA/anti-bot bypass; unreachable →
`WAITING_FOR_HUMAN`. Tests: normalization, health check.

**Day 8 — Dedupe + explainable match + job report.**
Dedup by normalized company/title/location + description similarity (not exact
string). Explainable match score vs a user profile (honest features, documented;
no fake precision). Report → `pdf.create` artifact. Tests: dedupe merges 3
sources → 1, match score + explanation, report artifact.

**Day 9 — `hotel.book` (HIGH-risk, approval-gated) + Sandbox/Live mode.**
Booking tool through the **full pipeline** in SANDBOX (mock provider, no side
effect): search → rank → availability → **approval required** → book → verify
confirmation → store. `SANDBOX`/`LIVE` mode flag + rule: never a real action in
sandbox. Tests: booking requires approval, sandbox has no side effect, verify
confirmation, no blind retry on booking.

**Day 10 — Frontend + e2e + release.**
Jobs page, Hotels page (sidebar), **Approval card**, **Artifacts panel +
Download**, Live/Sandbox badge, new mission events (`TOOL_REQUESTED`,
`APPROVAL_REQUIRED`, `VERIFICATION_PASSED`, `ARTIFACT_CREATED`) rendered in the
existing control-plane UI. Full e2e smoke (research → PDF → verified → artifact →
complete). Docs + tag **v3.0.0**.

## New files (indicative)
`app/exec/{__init__,executor,policy,verify,idempotency,failures}.py`,
`app/exec/tools/{pdf_create,job_search,hotel_book}.py`,
`app/artifacts/{models,store,api}.py`, `app/api/{approvals,artifacts,jobs}.py`,
`frontend/app/{jobs,hotels,artifacts}/page.tsx`, `frontend/app/components/ApprovalCard.tsx`.

## Files modified
`app/tools/registry.py` (metadata), `app/missions/state.py` (+approval state),
`app/missions/models.py` (+ToolExecution/Approval/Artifact), `app/missions/runtime.py`
(route task execution through the governed executor), `app/api/main.py` (mount routers),
`frontend/app/components/Sidebar.tsx`.

## Risks
State-machine change touches many tests (add approval transitions carefully) ·
real external providers need keys/permitted access (default to sandbox) · PDF/ML
libs must stay CI-safe (graceful skip) · idempotency correctness is the highest-stakes
piece (test hard).

## Definition of done
"Research X and make a PDF" → mission → plan → research → analysis → critic →
`pdf.create` → verified → artifact persisted → **Download** in UI → completed →
evaluated; survives a restart; high-risk tools pause for approval; no ungoverned
side effects.
