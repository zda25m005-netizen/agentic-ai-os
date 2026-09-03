"use client";
import Link from "next/link";
import { ErrorEvent } from "../../lib/obsApi";

export default function ErrorPanel({ errors }: { errors: ErrorEvent[] }) {
  return (
    <div className="card">
      {errors.length === 0 && <div className="empty-note">No failures in recent missions.</div>}
      {errors.map((e, i) => (
        <Link key={i} href={`/missions/${e.missionId}`} className="err" style={{ textDecoration: "none" }}>
          <span className="ed" />
          <span className="etitle">{e.title}</span>
          <span className="etype">{e.detail}</span>
        </Link>
      ))}
    </div>
  );
}
