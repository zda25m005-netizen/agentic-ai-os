"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import "../../../scholarships.css";
import Icon from "../../../components/Icon";
import ScholarshipCard from "../../../components/scholarships/ScholarshipCard";
import ScholarshipDrawer from "../../../components/scholarships/ScholarshipDrawer";
import StudentProfilePanel from "../../../components/scholarships/StudentProfilePanel";
import {
  searchByQuery, searchByFilters, filtersFromIntent, listSaved, saveScholarship, removeSaved,
  getProfile,
  COUNTRY_OPTIONS, DEGREE_OPTIONS, FUNDING_OPTIONS, FIELD_OPTIONS, TYPE_OPTIONS, INTAKE_OPTIONS,
  EXAMPLES, degreeLabel, fundingLabel,
  Scholarship, SearchResult, FilterSpec, StudentProfile,
} from "../../../lib/scholarshipsApi";
import { getResume } from "../../../lib/resumeApi";

type Phase = "empty" | "searching" | "results";
type Sort = "match" | "funding" | "eligibility";
const STEPS = ["Understanding request", "Searching official sources", "Checking eligibility", "Ranking matches"];

export default function ScholarshipsPage() {
  const [query, setQuery] = useState("");
  const [phase, setPhase] = useState<Phase>("empty");
  const [step, setStep] = useState(0);
  const [result, setResult] = useState<SearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<FilterSpec | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [sort, setSort] = useState<Sort>("match");
  const [tab, setTab] = useState<"all" | "saved">("all");
  const [savedList, setSavedList] = useState<Scholarship[]>([]);
  const [open, setOpen] = useState<Scholarship | null>(null);
  const [hasResume, setHasResume] = useState(false);
  const [onlyEligible, setOnlyEligible] = useState(false);
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { listSaved().then(setSavedList).catch(() => {}); }, []);
  useEffect(() => { getResume().then((r) => setHasResume(!!r.exists)).catch(() => {}); }, []);
  useEffect(() => { getProfile().then(setProfile).catch(() => {}); }, []);
  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);

  const savedIds = useMemo(() => new Set(savedList.map((s) => s.id)), [savedList]);

  const begin = () => {
    setPhase("searching"); setError(null); setStep(0);
    timer.current = setInterval(() => setStep((s) => Math.min(s + 1, 3)), 500);
  };
  const finish = (r: SearchResult) => {
    if (timer.current) clearInterval(timer.current);
    setResult(r); setActive(filtersFromIntent(r.intent)); setSort("match"); setPhase("results");
  };
  const fail = (e: unknown) => {
    if (timer.current) clearInterval(timer.current);
    setError(e instanceof Error ? e.message : "Search failed"); setPhase("results");
  };

  const runQuery = async (q: string) => {
    if (!q.trim() || phase === "searching") return;
    setQuery(q); begin();
    try { finish(await searchByQuery(q.trim(), hasResume)); } catch (e) { fail(e); }
  };
  const applyFilters = async (next: FilterSpec) => {
    setActive(next);
    if (phase === "searching") return;
    begin();
    try { finish(await searchByFilters(next, hasResume)); } catch (e) { fail(e); }
  };

  const toggleCountry = (c: string) => {
    const cur = active?.countries || [];
    const next = cur.includes(c) ? cur.filter((x) => x !== c) : [...cur, c];
    applyFilters({ ...(active || {}), countries: next });
  };
  const setF = (key: keyof FilterSpec, val: string) => {
    const cur = active || {};
    applyFilters({ ...cur, [key]: (cur as Record<string, unknown>)[key] === val ? null : val });
  };
  const removeChip = (key: keyof FilterSpec, val?: string) => {
    const next: FilterSpec = { ...(active || {}) };
    if (key === "countries" && val) next.countries = (next.countries || []).filter((c) => c !== val);
    else if (key === "no_ielts") next.no_ielts = false;
    else (next as Record<string, unknown>)[key] = null;
    applyFilters(next);
  };
  const clearAll = () => applyFilters({ countries: [] });

  const onSave = async (s: Scholarship) => {
    if (savedIds.has(s.id)) { await removeSaved(s.id); setSavedList((l) => l.filter((x) => x.id !== s.id)); }
    else { await saveScholarship(s); setSavedList((l) => [s, ...l]); }
  };

  // Saving/prefilling the profile recomputes eligibility → re-run the last search.
  const onProfileChange = (p: StudentProfile) => {
    setProfile(p);
    if (phase === "results" && !error) applyFilters(active || {});
  };

  const all = result?.scholarships ?? [];
  const base = tab === "saved" ? savedList : all;
  const visible = useMemo(() => {
    let list = onlyEligible ? base.filter((s) => ["eligible", "likely"].includes(s.eligibility_status || "")) : base;
    list = [...list].sort((a, b) => {
      if (sort === "funding") return (b.funding_type === "fully_funded" ? 1 : 0) - (a.funding_type === "fully_funded" ? 1 : 0);
      if (sort === "eligibility") {
        const rank = (x: string | null) => ({ eligible: 3, likely: 2, unclear: 1, not_eligible: 0 }[x || "unclear"] ?? 1);
        return rank(b.eligibility_status) - rank(a.eligibility_status);
      }
      return (b.match_score ?? 0) - (a.match_score ?? 0);
    });
    return list;
  }, [base, sort, onlyEligible]);

  const sm = result?.summary ?? {};
  const chips = active ? [
    ...(active.field ? [{ k: "field" as const, label: active.field }] : []),
    ...(active.degree ? [{ k: "degree" as const, label: degreeLabel(active.degree) }] : []),
    ...(active.funding ? [{ k: "funding" as const, label: fundingLabel(active.funding) }] : []),
    ...(active.intake ? [{ k: "intake" as const, label: active.intake }] : []),
    ...(active.nationality ? [{ k: "nationality" as const, label: `${active.nationality} students` }] : []),
    ...(active.scholarship_type ? [{ k: "scholarship_type" as const, label: active.scholarship_type }] : []),
    ...(active.no_ielts ? [{ k: "no_ielts" as const, label: "No IELTS" }] : []),
    ...((active.countries || []).map((c) => ({ k: "countries" as const, label: c, val: c }))),
  ] : [];

  return (
    <div className="sch">
      <div className="wrap">
        <div className="head">
          <div>
            <h1 className="h1">Scholarship Finder</h1>
            <p className="h-sub">Find scholarships matched to your study goals, eligibility and funding requirements.</p>
          </div>
        </div>

        <StudentProfilePanel profile={profile} onChange={onProfileChange} hasResume={hasResume} />

        <div className="qlabel">What are you looking for?</div>
        <div className="box">
          <input className="qinput" placeholder="Try: Fully funded Master's scholarships in Switzerland for Indian students"
            value={query} onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter") runQuery(query); }} />
          <button className="btn primary" onClick={() => runQuery(query)} disabled={!query.trim() || phase === "searching"}>
            {phase === "searching" ? "Searching…" : <>Search <Icon name="arrowRight" size={14} sw={2} /></>}
          </button>
        </div>

        <div className="countries">
          {COUNTRY_OPTIONS.map((c) => (
            <button key={c} className={`cbtn ${(active?.countries || []).includes(c) ? "on" : ""}`}
              onClick={() => toggleCountry(c)}>{c}</button>
          ))}
        </div>

        <div className="ctrl-row">
          <button className={`btn ghost sm ${showFilters ? "saved" : ""}`} onClick={() => setShowFilters((v) => !v)}>
            <Icon name="filter" size={13} /> Filters
          </button>
          {hasResume && <span className="resume-note"><Icon name="check" size={12} style={{ color: "var(--hgreen)" }} /> Personalized by your resume</span>}
          <span style={{ flex: 1 }} />
          {phase === "empty" && (
            <div className="examples">
              {EXAMPLES.map((ex) => <button key={ex} className="ex" onClick={() => runQuery(ex)}>{ex}</button>)}
            </div>
          )}
        </div>

        {showFilters && (
          <div className="fpanel">
            <FilterGroup label="Degree" options={DEGREE_OPTIONS} render={degreeLabel}
              value={active?.degree} onPick={(v) => setF("degree", v)} />
            <FilterGroup label="Funding" options={FUNDING_OPTIONS} render={fundingLabel}
              value={active?.funding} onPick={(v) => setF("funding", v)} />
            <FilterGroup label="Field" options={FIELD_OPTIONS} value={active?.field}
              onPick={(v) => setF("field", v)} />
            <FilterGroup label="Type" options={TYPE_OPTIONS} value={active?.scholarship_type}
              onPick={(v) => setF("scholarship_type", v)} />
            <FilterGroup label="Intake" options={INTAKE_OPTIONS} value={active?.intake}
              onPick={(v) => setF("intake", v)} />
            <button className="btn ghost sm" onClick={clearAll} style={{ alignSelf: "center" }}>Clear all</button>
          </div>
        )}

        {phase === "searching" && (
          <div className="progress">
            <div className="sec-h" style={{ margin: "0 0 12px" }}>Searching scholarships</div>
            {STEPS.map((label, i) => (
              <div className={`pstep ${i < step ? "done" : i === step ? "active" : "pending"}`} key={label}>
                <span className="pdot">{i < step ? <Icon name="check" size={14} /> : i === step ? <span className="spin" /> : <span className="idle" />}</span>
                <span className="plabel">{label}</span>
              </div>
            ))}
          </div>
        )}

        {phase === "results" && (
          <>
            <div className="results-head">
              <div>
                <div className="rh-sum">
                  {error ? "Search error"
                    : `${all.length} scholarship${all.length === 1 ? "" : "s"} found${active?.countries?.length ? ` in ${active.countries.join(", ")}` : ""}`}
                </div>
                {!error && chips.length > 0 && (
                  <div className="rh-chips">
                    {chips.map((ch) => (
                      <span className="cchip removable" key={`${ch.k}-${ch.label}`}>
                        {ch.label}
                        <button className="cchip-x" onClick={() => removeChip(ch.k, (ch as { val?: string }).val)}
                          aria-label={`Remove ${ch.label}`}><Icon name="x" size={11} /></button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="rh-actions">
                <div className="seg">
                  <button className={tab === "all" ? "on" : ""} onClick={() => setTab("all")}>Results</button>
                  <button className={tab === "saved" ? "on" : ""} onClick={() => setTab("saved")}>
                    Saved{savedList.length ? ` · ${savedList.length}` : ""}
                  </button>
                </div>
              </div>
            </div>

            {!error && result?.profile_incomplete && tab === "all" && (
              <div className="incomplete">
                <Icon name="alert" size={14} style={{ color: "#E0B457" }} />
                Add your profile above to check eligibility against each scholarship&apos;s real requirements — right now they show as “verify”.
              </div>
            )}

            {!error && tab === "all" && all.length > 0 && (
              <>
                <div className="summary">
                  <div className="scard2"><div className="val">{all.length}</div><div className="lbl">Scholarships</div></div>
                  <div className="scard2"><div className="val">{sm.fully_funded ?? 0}</div><div className="lbl">Fully funded</div></div>
                  <div className="scard2"><div className="val">{sm.eligible ?? 0}</div><div className="lbl">Likely eligible</div></div>
                  <div className="scard2"><div className="val">{(result?.country_facets ?? []).length}</div><div className="lbl">Countries</div></div>
                </div>
                {(result?.country_facets ?? []).length > 1 && (
                  <div className="facets">
                    {result!.country_facets.map((f) => (
                      <button key={f.country} className={`qchip ${(active?.countries || []).includes(f.country) ? "on" : ""}`}
                        onClick={() => toggleCountry(f.country)}>{f.country} · {f.count}</button>
                    ))}
                  </div>
                )}
                <div className="toolbar">
                  <button className={`qchip ${onlyEligible ? "on" : ""}`} onClick={() => setOnlyEligible((v) => !v)}>Eligible for you</button>
                  <span style={{ flex: 1 }} />
                  <select className="tb-sort" value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
                    <option value="match">Best match</option>
                    <option value="funding">Highest funding</option>
                    <option value="eligibility">Eligibility</option>
                  </select>
                </div>
              </>
            )}

            {error ? (
              <div className="empty"><b>Couldn&apos;t reach the scholarship service</b><p>{error}. Make sure the backend is running.</p></div>
            ) : visible.length === 0 ? (
              <div className="empty">
                <b>{tab === "saved" ? "No saved scholarships yet" : "No scholarships found"}</b>
                <p>{tab === "saved" ? "Use Save on any scholarship to track it here."
                  : "Try removing the funding filter, adding more countries, or broadening the field — your hard constraints are never silently relaxed."}</p>
              </div>
            ) : (
              <div className="results">
                {visible.map((s) => (
                  <ScholarshipCard key={s.id} s={s} saved={savedIds.has(s.id)} onOpen={setOpen} onSave={onSave} />
                ))}
              </div>
            )}

            {result && (
              <div className="srcline">
                {result.sources.map((s) => (
                  <span key={s.source} className={`srctag ${s.status}`}><span className="d" />{s.source}{s.note ? ` — ${s.note}` : ""}</span>
                ))}
                <span className="srctag note">Curated catalog of official programs — verify each on its official page.</span>
              </div>
            )}
          </>
        )}
      </div>

      {open && <ScholarshipDrawer s={open} saved={savedIds.has(open.id)} onClose={() => setOpen(null)} onSave={onSave} />}
    </div>
  );
}

function FilterGroup({ label, options, value, onPick, render }: {
  label: string; options: string[]; value?: string | null; onPick: (v: string) => void; render?: (v: string) => string;
}) {
  return (
    <div className="fgroup">
      <div className="fg-label">{label}</div>
      <div className="fg-opts">
        {options.map((o) => (
          <button key={o} className={`qchip ${value === o ? "on" : ""}`} onClick={() => onPick(o)}>
            {render ? render(o) : o}
          </button>
        ))}
      </div>
    </div>
  );
}
