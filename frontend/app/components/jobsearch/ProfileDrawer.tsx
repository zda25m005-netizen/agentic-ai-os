"use client";
import Icon from "../Icon";
import { ResumeProfile, experienceLabel } from "../../lib/resumeApi";

function Section({ title, items }: { title: string; items: string[] }) {
  if (!items || items.length === 0) return null;
  return (
    <div style={{ marginBottom: 16 }}>
      <div className="sec-h" style={{ margin: "0 0 8px" }}>{title}</div>
      <div className="v" style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
        {items.map((s) => <span className="tagv" key={s}>{s}</span>)}
      </div>
    </div>
  );
}

export default function ProfileDrawer({ profile, filename, onClose }: {
  profile: ResumeProfile; filename?: string | null; onClose: () => void;
}) {
  return (
    <>
      <div className="scrim" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label="Candidate profile">
        <div className="dhead">
          <div>
            <div className="dkicker">Candidate profile</div>
            <div className="dtitle">Your resume</div>
            {filename && <div className="dco">{filename}</div>}
          </div>
          <button className="head-link" onClick={onClose} aria-label="Close"><Icon name="x" size={16} /></button>
        </div>

        {profile.summary && (
          <p style={{ fontSize: 13, lineHeight: 1.55, color: "var(--htext)", marginBottom: 16 }}>{profile.summary}</p>
        )}
        <div className="crow" style={{ marginBottom: 16 }}>
          <span className="k">Experience</span><span className="v">{experienceLabel(profile.experience_years)}</span>
        </div>
        <Section title="Skills" items={profile.skills} />
        <Section title="Job titles" items={profile.job_titles} />
        <Section title="Education" items={profile.education} />
        <Section title="Certifications" items={profile.certifications} />
        <Section title="Industries" items={profile.industries} />
        <Section title="Languages" items={profile.languages} />
        <Section title="Projects" items={profile.projects} />
        <Section title="Locations" items={profile.locations} />
      </aside>
    </>
  );
}
