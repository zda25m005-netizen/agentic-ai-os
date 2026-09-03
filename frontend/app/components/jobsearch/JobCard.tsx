"use client";
import Icon from "../Icon";
import { JobListing, postedLabel, salaryLabel } from "../../lib/jobSearch";

export default function JobCard({ job, saved, selected, selectable, onOpen, onSave, onSelect }: {
  job: JobListing;
  saved: boolean;
  selected: boolean;
  selectable: boolean;
  onOpen: (j: JobListing) => void;
  onSave: (j: JobListing) => void;
  onSelect: (j: JobListing) => void;
}) {
  const sal = salaryLabel(job);
  const meta = [job.workplaceType, job.employmentType, job.experience].filter(Boolean);
  return (
    <div className="job" onClick={() => onOpen(job)}>
      {selectable && (
        <button className={`jcheck ${selected ? "on" : ""}`} title="Select to compare"
          onClick={(e) => { e.stopPropagation(); onSelect(job); }}>
          {selected && <Icon name="check" size={12} />}
        </button>
      )}
      <div className="job-main">
        <div className="job-top">
          <span className="job-title">{job.title}</span>
          {job.matchScore != null && <span className="job-match">{Math.round(job.matchScore * 100)}% match</span>}
        </div>
        <div className="job-co">{job.company}{job.location ? ` · ${job.location}` : ""}</div>
        {meta.length > 0 && <div className="job-meta">{meta.map((m) => <span key={m}>{m}</span>)}</div>}
        {job.skills.length > 0 && (
          <div className="job-skills">{job.skills.slice(0, 6).map((s) => <span className="tagv" key={s}>{s}</span>)}</div>
        )}
        <div className="job-sub">
          <span className={`sal ${sal.kind}`}>{sal.text}</span>
          <span className="dot">·</span>
          <span>{postedLabel(job.postedAt)}</span>
        </div>
        <div className="job-foot">
          <span className="job-src">
            {job.sources.length > 1 ? `${job.sources.length} sources` : `Source: ${job.source}`}
          </span>
          <button className={`btn ghost sm ${saved ? "saved" : ""}`} onClick={(e) => { e.stopPropagation(); onSave(job); }}>
            <Icon name={saved ? "bookmarkOn" : "bookmark"} size={13} /> {saved ? "Saved" : "Save"}
          </button>
          <a className="btn primary sm" href={job.applicationUrl} target="_blank" rel="noreferrer noopener"
            onClick={(e) => e.stopPropagation()}>Apply <Icon name="arrowRight" size={13} sw={2} /></a>
        </div>
      </div>
    </div>
  );
}
