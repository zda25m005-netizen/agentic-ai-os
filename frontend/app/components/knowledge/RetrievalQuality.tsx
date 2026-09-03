"use client";
import Icon from "../Icon";
import { QUALITY } from "../../lib/knowledgeApi";

export default function RetrievalQuality() {
  return (
    <div className="quality">
      {QUALITY.map((q) => (
        <div className="qcard" key={q.name}>
          <div className="qn">{q.name}</div>
          {q.value && <div className="qv">{q.value}</div>}
          {q.baseline && (
            <div className="qdelta">
              <span className="qbase">{q.baseline}</span>
              <span className="qarr"><Icon name="arrowRight" size={14} sw={2} /></span>
              <span className="qcur">{q.current}</span>
            </div>
          )}
          <div className="qnote">{q.note}</div>
        </div>
      ))}
    </div>
  );
}
