"use client";
import Link from "next/link";
import Icon from "../Icon";
import { ActivityEvent, relSeconds } from "../../lib/obsApi";

export default function LiveActivity({ events }: { events: ActivityEvent[] }) {
  return (
    <div className="card">
      {events.length === 0 && <div className="empty-note">No mission activity yet.</div>}
      {events.map((e) => (
        <Link key={e.missionId} href={`/missions/${e.missionId}`} className="act act-link">
          <span className={`d ${e.status}`} />
          <span className="title">{e.title}</span>
          <span className="prog">{e.progress}</span>
          <span className="time">{relSeconds(e.at)}</span>
          <span className="view"><Icon name="arrowRight" size={13} sw={2} /></span>
        </Link>
      ))}
    </div>
  );
}
