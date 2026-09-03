"use client";
import Icon from "../Icon";
import { ACTIVITY } from "../../lib/dashboardData";

export default function RecentActivity() {
  return (
    <div className="panel">
      <div className="panel-head">
        <div className="panel-title">Recent Activity</div>
        <span className="link">View all</span>
      </div>
      <div className="panel-sub" />
      {ACTIVITY.map((a, i) => (
        <div className="act" key={i}>
          <div className="act-ico"><Icon name={a.icon} size={15} sw={1.7} /></div>
          <div className="act-b">
            <div className="act-title">{a.title}</div>
            <div className="act-sub">{a.sub}</div>
          </div>
          <div className="act-time">{a.time}</div>
        </div>
      ))}
    </div>
  );
}
