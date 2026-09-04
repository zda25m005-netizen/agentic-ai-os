"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import "../../jobsearch.css";
import Icon from "../../components/Icon";
import JobSearchInput from "../../components/jobsearch/JobSearchInput";
import SearchProgress from "../../components/jobsearch/SearchProgress";
import JobCard from "../../components/jobsearch/JobCard";
import JobDetailDrawer from "../../components/jobsearch/JobDetailDrawer";
import CompareView from "../../components/jobsearch/CompareView";
import AnalysisReport from "../../components/jobsearch/AnalysisReport";
import SearchHistory from "../../components/jobsearch/SearchHistory";
import {
  parseCriteria, runJobSearch, loadHistory, pushHistory,
  loadSaved, toggleSaved, computeInsights, constraintChips, resultCountText,
  JobListing, JobSearchResult, SearchHistoryEntry,
} from "../../lib/jobSearch";

type Phase = "empty" | "searching" | "results";
type Quick = "all" | "best" | "newest" | "salary" | "remote";
type Sort = "match" | "newest" | "salhi" | "sallo" | "company";

function salaryNum(j: JobListing): number | null {
  if (!j.salary) return null;
  const m = j.salary.replace(/,/g, "").match(/(\d+(?:\.\d+)?)\s*([kK])?/);
  if (!m) return null;
  return parseFloat(m[1]) * (m[2] ? 1000 : 1);
}

