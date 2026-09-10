"use client";
// ---------------------------------------------------------------------------
// AgentCharacter — the single reusable renderer for every character.
//
//   <AgentCharacter character="nova" state="working" size={72} />
//
// The character is presentation only. `state` is the agent's REAL lifecycle state
// (from the mission/task runtime); this component just maps it to an expression +
// a subtle animation. All motion is gated behind prefers-reduced-motion in CSS.
// Pure SVG/CSS — no animation library, negligible bundle cost.
// ---------------------------------------------------------------------------

import { type AgentState, type CharacterDef, getCharacter, STATE_LABEL } from "../lib/characters";

type Expression = "neutral" | "think" | "happy" | "concerned" | "sleepy" | "alert" | "flat";

const STATE_EXPRESSION: Record<AgentState, Expression> = {
  idle: "neutral",
  thinking: "think",
  planning: "think",
  working: "neutral",
  waiting: "sleepy",
  needs_approval: "alert",
  completed: "happy",
  failed: "concerned",
  paused: "flat",
};

const STATE_ANIM: Record<AgentState, string> = {
  idle: "ac-bob",
  thinking: "ac-think",
  planning: "ac-think",
  working: "ac-work",
  waiting: "ac-sleepy",
  needs_approval: "ac-alert",
  completed: "ac-pop",
  failed: "ac-shake",
  paused: "",
};

// --- body silhouette per shape (viewBox 0 0 120 120) -----------------------
function bodyPath(shape: CharacterDef["shape"]): { el: "ellipse" | "path"; attrs: Record<string, number | string> } {
  switch (shape) {
    case "tall":     return { el: "ellipse", attrs: { cx: 60, cy: 70, rx: 28, ry: 40 } };
    case "chunky":   return { el: "ellipse", attrs: { cx: 60, cy: 74, rx: 42, ry: 34 } };
    case "round":    return { el: "ellipse", attrs: { cx: 60, cy: 70, rx: 36, ry: 36 } };
    case "bean":     return { el: "path", attrs: { d: "M30 74c0-24 16-38 34-34 18 4 26 20 22 40-4 20-24 28-40 20-12-6-16-16-16-26z" } };
    case "pebble":   return { el: "ellipse", attrs: { cx: 60, cy: 80, rx: 40, ry: 26 } };
    case "egg":      return { el: "ellipse", attrs: { cx: 60, cy: 72, rx: 32, ry: 38 } };
    case "capsule":  return { el: "path", attrs: { d: "M40 52a20 20 0 0140 0v30a20 20 0 01-40 0z" } };
    case "dome":     return { el: "path", attrs: { d: "M24 96V72a36 34 0 0172 0v24a6 6 0 01-6 6H30a6 6 0 01-6-6z" } };
    case "diamond":  return { el: "path", attrs: { d: "M60 32l34 38-34 38-34-38z" } };
    case "teardrop": return { el: "path", attrs: { d: "M60 34c16 14 30 30 30 46a30 30 0 01-60 0c0-16 14-32 30-46z" } };
    case "pear":     return { el: "path", attrs: { d: "M60 36c10 0 14 10 14 20 8 6 14 16 14 26a28 28 0 01-56 0c0-10 6-20 14-26 0-10 4-20 14-20z" } };
    case "hex":      return { el: "path", attrs: { d: "M60 34l30 17v34L60 102 30 85V51z" } };
    case "blob":     return { el: "path", attrs: { d: "M34 62c2-18 20-30 38-24 16 6 22 22 18 40-3 14-14 24-30 24-18 0-28-14-28-30 0-4 1-7 2-10z" } };
    default:         return { el: "ellipse", attrs: { cx: 60, cy: 70, rx: 36, ry: 36 } };
  }
}

