"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import "../../../sop.css";
import Icon from "../../../components/Icon";
import {
  SopDoc, QualityReport, FactCheckResult, SopVersion,
  listSop, createSop, fromPhd, getSop, updateSop, generateSop, rewriteSop,
  checkSop, qualitySop, listVersions, snapshotVersion, restoreVersion, exportSop,
  STYLES, REWRITE_ACTIONS, factLabel,
} from "../../../lib/sopApi";

export default function SopPage() {
  const [doc, setDoc] = useState<SopDoc | null>(null);
  const [docs, setDocs] = useState<{ id: string; title: string; updated_at: number; words: number }[]>([]);
  const [content, setContent] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [saved, setSaved] = useState(true);
  const [tab, setTab] = useState<"analysis" | "facts" | "versions">("analysis");
  const [quality, setQuality] = useState<QualityReport | null>(null);
  const [facts, setFacts] = useState<FactCheckResult | null>(null);
  const [versions, setVersions] = useState<SopVersion[]>([]);
  const [error, setError] = useState<string | null>(null);
  const ta = useRef<HTMLTextAreaElement | null>(null);
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async (d: SopDoc) => { setDoc(d); setContent(d.content); setSaved(true); refreshDocs(); }, []);
  const refreshDocs = () => listSop().then(setDocs).catch(() => {});

  useEffect(() => {
    (async () => {
      try {
        const phd = new URLSearchParams(window.location.search).get("phd");
        if (phd) { await load(await fromPhd(phd)); return; }
        const list = await listSop(); setDocs(list);
        if (list.length) await load(await getSop(list[0].id));
        else await load(await createSop());
      } catch (e) { setError(e instanceof Error ? e.message : "Failed to load"); }
    })();
  }, [load]);

  // debounced autosave of content
  const onContent = (v: string) => {
    setContent(v); setSaved(false);
    if (saveTimer.current) clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(async () => {
      if (doc) { await updateSop(doc.id, { content: v }); setSaved(true); refreshDocs(); }
    }, 800);
  };

  const patchDoc = async (patch: Partial<SopDoc>) => { if (!doc) return; const d = await updateSop(doc.id, patch); setDoc(d); };
  const patchTarget = (k: string, v: string) => doc && patchDoc({ target: { ...doc.target, [k]: v || null } });
  const patchReq = (k: string, v: string | number | null) => doc && patchDoc({ requirements: { ...doc.requirements, [k]: v } });

  const generate = async () => {
    if (!doc) return; setBusy("Generating draft…"); setError(null);
    try { const d = await generateSop(doc.id, doc.style, doc.instructions); setDoc(d); setContent(d.content); setSaved(true); }
    catch (e) { setError(e instanceof Error ? e.message : "Generation failed"); }
    finally { setBusy(null); }
  };

  const applyRewrite = async (action: string) => {
    const el = ta.current; if (!el || !doc) return;
    const s = el.selectionStart, e = el.selectionEnd;
    if (s === e) { setError("Select some text to rewrite."); return; }
    const sel = content.slice(s, e);
    setBusy("Rewriting…"); setError(null);
    try {
      const { text } = await rewriteSop(doc.id, sel, action);
      const next = content.slice(0, s) + text + content.slice(e);
      onContent(next);
    } catch (err) { setError(err instanceof Error ? err.message : "Rewrite failed"); }
    finally { setBusy(null); }
  };

  const runCheck = async () => { if (!doc) return; setTab("facts"); setFacts(await checkSop(doc.id)); };
  const runQuality = async () => { if (!doc) return; setTab("analysis"); setQuality(await qualitySop(doc.id)); };
  const loadVersions = async () => { if (!doc) return; setTab("versions"); setVersions(await listVersions(doc.id)); };
  const snapshot = async () => { if (!doc) return; const label = `Draft ${versions.length + 1}`; await snapshotVersion(doc.id, label); loadVersions(); };
  const restore = async (vid: string) => { if (!doc) return; const d = await restoreVersion(doc.id, vid); setDoc(d); setContent(d.content); };

  const newDoc = async () => load(await createSop());
  const switchDoc = async (id: string) => load(await getSop(id));

  useEffect(() => { if (doc) qualitySop(doc.id).then(setQuality).catch(() => {}); }, [doc, content]);

  const words = content.trim() ? content.trim().split(/\s+/).length : 0;
  const limit = doc?.requirements.word_limit ?? null;

  return (
    <div className="sop">
      <div className="sop-top">
        <div className="sop-top-l">
          <input className="sop-title" value={doc?.title ?? ""} placeholder="Untitled SOP"
            onChange={(e) => setDoc(doc ? { ...doc, title: e.target.value } : doc)}
            onBlur={(e) => patchDoc({ title: e.target.value })} />
          <select className="sop-sel" value={doc?.id ?? ""} onChange={(e) => switchDoc(e.target.value)}>
            {docs.map((d) => <option key={d.id} value={d.id}>{d.title}</option>)}
          </select>
          <button className="btn ghost sm" onClick={newDoc}><Icon name="plus" size={13} /> New</button>
        </div>
        <div className="sop-top-r">
          <span className="sop-saved">{saved ? "Saved" : "Saving…"}</span>
          <select className="sop-sel" value={doc?.style ?? "academic"} onChange={(e) => patchDoc({ style: e.target.value })}>
            {STYLES.map((s) => <option key={s} value={s}>{s[0].toUpperCase() + s.slice(1)}</option>)}
          </select>
          <button className="btn ghost sm" onClick={() => doc && exportSop(doc.id, "pdf", doc.title)}>PDF</button>
          <button className="btn ghost sm" onClick={() => doc && exportSop(doc.id, "docx", doc.title)}>DOCX</button>
          <button className="btn ghost sm" onClick={() => doc && exportSop(doc.id, "txt", doc.title)}>TXT</button>
        </div>
      </div>

      {error && <div className="sop-err">{error} <button onClick={() => setError(null)}>×</button></div>}

      <div className="sop-grid">
        {/* LEFT: context */}
        <div className="sop-pane">
          <div className="sec-h" style={{ marginTop: 0 }}>Target application</div>
          <Field label="University" value={doc?.target.university} onSave={(v) => patchTarget("university", v)} />
          <Field label="Program" value={doc?.target.program} onSave={(v) => patchTarget("program", v)} />
          <Field label="Degree" value={doc?.target.degree} onSave={(v) => patchTarget("degree", v)} />
          <Field label="Country" value={doc?.target.country} onSave={(v) => patchTarget("country", v)} />
          <Field label="Field" value={doc?.target.field} onSave={(v) => patchTarget("field", v)} />
          {doc?.target.opportunity_url && (
            <a className="sop-link" href={doc.target.opportunity_url} target="_blank" rel="noreferrer noopener">Imported from PhD Finder →</a>
          )}

          <div className="sec-h">Requirements</div>
          <Field label="Word limit" value={doc?.requirements.word_limit != null ? String(doc.requirements.word_limit) : ""}
            onSave={(v) => patchReq("word_limit", v ? Number(v) : null)} placeholder="Not specified" />
          <div className="sop-fld">
            <span className="sop-fl">SOP prompt</span>
            <textarea className="sop-mini" defaultValue={doc?.requirements.prompt ?? ""} placeholder="Paste the official SOP prompt (optional)"
              onBlur={(e) => patchReq("prompt", e.target.value || null)} />
          </div>
          <div className="sop-note">Applicant facts come from your saved profile + résumé; program facts from the imported opportunity. The draft never invents facts.</div>
        </div>

        {/* CENTER: editor */}
        <div className="sop-editor">
          <div className="sop-toolbar">
            <button className="btn primary sm" onClick={generate} disabled={!!busy}>
              <Icon name="sync" size={13} /> {busy === "Generating draft…" ? "Generating…" : "Generate Draft"}
            </button>
            <span className="sop-tb-div" />
            {REWRITE_ACTIONS.map((a) => <button key={a.key} className="btn ghost sm" onClick={() => applyRewrite(a.key)} disabled={!!busy}>{a.label}</button>)}
          </div>
          {busy && <div className="sop-busy"><span className="spin" /> {busy} (no facts are invented)</div>}
          <textarea ref={ta} className="sop-doc" value={content} onChange={(e) => onContent(e.target.value)}
            placeholder="Write your Statement of Purpose, or click Generate Draft to start from your profile and target program…" />
          <div className="sop-count">
            Words: {words}{limit ? ` / ${limit}` : ""} · Characters: {content.length}
            {limit && words > limit ? <span className="over"> · over limit</span> : null}
          </div>
        </div>

        {/* RIGHT: analysis */}
        <div className="sop-pane">
          <div className="sop-tabs">
            <button className={tab === "analysis" ? "on" : ""} onClick={runQuality}>Analysis</button>
            <button className={tab === "facts" ? "on" : ""} onClick={runCheck}>Facts</button>
            <button className={tab === "versions" ? "on" : ""} onClick={loadVersions}>Versions</button>
          </div>

          {tab === "analysis" && quality && (
            <div>
              <div className="qrow"><span>Words</span><b>{quality.word_count}{quality.word_limit ? ` / ${quality.word_limit}` : ""}</b></div>
              <div className="qrow"><span>Specificity</span><b>{Math.round(quality.specificity * 100)}%</b></div>
              <div className="sec-h">Requirement coverage</div>
              {quality.coverage.map((c) => (
                <div className="chk" key={c.section}><span className={`chk-m ${c.covered ? "ok" : "unclear"}`}>{c.covered ? "✓" : "⚠"}</span><span className="chk-body">{c.section}</span></div>
              ))}
              {quality.generic_flags.length > 0 && (<><div className="sec-h">Generic language</div><div className="sop-flags">{quality.generic_flags.map((g) => <span key={g} className="flag">{g}</span>)}</div></>)}
              {quality.repetition_flags.length > 0 && (<><div className="sec-h">Repetition</div>{quality.repetition_flags.map((r, i) => <div key={i} className="sop-rep">{r}</div>)}</>)}
              <div className="sop-note" style={{ marginTop: 12 }}>These are computed metrics — not an objective quality score.</div>
            </div>
          )}

          {tab === "facts" && (
            <div>
              <button className="btn ghost sm" onClick={runCheck} style={{ marginBottom: 10 }}><Icon name="shield" size={13} /> Re-check facts</button>
              {facts ? (
                <>
                  <div className="qrow"><span>Verified {facts.verified} · Needs check {facts.needs_verification} · Unsupported {facts.unsupported}</span></div>
                  {facts.claims.map((c, i) => { const m = factLabel(c.status); return (
                    <div className="chk" key={i}><span className={`chk-m ${m.kind}`}>{m.sym}</span><span className="chk-body"><b>{c.text}</b>{c.note ? <div className="chk-exp">{c.note}</div> : null}</span></div>
                  ); })}
                  {facts.claims.length === 0 && <div className="sop-note">No flagged claims. Verify names/labs on the official page regardless.</div>}
                </>
              ) : <div className="sop-note">Run a fact check to compare claims against your profile/résumé.</div>}
            </div>
          )}

          {tab === "versions" && (
            <div>
              <button className="btn ghost sm" onClick={snapshot} style={{ marginBottom: 10 }}><Icon name="plus" size={13} /> Save version</button>
              {versions.map((v) => (
                <div className="ver" key={v.id}>
                  <span>{v.label}</span>
                  <button className="btn ghost sm" onClick={() => restore(v.id)}>Restore</button>
                </div>
              ))}
              {versions.length === 0 && <div className="sop-note">Save named versions (Draft 1, Draft 2, Final) and restore any of them.</div>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function Field({ label, value, onSave, placeholder }: { label: string; value: string | null | undefined; onSave: (v: string) => void; placeholder?: string }) {
  return (
    <div className="sop-fld">
      <span className="sop-fl">{label}</span>
      <input className="sop-in" defaultValue={value ?? ""} placeholder={placeholder ?? "—"} onBlur={(e) => onSave(e.target.value)} />
    </div>
  );
}
