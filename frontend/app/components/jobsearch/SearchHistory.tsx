"use client";
import { SearchHistoryEntry } from "../../lib/jobSearch";

function rel(at: number) {
  const d = Date.now() - at;
  const h = Math.floor(d / 36e5), day = Math.floor(d / 864e5);
  if (h < 1) return "just now";
  if (day < 1) return `${h}h ago`;
  if (day === 1) return "yesterday";
  return `${day}d ago`;
}

export default function SearchHistory({ items, onPick }: {
  items: SearchHistoryEntry[]; onPick: (q: string) => void;
}) {
  if (!items.length) return null;
  return (
    <div className="panel">
      <div className="panel-title">Recent Searches</div>
      {items.map((h) => (
        <div className="hitem" key={h.id} onClick={() => onPick(h.query)}>
          <span className="hq">{h.query}</span>
          <span className="hmeta">{h.results} results · {rel(h.at)}</span>
        </div>
      ))}
    </div>
  );
}
