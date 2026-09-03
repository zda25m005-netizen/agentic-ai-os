"use client";
import Icon from "../Icon";
import { JobListing, salaryLabel } from "../../lib/jobSearch";

export default function CompareView({ jobs, onClose }: { jobs: JobListing[]; onClose: () => void }) {
  const rows: [string, (j: JobListing) => string][] = [
    ["Match", (j) => (j.matchScore != null ? `${Math.round(j.matchScore * 100)}%` : "—")],
    ["Company", (j) => j.company],
    ["Location", (j) => j.location || "—"],
    ["Workplace", (j) => j.workplaceType || "—"],
    ["Experience", (j) => j.experience || "—"],
    ["Employment", (j) => j.employmentType || "—"],
    ["Salary", (j) => salaryLabel(j).text],
    ["Top skills", (j) => j.skills.slice(0, 4).join(", ") || "—"],
    ["Source", (j) => j.sources.join(", ")],
  ];
  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer wide" role="dialog" aria-label="Compare jobs">
        <div className="dhead">
          <div>
            <div className="dkicker">Compare</div>
            <div className="dtitle">{jobs.length} opportunities</div>
          </div>
          <button className="head-link" onClick={onClose} aria-label="Close"><Icon name="x" size={16} /></button>
        </div>
        <div className="cmp-wrap">
          <table className="cmp">
            <thead>
              <tr><th /> {jobs.map((j) => <th key={j.id}>{j.title}</th>)}</tr>
            </thead>
            <tbody>
              {rows.map(([label, get]) => (
                <tr key={label}>
                  <td className="cmp-k">{label}</td>
                  {jobs.map((j) => <td key={j.id}>{get(j)}</td>)}
                </tr>
              ))}
              <tr>
                <td className="cmp-k">Apply</td>
                {jobs.map((j) => (
                  <td key={j.id}>
                    <a className="btn primary sm" href={j.applicationUrl} target="_blank" rel="noreferrer noopener">
                      Apply <Icon name="arrowRight" size={12} sw={2} /></a>
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </aside>
    </>
  );
}