export default function JobSearchAgentPage() {
  const [query, setQuery] = useState("");
  const [phase, setPhase] = useState<Phase>("empty");
  const [step, setStep] = useState(0);
  const [result, setResult] = useState<JobSearchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tookMs, setTookMs] = useState(0);

  const [history, setHistory] = useState<SearchHistoryEntry[]>([]);
  const [saved, setSaved] = useState<Record<string, JobListing>>({});

  const [text, setText] = useState("");
  const [quick, setQuick] = useState<Quick>("all");
  const [exp, setExp] = useState("");            // "" | "0-2" | "3-5" | "6+"  (hard constraint)
  const [sort, setSort] = useState<Sort>("match");
  const [view, setView] = useState<"all" | "saved">("all");
  const [modify, setModify] = useState(false);
  const [selecting, setSelecting] = useState(false);
  const [selected, setSelected] = useState<Set<string>>(new Set());

  const [openJob, setOpenJob] = useState<JobListing | null>(null);
  const [showCompare, setShowCompare] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => { setHistory(loadHistory()); setSaved(loadSaved()); }, []);
  useEffect(() => () => { if (timer.current) clearInterval(timer.current); }, []);

  const criteria = useMemo(() => parseCriteria(query), [query]);

  // A single search entry point. `expOverride` lets the experience filter re-run
  // the search so experience stays a BACKEND hard constraint (not a display trick).
  const search = async (expOverride?: string) => {
    if (!query.trim() || phase === "searching") return;
    const expValue = typeof expOverride === "string" ? expOverride : exp;
    setPhase("searching"); setError(null); setStep(0); setModify(false);
    const t0 = Date.now();
    timer.current = setInterval(() => setStep((s) => Math.min(s + 1, 4)), 550);
    try {
      const r = await runJobSearch(query.trim(), expValue || undefined);
      if (timer.current) clearInterval(timer.current);
      setStep(5);
      setResult(r);
      setTookMs(Date.now() - t0);
      setHistory(pushHistory(query.trim(), constraintChips(r.constraints).join(" · ") || query.trim(), r.jobs.length));
      setQuick("all"); setSort("match"); setView("all"); setText(""); setSelected(new Set()); setSelecting(false);
      setPhase("results");
    } catch (e) {
      if (timer.current) clearInterval(timer.current);
      setError(e instanceof Error ? e.message : "Search failed");
      setResult(null);
      setPhase("results");
    }
  };

  const changeExp = (v: string) => { setExp(v); search(v); };

  const onSave = (j: JobListing) => setSaved(toggleSaved(j));
  const onSelect = (j: JobListing) => setSelected((prev) => {
    const next = new Set(prev);
    if (next.has(j.id)) next.delete(j.id);
    else if (next.size < 4) next.add(j.id);
    return next;
  });

  const allJobs = result?.jobs ?? [];
  const savedList = Object.values(saved);

  const visible = useMemo(() => {
    let js = view === "saved" ? savedList : allJobs;
    if (text.trim()) {
      const q = text.toLowerCase();
      js = js.filter((j) => `${j.title} ${j.company} ${j.location ?? ""} ${j.skills.join(" ")}`.toLowerCase().includes(q));
    }
    if (quick === "best") js = js.filter((j) => (j.matchScore ?? 0) >= 0.75);
    else if (quick === "salary") js = js.filter((j) => j.salary);
    else if (quick === "remote") js = js.filter((j) => ["remote", "hybrid"].includes((j.workplaceType ?? "").toLowerCase()));
    else if (quick === "newest") js = js.filter((j) => j.postedAt && Date.now() - Date.parse(j.postedAt) < 14 * 864e5);

    const arr = [...js];
    arr.sort((a, b) => {
      if (sort === "match") return (b.matchScore ?? 0) - (a.matchScore ?? 0);
      if (sort === "company") return a.company.localeCompare(b.company);
      if (sort === "newest") return (b.postedAt ? Date.parse(b.postedAt) : 0) - (a.postedAt ? Date.parse(a.postedAt) : 0);
      const an = salaryNum(a), bn = salaryNum(b);
      if (an == null && bn == null) return 0;
      if (an == null) return 1; if (bn == null) return -1;   // missing salary always last
      return sort === "salhi" ? bn - an : an - bn;
    });
    return arr;
  }, [view, savedList, allJobs, text, quick, sort]);

  const ins = useMemo(() => computeInsights(visible), [visible]);
  const okSources = result?.sources.filter((s) => s.status === "ok").length ?? 0;
  const totalSources = result?.sources.length ?? 0;
  const selJobs = allJobs.filter((j) => selected.has(j.id));

  return (
    <div className="jsa">
      <div className="wrap">
        <div className="head">
          <div>
            <h1 className="h1">Job Search Agent</h1>
            <p className="h-sub">Find, compare, and prioritize opportunities that match your goals.</p>
          </div>
        </div>

        {/* EMPTY */}
        {phase === "empty" && (
          <>
            <JobSearchInput value={query} onChange={setQuery} onSearch={search} searching={false} />
            {history.length > 0 && (
              <>
                <div className="sec-h">Recent searches</div>
                <SearchHistory items={history} onPick={(q) => setQuery(q)} />
              </>
            )}
          </>
        )}

        {/* SEARCHING */}
        {phase === "searching" && (
          <>
            <div className="results-head">
              <div className="rh-sum">{query.trim()}</div>
            </div>
            <SearchProgress step={step} />
          </>
        )}

        {/* RESULTS */}
        {phase === "results" && (
          <>
            <div className="results-head">
              <div>
                <div className="rh-sum">
                  {result ? resultCountText(result.constraints, allJobs.length) : query.trim()}
                </div>
                {result && (
                  <>
                    {constraintChips(result.constraints).length > 0 && (
                      <div className="rh-chips">
                        {constraintChips(result.constraints).map((c) => (
                          <span className={`cchip ${c === "Strict location" || c === "Worldwide" ? "scope" : ""}`} key={c}>{c}</span>
                        ))}
                      </div>
                    )}
                    {result.constraints.locationScope !== "ANY" && (
                      <div className="rh-note">Showing only jobs matching your requested location and role.</div>
                    )}
                  </>
                )}
                {!error && (
                  <div className="rh-exec">
                    <Icon name="check" size={13} style={{ color: "var(--hgreen)" }} />
                    Completed · {result?.totalFetched ?? 0} retrieved → {allJobs.length} valid · {okSources}/{totalSources} sources · {(tookMs / 1000).toFixed(1)}s
                  </div>
                )}
              </div>
              <div className="rh-actions">
                <button className="btn ghost sm" onClick={() => setModify((m) => !m)}>
                  <Icon name="edit" size={13} /> Modify search
                </button>
                {!error && allJobs.length > 0 && (
                  <button className="btn ghost sm" onClick={() => setShowReport(true)}>
                    <Icon name="file" size={13} /> Generate Analysis Report
                  </button>
                )}
              </div>
            </div>

            {modify && (
              <div style={{ marginBottom: 18 }}>
                <JobSearchInput value={query} onChange={setQuery} onSearch={search} searching={false} compact />
              </div>
            )}

            {error ? (
              <div className="empty">
                <b>Couldn&apos;t reach the job service</b>
                <p>{error}. Make sure the backend is running (the Job Search Agent calls
                  its <code>/jobs/search</code> endpoint). Nothing is shown rather than fabricated listings.</p>
              </div>
            ) : allJobs.length === 0 ? (
              <div className="empty">
                <b>No matching openings right now</b>
                <p>The connected public boards ({okSources}/{totalSources} reachable) returned no roles matching
                  these criteria. Try broadening the role, location, or experience — no placeholder jobs are shown.</p>
              </div>
            ) : (
              <>
                {/* stat summary — computed from the visible result set */}
                <div className="summary">
                  <div className="scard"><div className="val">{visible.length}</div><div className="lbl">Jobs shown</div></div>
                  <div className="scard"><div className="val">{ins.strong}</div><div className="lbl">Strong matches</div></div>
                  <div className="scard"><div className="val">{ins.newThisWeek}</div><div className="lbl">New this week</div></div>
                  <div className="scard"><div className="val">{ins.withSalary}</div><div className="lbl">Salary disclosed</div></div>
                </div>

                {/* toolbar */}
                <div className="toolbar">
                  <div className="tb-search">
                    <Icon name="search" size={14} style={{ color: "var(--hmuted)" }} />
                    <input placeholder="Search within results…" value={text} onChange={(e) => setText(e.target.value)} />
                  </div>
                  <div className="tb-quick">
                    {(["all", "best", "newest", "salary", "remote"] as Quick[]).map((q) => (
                      <button key={q} className={`qchip ${quick === q ? "on" : ""}`} onClick={() => setQuick(q)}>
                        {q === "all" ? "All" : q === "best" ? "Best match" : q === "newest" ? "Newest"
                          : q === "salary" ? "Salary" : "Remote"}
                      </button>
                    ))}
                  </div>
                  <select className="tb-sort" value={exp} onChange={(e) => changeExp(e.target.value)}
                    title="Experience is a hard filter — re-runs the search">
                    <option value="">Any experience</option>
                    <option value="0-2">0–2 years</option>
                    <option value="3-5">3–5 years</option>
                    <option value="6+">6+ years</option>
                  </select>
                  <select className="tb-sort" value={sort} onChange={(e) => setSort(e.target.value as Sort)}>
                    <option value="match">Best match</option>
                    <option value="newest">Newest</option>
                    <option value="salhi">Salary: high → low</option>
                    <option value="sallo">Salary: low → high</option>
                    <option value="company">Company</option>
                  </select>
                </div>

                {/* view + compare controls */}
                <div className="viewbar">
                  <div className="seg">
                    <button className={view === "all" ? "on" : ""} onClick={() => setView("all")}>All jobs</button>
                    <button className={view === "saved" ? "on" : ""} onClick={() => setView("saved")}>
                      Saved{savedList.length ? ` · ${savedList.length}` : ""}
                    </button>
                  </div>
                  <span style={{ flex: 1 }} />
                  <button className={`btn ghost sm ${selecting ? "saved" : ""}`}
                    onClick={() => { setSelecting((s) => !s); setSelected(new Set()); }}>
                    <Icon name="layers" size={13} /> {selecting ? "Cancel compare" : "Compare"}
                  </button>
                  {selecting && (
                    <button className="btn primary sm" disabled={selected.size < 2} onClick={() => setShowCompare(true)}>
                      Compare {selected.size > 0 ? `(${selected.size})` : ""}
                    </button>
                  )}
                </div>

                {/* source provenance */}
                <div className="srcline">
                  {result?.sources.map((s) => (
                    <span key={s.source} className={`srctag ${s.status}`}>
                      <span className="d" />{s.source}{s.note ? ` — ${s.note}` : ""}
                    </span>
                  ))}
                </div>

                {view === "saved" && savedList.length === 0 ? (
                  <div className="empty" style={{ marginTop: 12 }}>
                    <b>No saved jobs yet</b>
                    <p>Use <b>Save</b> on any listing to keep it here. Saved jobs persist in this browser.</p>
                  </div>
                ) : (
                  <>
                    <div className="results">
                      {visible.map((j) => (
                        <JobCard key={j.id} job={j} saved={!!saved[j.id]} selected={selected.has(j.id)}
                          selectable={selecting} onOpen={setOpenJob} onSave={onSave} onSelect={onSelect} />
                      ))}
                    </div>
                    {visible.length === 0 && (
                      <div className="empty" style={{ marginTop: 12 }}>
                        <b>No jobs match these filters</b>
                        <p>Clear the search box or filters to see all {allJobs.length} results.</p>
                      </div>
                    )}
                  </>
                )}

                {/* insights */}
                {view === "all" && (
                  <>
                    <div className="sec-h" style={{ marginTop: 26 }}>Insights</div>
                    <div className="grid2">
                      <div className="panel">
                        <div className="panel-title">Top skills in demand</div>
                        {ins.topSkills.length ? ins.topSkills.map(([s, n]) => (
                          <div className="bar-row" key={s}>
                            <span className="bar-k">{s}</span>
                            <span className="bar-t"><span style={{ width: `${Math.round((n / ins.total) * 100)}%` }} /></span>
                            <span className="bar-v">{Math.round((n / ins.total) * 100)}%</span>
                          </div>
                        )) : <p className="muted" style={{ fontSize: 12.5 }}>No skills extractable from these postings.</p>}
                      </div>
                      <div className="panel">
                        <div className="panel-title">Locations</div>
                        {ins.byCountry.map(([k, n]) => (
                          <div className="bar-row" key={k}>
                            <span className="bar-k">{k}</span>
                            <span className="bar-t"><span style={{ width: `${Math.round((n / ins.total) * 100)}%` }} /></span>
                            <span className="bar-v">{n}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                )}
              </>
            )}

            {history.length > 0 && (
              <>
                <div className="sec-h" style={{ marginTop: 26 }}>Recent searches</div>
                <SearchHistory items={history} onPick={(q) => { setQuery(q); setModify(true); }} />
              </>
            )}
          </>
        )}
      </div>

      {openJob && (
        <JobDetailDrawer job={openJob} saved={!!saved[openJob.id]}
          onClose={() => setOpenJob(null)} onSave={onSave} />
      )}
      {showCompare && selJobs.length >= 2 && (
        <CompareView jobs={selJobs} onClose={() => setShowCompare(false)} />
      )}
      {showReport && result && (
        <AnalysisReport jobs={allJobs} criteria={criteria} sources={result.sources}
          onClose={() => setShowReport(false)} />
      )}
    </div>
  );
}