// --- topper (ears, antenna, etc.) drawn above the body ---------------------
function Topper({ t, accent }: { t: CharacterDef["topper"]; accent: string }) {
  const line = "#0b0f17";
  switch (t) {
    case "ears":
      return <g fill={accent} stroke={line} strokeWidth={2}>
        <path d="M36 44c-4-14-2-22 6-22s10 10 8 20z" /><path d="M84 44c4-14 2-22-6-22s-10 10-8 20z" />
      </g>;
    case "earTufts":
      return <g fill={accent} stroke={line} strokeWidth={2}>
        <path d="M40 40l-6-16 16 8z" /><path d="M80 40l6-16-16 8z" />
      </g>;
    case "antenna":
      return <g stroke={line} strokeWidth={2}><line x1="60" y1="40" x2="60" y2="20" /><circle cx="60" cy="16" r="6" fill={accent} /></g>;
    case "antenna2":
      return <g stroke={line} strokeWidth={2}>
        <line x1="48" y1="40" x2="42" y2="22" /><circle cx="41" cy="18" r="5" fill={accent} />
        <line x1="72" y1="40" x2="78" y2="22" /><circle cx="79" cy="18" r="5" fill={accent} />
      </g>;
    case "sprout":
      return <g stroke={line} strokeWidth={2}><line x1="60" y1="42" x2="60" y2="26" /><path d="M60 30c-8-2-14-8-14-8s2 10 14 8z" fill={accent} /></g>;
    case "horns":
      return <g fill={accent} stroke={line} strokeWidth={2}><path d="M38 46c-8-6-12-16-8-22 6 2 12 12 12 20z" /><path d="M82 46c8-6 12-16 8-22-6 2-12 12-12 20z" /></g>;
    case "bow":
      return <g fill={accent} stroke={line} strokeWidth={2}><path d="M60 34l-16-8v16zM60 34l16-8v16z" /><circle cx="60" cy="34" r="4" /></g>;
    case "cap":
      return <g fill={accent} stroke={line} strokeWidth={2}><path d="M32 44c0-14 12-22 28-22s28 8 28 22z" /><rect x="30" y="42" width="60" height="6" rx="3" /></g>;
    case "fin":
      return <g fill={accent} stroke={line} strokeWidth={2}><path d="M60 42c-2-16 4-24 4-24s10 10 4 24z" /></g>;
    case "tuft":
      return <g stroke={line} strokeWidth={2} fill={accent}><path d="M60 42c-6-10-2-20-2-20s8 6 8 14M60 42c6-10 2-18 2-18" /></g>;
    case "moon":
      return <g fill={accent} stroke={line} strokeWidth={2}><path d="M52 26a10 10 0 1012 0 8 8 0 01-12 0z" /></g>;
    case "glasses":
      return <g stroke={line} strokeWidth={2} fill="none"><line x1="60" y1="40" x2="60" y2="22" /><circle cx="60" cy="18" r="5" fill={accent} /></g>;
    default:
      return null;
  }
}

// --- eyes + mouth per expression -------------------------------------------
function Face({ expr, eyes }: { expr: Expression; eyes: CharacterDef["eyes"] }) {
  const ink = "#0b0f17";
  const lx = 48, rx = 72, ey = 68; // eye anchor points
  const r = eyes === "wide" ? 6 : eyes === "dot" ? 3 : eyes === "oval" ? 4.5 : 5;

  let eyeEls: React.ReactNode;
  let mouth: React.ReactNode;

  switch (expr) {
    case "happy":
      eyeEls = <g stroke={ink} strokeWidth={3} fill="none" strokeLinecap="round">
        <path d={`M${lx - 5} ${ey + 2}q5 -7 10 0`} /><path d={`M${rx - 5} ${ey + 2}q5 -7 10 0`} /></g>;
      mouth = <path d="M52 82q8 8 16 0" stroke={ink} strokeWidth={3} fill="none" strokeLinecap="round" />;
      break;
    case "sleepy":
      eyeEls = <g stroke={ink} strokeWidth={3} strokeLinecap="round"><line x1={lx - 5} y1={ey} x2={lx + 5} y2={ey} /><line x1={rx - 5} y1={ey} x2={rx + 5} y2={ey} /></g>;
      mouth = <circle cx="60" cy="82" r="3" fill={ink} />;
      break;
    case "concerned":
      eyeEls = <g stroke={ink} strokeWidth={3} strokeLinecap="round">
        <line x1={lx - 4} y1={ey - 4} x2={lx + 4} y2={ey + 4} /><line x1={lx + 4} y1={ey - 4} x2={lx - 4} y2={ey + 4} />
        <line x1={rx - 4} y1={ey - 4} x2={rx + 4} y2={ey + 4} /><line x1={rx + 4} y1={ey - 4} x2={rx - 4} y2={ey + 4} /></g>;
      mouth = <path d="M52 84q8 -6 16 0" stroke={ink} strokeWidth={3} fill="none" strokeLinecap="round" />;
      break;
    case "alert":
      eyeEls = <g fill={ink}><circle cx={lx} cy={ey} r={6} /><circle cx={rx} cy={ey} r={6} /></g>;
      mouth = <ellipse cx="60" cy="83" rx="4" ry="5" fill={ink} />;
      break;
    case "think":
      eyeEls = <g fill={ink}><circle cx={lx} cy={ey - 3} r={r} /><circle cx={rx} cy={ey - 3} r={r} /></g>;
      mouth = <line x1="54" y1="83" x2="64" y2="83" stroke={ink} strokeWidth={3} strokeLinecap="round" />;
      break;
    case "flat":
      eyeEls = <g stroke={ink} strokeWidth={3} strokeLinecap="round"><line x1={lx - 4} y1={ey} x2={lx + 4} y2={ey} /><line x1={rx - 4} y1={ey} x2={rx + 4} y2={ey} /></g>;
      mouth = <line x1="54" y1="83" x2="66" y2="83" stroke={ink} strokeWidth={3} strokeLinecap="round" />;
      break;
    default: // neutral
      eyeEls = eyes === "oval"
        ? <g fill={ink}><ellipse cx={lx} cy={ey} rx={r - 1} ry={r + 1} /><ellipse cx={rx} cy={ey} rx={r - 1} ry={r + 1} /></g>
        : <g fill={ink}><circle cx={lx} cy={ey} r={r} /><circle cx={rx} cy={ey} r={r} /></g>;
      mouth = <path d="M54 82q6 5 12 0" stroke={ink} strokeWidth={2.5} fill="none" strokeLinecap="round" />;
  }
  return <g>{eyeEls}<g className="ac-eyeshine" fill="#fff" opacity={expr === "concerned" || expr === "flat" ? 0 : 0.9}>
    <circle cx={lx - 2} cy={ey - 2} r={1.4} /><circle cx={rx - 2} cy={ey - 2} r={1.4} /></g>{mouth}</g>;
}

