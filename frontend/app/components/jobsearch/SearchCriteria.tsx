"use client";
import { JobCriteria } from "../../lib/jobSearch";

function Row({ k, values, empty }: { k: string; values: string[]; empty?: string }) {
  return (
    <div className="crow">
      <span className="k">{k}</span>
      <span className="v">
        {values.length
          ? values.map((v) => <span className="tagv" key={v}>{v}</span>)
          : <span className="muted">{empty ?? "—"}</span>}
      </span>
    </div>
  );
}

export default function SearchCriteria({ c }: { c: JobCriteria }) {
  return (
    <div className="criteria">
      <Row k="Role" values={c.roles} empty="Any role" />
      <Row k="Location" values={c.locations} empty="Any location" />
      <Row k="Experience" values={c.experience ? [c.experience] : []} empty="Any level" />
      <Row k="Remote" values={c.remote ? ["Preferred"] : []} empty="Not specified" />
      <Row k="Keywords" values={c.keywords} empty="None detected" />
    </div>
  );
}
