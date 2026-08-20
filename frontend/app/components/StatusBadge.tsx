import type { MissionStatus, TaskStatus } from "../lib/api";

// Maps every mission/task status to a color class defined in globals.css.
const CLASS: Record<string, string> = {
  created: "s-created",
  active: "s-active",
  running: "s-active",
  ready: "s-ready",
  pending: "s-pending",
  paused: "s-paused",
  completed: "s-done",
  done: "s-done",
  failed: "s-failed",
  skipped: "s-skipped",
};

export default function StatusBadge({
  status,
}: {
  status: MissionStatus | TaskStatus | string;
}) {
  return <span className={`badge ${CLASS[status] || "s-pending"}`}>{status}</span>;
}
