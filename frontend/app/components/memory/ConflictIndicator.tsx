"use client";
import Icon from "../Icon";
import { Conflict } from "../../lib/memoryApi";

// Renders nothing unless real conflicts exist.
export default function ConflictIndicator({ conflicts, onReview }: {
  conflicts: Conflict[]; onReview: (c: Conflict) => void;
}) {
  if (!conflicts.length) return null;
  const c = conflicts[0];
  return (
    <div className="conflict">
      <Icon name="alert" size={17} sw={1.7} />
      <div>
        <b>Memory conflict</b>
        <p>Two memories contain different information about: {c.topic}</p>
      </div>
      <button className="btn ghost" onClick={() => onReview(c)}>Review</button>
    </div>
  );
}
