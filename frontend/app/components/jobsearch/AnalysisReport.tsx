"use client";
import { useState } from "react";
import Icon from "../Icon";
import { API } from "../../lib/api";
import {
  JobCriteria, JobListing, SourceStatus, computeInsights, criteriaSummary, salaryLabel,
} from "../../lib/jobSearch";

// The report is ANALYTICAL ONLY — market overview, skill/salary/location/company
// analysis, and a short highlight of the top opportunities. It is deliberately
// NOT a dump of every listing; the full browsable list lives in the UI.
function buildSections(jobs: JobListing[], c: JobCriteria, sources: SourceStatus[]) {
  const ins = computeInsights(jobs);
  const disclosed = jobs.filter((j) => j.salary);
  const top = [...jobs].sort((a, b) => (b.matchScore ?? 0) - (a.matchScore ?? 0)).slice(0, 5);

  const skillLines = ins.topSkills.map(([s, n]) =>
    `${s}: ${n} of ${ins.total} roles (${Math.round((n / ins.total) * 100)}%)`).join("\n");
  const locLines = ins.byCountry.map(([k, n]) => `${k}: ${n}`).join("\n");
  const srcLines = sources.map((s) =>
    `${s.source}: ${s.status === "ok" ? "available" : "unavailable"}${s.note ? ` (${s.note})` : ""}`).join("\n");

  return [
    { heading: "Search criteria", body:
      `Query: ${c.raw || "—"}\nInterpreted as: ${criteriaSummary(c)}\n` +
      `Roles: ${c.roles.join(", ") || "any"}\nLocations: ${c.locations.join(", ") || "any"}\n` +
      `Experience: ${c.experience || "any"}\nRemote preferred: ${c.remote ? "yes" : "no"}` },
    { heading: "Sources searched", body: srcLines || "No sources reported." },
    { heading: "Market overview", body:
      `${ins.total} matching opportunities across ${ins.companies} companies.\n` +
      `${ins.strong} strong matches (75%+ relevance to your criteria).\n` +
      `${ins.newThisWeek} posted in the last 7 days.\n` +
      `${ins.withSalary} of ${ins.total} disclose salary.` },
    { heading: "Skill demand", body: skillLines || "No skills were extractable from the postings." },
    { heading: "Location analysis", body: locLines || "No location data available." },
    { heading: "Salary analysis", body: disclosed.length
      ? `${disclosed.length} of ${ins.total} roles disclose salary. Figures are taken verbatim from ` +
        `the job boards; roles without a disclosed range are not estimated.\n` +
        disclosed.slice(0, 8).map((j) => `${j.title} — ${j.company}: ${j.salary}`).join("\n")
      : "No employers in this result set disclosed salary. No figures are estimated." },
    { heading: "Top matching opportunities", body: top.map((j) =>
      `${j.title} — ${j.company}${j.location ? ` (${j.location})` : ""} · ` +
      `${j.matchScore != null ? Math.round(j.matchScore * 100) + "% match" : "match n/a"} · ` +
      `${salaryLabel(j).text}`).join("\n") || "—" },
    { heading: "Methodology", body:
      "Listings were fetched from official, keyless public job-board APIs (Greenhouse, Lever) for a " +
      "curated set of AI/ML companies, normalized, de-duplicated by company + title, and ranked by " +
      "keyword/role/location overlap with the stated criteria. Match scores reflect search relevance, " +
      "not hiring probability. No listings, salaries, dates, or URLs were fabricated." },
  ];
}

export default function AnalysisReport({ jobs, criteria, sources, onClose }: {
  jobs: JobListing[]; criteria: JobCriteria; sources: SourceStatus[]; onClose: () => void;
}) {
  const [busy, setBusy] = useState(false);
  const sections = buildSections(jobs, criteria, sources);

  const download = async () => {
    setBusy(true);
    try {
      const r = await fetch(`${API}/reports/pdf`, {
        method: "POST", headers: { "content-type": "application/json" },
        body: JSON.stringify({ title: "Job Market Analysis", filename: "job-market-analysis", sections }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = "job-market-analysis.pdf"; a.click();
      URL.revokeObjectURL(url);
    } catch {
      alert("Could not generate the PDF — the report service is unavailable.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <div className="scrim" onClick={onClose} />
      <div className="report" role="dialog" aria-label="Job market analysis report">
        <div className="dhead">
          <div>
            <div className="dkicker">Analysis report</div>
            <div className="dtitle">Job Market Analysis</div>
            <div className="dco">{jobs.length} opportunities · {criteriaSummary(criteria)}</div>
          </div>
          <button className="head-link" onClick={onClose} aria-label="Close"><Icon name="x" size={16} /></button>
        </div>
        <div className="rbody">
          {sections.map((s) => (
            <div className="rsec" key={s.heading}>
              <div className="rsec-h">{s.heading}</div>
              <pre className="rsec-b">{s.body}</pre>
            </div>
          ))}
        </div>
        <div className="dactions">
          <span className="rnote">This report contains analysis only — browse and apply to jobs in the workspace.</span>
          <button className="btn primary" onClick={download} disabled={busy}>
            <Icon name="file" size={14} /> {busy ? "Generating…" : "Download PDF"}
          </button>
        </div>
      </div>
    </>
  );
}