// --- status glyph (top-right) ----------------------------------------------
function Glyph({ state, accent }: { state: AgentState; accent: string }) {
  if (state === "waiting") return <text x="96" y="30" fontSize="16" fill={accent} fontWeight="700">z</text>;
  if (state === "needs_approval") return <g><circle cx="96" cy="26" r="10" fill="#f59e0b" /><text x="96" y="31" fontSize="14" fill="#0b0f17" textAnchor="middle" fontWeight="800">!</text></g>;
  if (state === "completed") return <g className="ac-sparkle" fill={accent}><path d="M96 16l2 6 6 2-6 2-2 6-2-6-6-2 6-2z" /></g>;
  if (state === "thinking" || state === "planning")
    return <g className="ac-dots" fill={accent}><circle cx="90" cy="30" r="2.5" /><circle cx="98" cy="26" r="3" /><circle cx="106" cy="22" r="3.5" /></g>;
  return null;
}

export default function AgentCharacter({
  character,
  state = "idle",
  size = 72,
  className = "",
}: {
  character: string;
  state?: AgentState;
  size?: number;
  className?: string;
}) {
  const c = getCharacter(character);
  const expr = STATE_EXPRESSION[state];
  const anim = STATE_ANIM[state];
  const body = bodyPath(c.shape);
  const dim = state === "paused" ? 0.55 : 1;

  return (
    <span
      className={`ac ${className}`}
      style={{ width: size, height: size, display: "inline-block", opacity: dim }}
      role="img"
      aria-label={`${c.name}, ${STATE_LABEL[state]}`}
    >
      <svg viewBox="0 0 120 120" width={size} height={size} className={anim} style={{ overflow: "visible" }}>
        <ellipse cx="60" cy="110" rx="26" ry="5" fill="#000" opacity={0.18} />
        <Topper t={c.topper} accent={c.accent} />
        {body.el === "ellipse"
          ? <ellipse {...(body.attrs as any)} fill={c.accent} stroke="#0b0f17" strokeWidth={2.5} />
          : <path {...(body.attrs as any)} fill={c.accent} stroke="#0b0f17" strokeWidth={2.5} />}
        {/* soft belly highlight */}
        <ellipse cx="60" cy="76" rx="18" ry="14" fill="#fff" opacity={0.14} />
        <g className={state === "idle" ? "ac-blink" : ""}>
          <Face expr={expr} eyes={c.eyes} />
        </g>
        <Glyph state={state} accent={c.accent} />
      </svg>
    </span>
  );
}
