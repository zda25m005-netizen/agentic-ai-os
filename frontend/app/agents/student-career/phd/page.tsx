"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import "../../../scholarships.css";
import Icon from "../../../components/Icon";
import PhdCard from "../../../components/phd/PhdCard";
import PhdDrawer from "../../../components/phd/PhdDrawer";
import StudentProfilePanel from "../../../components/scholarships/StudentProfilePanel";
import { getProfile, StudentProfile } from "../../../lib/scholarshipsApi";
import {
  searchByQuery, searchByFilters, filtersFromIntent, listSaved, savePhd, removeSaved,
  COUNTRY_OPTIONS, FIELD_OPTIONS, FUNDING_OPTIONS, OPP_OPTIONS, INTAKE_OPTIONS, EXAMPLES,
  fundingLabel, oppLabel,
  PhdOpportunity, PhdSearchResult, PhdFilterSpec,
} from "../../../lib/phdApi";

type Phase = "empty" | "searching" | "results";
const STEPS = ["Understanding request", "Searching sources", "Checking eligibility", "Ranking matches"];

export default function PhdPage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [phase, setPhase] = useState<Phase>("empty");
  const [step, setStep] = useState(0);
  const [result, setResult] = useState<PhdSearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [active, setActive] = useState<PhdFilterSpec | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [tab, setTab] = useState<"all" | "saved">("all");
  const [savedList, setSavedList] = useState<PhdOpportunity[]>([]);
  const [open, setOpen] = useState<PhdOpportunity | null>(null);
  const [profile, setProfile] = useState<StudentProfile | null>(null);
  const [hasResume] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { listSaved().then(setSavedList).catch(() => {}); getProfile().then(setProfile).catch(() => {}); }, []);
  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);
  const savedIds = useMemo(() => new Set(savedList.map((s) => s.id)), [savedList]);

  const begin = () => { setPhase("searching"); setError(null); setStep(0); timer.current = setInterval(() => setStep((s) => Math.min(s + 1, 3)), 500); };
  const finish = (r: PhdSearchResult) => { if (timer.current) clearInterval(timer.current); setResult(r); setActive(filtersFromIntent(r.intent)); setTab("all"); setPhase("results"); };
  const fail = (e: unknown) => { if (timer.current) clearInterval(timer.current); setError(e instanceof Error ? e.message : "Search failed"); setPhase("results"); };

  const runQuery = async (q: string) => { if (!q.trim() || phase === "searching") return; setQuery(q); begin(); try { finish(await searchByQuery(q.trim())); } catch (e) { fail(e); } };
  const applyFilters = async (next: PhdFilterSpec) => { setActive(next); if (phase === "searching") return; begin(); try { finish(await searchByFilters(next)); } catch (e) { fail(e); } };
  const toggleCountry = (c: string) => { const cur = active?.countries || []; applyFilters({ ...(active || {}), countries: cur.includes(c) ? cur.filter((x) => x !== c) : [...cur, c] }); };
  const setF = (k: keyof PhdFilterSpec, v: string) => { const cur = active || {}; applyFilters({ ...cur, [k]: (cur as Record<string, unknown>)[k] === v ? null : v }); };
  const removeChip = (k: keyof PhdFilterSpec, val?: string) => { const next: PhdFilterSpec = { ...(active || {}) }; if (k === "countries" && val) next.countries = (next.countries || []).filter((c) => c !== val); else (next as Record<string, unknown>)[k] = null; applyFilters(next); };

  const onSave = async (o: PhdOpportunity) => {
    if (savedIds.has(o.id)) { await removeSaved(o.id); setSavedList((l) => l.filter((x) => x.id !== o.id)); }
    else { await savePhd(o); setSavedList((l) => [o, ...l]); }
  };
  const onProfileChange = (p: StudentProfile) => { setProfile(p); if (phase === "results" && !error) applyFilters(active || {}); };
  const writeSop = (o: PhdOpportunity) => router.push(`/agents/student-career/sop?phd=${encodeURIComponent(o.id)}`);

  const all = result?.opportunities ?? [];
  const visible = tab === "saved" ? savedList : all;
  const sm = result?.summary ?? {};
  const chips = active ? [
    ...(active.field ? [{ k: "field" as const, label: active.field }] : []),
    ...(active.funding ? [{ k: "funding" as const, label: fundingLabel(active.funding) }] : []),
    ...(active.opportunity_type ? [{ k: "opportunity_type" as const, label: oppLabel(active.opportunity_type) }] : []),
    ...(active.intake ? [{ k: "intake" as const, label: active.intake }] : []),
    ...(active.nationality ? [{ k: "nationality" as const, label: `${active.nationality} students` }] : []),
    ...((active.countries || []).map((c) => ({ k: "countries" as const, label: c, val: c }))),
  ] : [];

  return (
    <div className="sch">
      <div className="wrap">
        <div className="head">
          <h1 className="h1">PhD Finder</h1>
          <p className="h-sub">Discover PhD programs, funded positions and research opportunities matched to your research interests.</p>
        </div>

        <StudentProfilePanel profile={profile} onChange={onProfileChange} hasResume={hasResume} />

        <div className="qlabel">What research opportunity are you looking for?</div>
        <div className="box">
          <input className="qinput" placeholder="Search PhD positions, programs, supervisors or research areas..."
            value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") runQuery(query); }} />
          <button className="btn primary" onClick={() => runQuery(query)} disabled={!query.trim() || phase === "searching"}>
            {phase === "searching" ? "Searching…" : <>Search <Icon name="arrowRight" size={14} sw={2} /></>}
          </button>
        </div>

        <div className="countries">
          {COUNTRY_OPTIONS.map((c) => <button key={c} className={`cbtn ${(active?.countries || []).includes(c) ? "on" : ""}`} onClick={() => toggleCountry(c)}>{c}</button>)}
        </div>
        <div className="ctrl-row">
          <button className={`btn ghost sm ${showFilters ? "saved" : ""}`} onClick={() => setShowFilters((v) => !v)}><Icon name="filter" size={13} /> Filters</button>
          <span style={{ flex: 1 }} />
          {phase === "empty" && <div className="examples">{EXAMPLES.map((ex) => <button key={ex} className="ex" onClick={() => runQuery(ex)}>{ex}</button>)}</div>}
        </div>

        {showFilters && (
          <div className="fpanel">
            <FG label="Field" options={FIELD_OPTIONS} value={active?.field} onPick={(v) => setF("field", v)} />
            <FG label="Funding" options={FUNDING_OPTIONS} render={fundingLabel} value={active?.funding} onPick={(v) => setF("funding", v)} />
            <FG label="Type" options={OPP_OPTIONS} render={oppLabel} value={active?.opportunity_type} onPick={(v) => setF("opportunity_type", v)} />
            <FG label="Intake" options={INTAKE_OPTIONS} value={active?.intake} onPick={(v) => setF("intake", v)} />
            <button className="btn ghost sm" onClick={() => applyFilters({ countries: [] })} style={{ alignSelf: "center" }}>Clear all</button>
          </div>
        )}

        {phase === "searching" && (
          <div className="progress">
            <div className="sec-h" style={{ margin: "0 0 12px" }}>Searching PhD opportunities</div>
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
                <div className="rh-sum">{error ? "Search error" : `${all.length} PhD ${all.length === 1 ? "opportunity" : "opportunities"} found${active?.countries?.length ? ` in ${active.countries.join(", ")}` : ""}`}</div>
                {!error && chips.length > 0 && (
                  <div className="rh-chips">
                    {chips.map((ch) => (
                      <span className="cchip removable" key={`${ch.k}-${ch.label}`}>{ch.label}
                        <button className="cchip-x" onClick={() => removeChip(ch.k, (ch as { val?: string }).val)} aria-label={`Remove ${ch.label}`}><Icon name="x" size={11} /></button>
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <div className="rh-actions"><div className="seg">
                <button className={tab === "all" ? "on" : ""} onClick={() => setTab("all")}>Results</button>
                <button className={tab === "saved" ? "on" : ""} onClick={() => setTab("saved")}>Saved{savedList.length ? ` · ${savedList.length}` : ""}</button>
              </div></div>
            </div>

            {!error && result?.profile_incomplete && tab === "all" && (
              <div className="incomplete"><Icon name="alert" size={14} style={{ color: "#E0B457" }} /> Add your profile above to check eligibility against each opportunity&apos;s real requirements.</div>
            )}

            {!error && tab === "all" && all.length > 0 && (
              <>
                <div className="summary">
                  <div className="scard2"><div className="val">{all.length}</div><div className="lbl">Opportunities</div></div>
                  <div className="scard2"><div className="val">{sm.funded ?? 0}</div><div className="lbl">Funded</div></div>
                  <div className="scard2"><div className="val">{sm.positions ?? 0}</div><div className="lbl">Positions</div></div>
                  <div className="scard2"><div className="val">{(result?.country_facets ?? []).length}</div><div className="lbl">Countries</div></div>
                </div>
                {(result?.country_facets ?? []).length > 1 && (
                  <div className="facets">{result!.country_facets.map((f) => <button key={f.country} className={`qchip ${(active?.countries || []).includes(f.country) ? "on" : ""}`} onClick={() => toggleCountry(f.country)}>{f.country} · {f.count}</button>)}</div>
                )}
              </>
            )}

            {error ? (
              <div className="empty"><b>Couldn&apos;t reach the PhD service</b><p>{error}. Make sure the backend is running.</p></div>
            ) : visible.length === 0 ? (
              <div className="empty"><b>{tab === "saved" ? "No saved opportunities yet" : "No PhD opportunities found"}</b>
                <p>{tab === "saved" ? "Use Save on any opportunity to track it here." : "Broaden the research area, remove the country restriction, or expand the funding type — hard constraints are never silently relaxed."}</p></div>
            ) : (
              <div className="results">{visible.map((o) => <PhdCard key={o.id} o={o} saved={savedIds.has(o.id)} onOpen={setOpen} onSave={onSave} />)}</div>
            )}

            {result && (
              <div className="srcline">
                {result.sources.map((s) => <span key={s.source} className={`srctag ${s.status}`}><span className="d" />{s.source}{s.note ? ` — ${s.note}` : ""}</span>)}
                <span className="srctag note">Curated catalog of official programs/portals — verify each on its official page.</span>
              </div>
            )}
          </>
        )}
      </div>

      {open && <PhdDrawer o={open} saved={savedIds.has(open.id)} onClose={() => setOpen(null)} onSave={onSave} onWriteSop={writeSop} />}
    </div>
  );
}

function FG({ label, options, value, onPick, render }: { label: string; options: string[]; value?: string | null; onPick: (v: string) => void; render?: (v: string) => string }) {
  return (
    <div className="fgroup"><div className="fg-label">{label}</div>
      <div className="fg-opts">{options.map((o) => <button key={o} className={`qchip ${value === o ? "on" : ""}`} onClick={() => onPick(o)}>{render ? render(o) : o}</button>)}</div>
    </div>
  );
}
