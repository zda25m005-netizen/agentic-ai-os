"use client";
import { useEffect, useRef } from "react";
import Icon from "../Icon";

export default function Topbar() {
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="topbar">
      <label className="search" onClick={() => inputRef.current?.focus()}>
        <Icon name="search" size={15} />
        <input ref={inputRef} placeholder="Search anything..." aria-label="Search" />
        <span className="kbd">⌘ K</span>
      </label>
      <div className="topbar-right">
        <button className="icon-btn" aria-label="Notifications"><Icon name="bell" size={17} /></button>
        <div className="chev">
          <span className="avatar">GJ</span>
          <Icon name="chevronDown" size={14} sw={2} />
        </div>
      </div>
    </div>
  );
}
