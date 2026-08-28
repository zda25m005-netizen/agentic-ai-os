"""Render the structured `Report` IR into a professional LaTeX document.

The renderer owns all structure and styling; dynamic text is escaped (escape.py)
before it is placed into the document, so agent/LLM content is data, never code.
Nothing here fabricates data — every section is emitted only when the IR carries
real content for it, and qualitative scores are labelled as analyst assessments.
"""
from __future__ import annotations

import re

from app.exec import markdown as md
from app.exec.latex.escape import tex_escape
from app.exec.report import Report, ReportSection, Scorecard, Table

_URL_RE = re.compile(r"https?://\S+")


def _prose(text: str) -> str:
    """Escaped body text with bare URLs removed (they live in the register)."""
    cleaned = _URL_RE.sub("", text or "")
    cleaned = re.sub(r"\s+([.,;:])", r"\1", cleaned)   # tidy space before punctuation
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return tex_escape(cleaned)

# Confidence label -> (xcolor name defined in the preamble)
_CONF_COLOR = {
    "High": "confhigh",
    "Medium": "confmed",
    "Low": "conflow",
    "Analytical": "confana",
}

_PREAMBLE = r"""\documentclass[11pt]{article}
\usepackage[a4paper,top=24mm,bottom=24mm,left=22mm,right=22mm]{geometry}
\usepackage[T1]{fontenc}
\usepackage{lmodern}
\usepackage{xcolor}
\usepackage{titlesec}
\usepackage{fancyhdr}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{array}
\usepackage{longtable}
\usepackage{ragged2e}
\usepackage{needspace}
\usepackage{enumitem}
\usepackage{tcolorbox}
\usepackage{amsmath}
\usepackage{graphicx}
\usepackage{lastpage}
\usepackage[hidelinks]{hyperref}

% --- restrained analytical palette ---
\definecolor{navy}{RGB}{20,33,61}
\definecolor{steel}{RGB}{45,77,122}
\definecolor{ink}{RGB}{28,31,38}
\definecolor{mute}{RGB}{110,116,128}
\definecolor{rule}{RGB}{205,210,218}
\definecolor{track}{RGB}{232,235,240}
\definecolor{cardbg}{RGB}{248,249,251}
\definecolor{confhigh}{RGB}{23,140,86}
\definecolor{confmed}{RGB}{196,132,10}
\definecolor{conflow}{RGB}{178,45,58}
\definecolor{confana}{RGB}{45,77,122}

\color{ink}
\setlength{\parindent}{0pt}
\setlength{\parskip}{5pt}
\renewcommand{\arraystretch}{1.25}

% --- headings ---
\titleformat{\section}{\sffamily\Large\bfseries\color{navy}}{\thesection}{0.6em}{}[{\color{rule}\titlerule[0.8pt]}]
\titlespacing*{\section}{0pt}{16pt}{6pt}
\titleformat{\subsection}{\sffamily\large\bfseries\color{steel}}{\thesubsection}{0.5em}{}
\titlespacing*{\subsection}{0pt}{10pt}{3pt}

% --- header / footer ---
\pagestyle{fancy}\fancyhf{}
\renewcommand{\headrulewidth}{0.4pt}
\renewcommand{\footrulewidth}{0.4pt}
\fancyhead[L]{\footnotesize\sffamily\color{mute}\REPTITLE}
\fancyhead[R]{}
\fancyfoot[L]{}
\fancyfoot[C]{}
\fancyfoot[R]{\footnotesize\sffamily\color{mute}Page \thepage\ of \pageref{LastPage}}

\newcolumntype{L}{>{\RaggedRight\arraybackslash}X}

% evidence bar: #1 = fill fraction (0..1)
\newcommand{\evbar}[1]{\noindent\begingroup\color{track}\rule{\linewidth}{10pt}\hspace{-\linewidth}\color{navy}\rule{#1\linewidth}{10pt}\endgroup}
% confidence badge: #1 = color, #2 = label
\newcommand{\confbadge}[2]{\setlength{\fboxsep}{3pt}\colorbox{#1}{\textcolor{white}{\scriptsize\sffamily\bfseries #2}}}

\newtcolorbox{bottomline}{colback=navy,colframe=navy,arc=2pt,left=12pt,right=12pt,top=10pt,bottom=10pt,coltext=white}
\newtcolorbox{findingcard}{colback=cardbg,colframe=rule,boxrule=0.4pt,arc=2pt,left=11pt,right=11pt,top=9pt,bottom=9pt}
\newtcolorbox{integritybox}{colback=white,colframe=rule,boxrule=0.6pt,arc=2pt,left=12pt,right=12pt,top=10pt,bottom=10pt}
"""


def _defs(report: Report) -> str:
    return f"\\newcommand{{\\REPTITLE}}{{{tex_escape(report.title)[:70]}}}\n"


def _cover(r: Report) -> str:
    meta = r.meta
    rtype = r.report_type.replace("_", " ").title()
    status = {"COMPLETED": "Completed", "FAILED": "Failed"}.get(
        str(meta.get("status", "")).upper(), meta.get("status", "Completed"))
    n_src = meta.get("sources", len(r.source_records))
    lines = [
        r"\thispagestyle{empty}",
        r"\noindent{\color{navy}\rule{\linewidth}{6pt}}\par\vspace{34mm}",
        r"{\sffamily\normalsize\color{steel}\bfseries RESEARCH \& ANALYSIS REPORT}"
        r"\par\vspace{22mm}",
        r"{\sffamily\bfseries\color{navy}\fontsize{26}{30}\selectfont " + tex_escape(r.title) + r"\par}",
    ]
    if r.subtitle:
        lines.append(r"\vspace{6pt}{\sffamily\large\color{mute}" + tex_escape(r.subtitle) + r"\par}")
    lines.append(r"\vspace{4mm}{\color{steel}\rule{60mm}{1.4pt}}\par")
    lines.append(r"\vfill")
    meta_rows = [
        ("Report type", rtype),
        ("Date", str(meta.get("date", ""))),
        ("Status", str(status)),
        ("Evidence base", f"{n_src} source(s)"),
    ]
    body = r"\noindent\begin{tabular}{@{}p{34mm}l@{}}"
    for k, v in meta_rows:
        if v:
            body += (r"{\sffamily\small\color{mute}" + tex_escape(k) + r"} & "
                     + r"{\sffamily\small\bfseries\color{ink}" + tex_escape(v) + r"} \\")
    body += r"\end{tabular}\par"
    lines.append(body)
    lines.append(r"\clearpage")
    return "\n".join(lines)


def _overall_conf(r: Report) -> str:
    confs = {f.confidence for f in r.findings}
    if "High" in confs:
        return "High"
    if "Medium" in confs:
        return "Medium"
    if "Low" in confs:
        return "Low"
    return "Analytical"


def _exec_summary(r: Report) -> str:
    out = [r"\section{Executive Summary}"]
    if r.executive_summary:
        out.append(md.inline_to_latex(md.strip_bare_urls(r.executive_summary), tex_escape))
    # Bottom line callout — first substantive finding, else summary lead.
    bl = ""
    if r.findings:
        bl = r.findings[0].body.strip()
    bl = bl or r.executive_summary
    bl = md.inline_to_plain(_URL_RE.sub("", bl)).strip()
    if bl:
        bl = bl.split(". ")[0].rstrip(".") + "."
        out.append(r"\vspace{4pt}\begin{bottomline}"
                   r"{\sffamily\bfseries\footnotesize BOTTOM LINE}\par\vspace{3pt}"
                   + tex_escape(bl[:400]) + r"\end{bottomline}")
    # evidence coverage bar (real) + overall qualitative confidence
    if r.coverage:
        pct = r.coverage.coverage_pct
        conf = r.integrity.get("overall_confidence") or _overall_conf(r)
        col = _CONF_COLOR.get(conf, "confana")
        out.append(r"\vspace{8pt}{\sffamily\footnotesize\color{mute}EVIDENCE COVERAGE}\par\vspace{3pt}"
                   + f"\\evbar{{{pct / 100:.3f}}}\\par\\vspace{{2pt}}"
                   + r"{\footnotesize\color{mute}" + f"{pct}\\% of major claims source-backed "
                   + f"$\\cdot$ {r.coverage.sources_analyzed} source(s) analysed "
                   + r"$\cdot$ overall confidence \confbadge{" + col + "}{"
                   + conf.upper() + r"} (analyst assessment).}")
    # snapshot key figures
    if r.snapshot:
        cells = " & ".join(r"{\sffamily\footnotesize\color{mute}" + tex_escape(m.label.upper())
                           + r"}\newline{\sffamily\large\bfseries\color{navy}" + tex_escape(m.value)
                           + r"}" for m in r.snapshot[:4])
        cols = "X" * min(len(r.snapshot), 4)
        out.append(r"\par\vspace{10pt}\noindent\begin{tabularx}{\linewidth}{" + cols + r"}"
                   + cells + r"\end{tabularx}\par")
    return "\n\n".join(out)


def _findings(r: Report) -> str:
    if not r.findings:
        return ""
    out = [r"\section{Key Findings}"]
    for i, f in enumerate(r.findings, 1):
        col = _CONF_COLOR.get(f.confidence, "confana")
        card = [r"\begin{findingcard}",
                r"{\sffamily\bfseries\large\color{steel}" + f"{i:02d}" + r"}\quad"
                r"{\sffamily\bfseries\color{navy}" + tex_escape(f.title) + r"}"
                r"\hfill\confbadge{" + col + "}{" + tex_escape(f.confidence).upper() + r"}",
                r"\par\vspace{4pt}"
                + md.inline_to_latex(md.strip_bare_urls(f.body[:700]), tex_escape)]
        if f.unverified_figures:
            card.append(r"\par\vspace{3pt}{\footnotesize\color{conflow}\sffamily "
                        r"$\triangle$~Contains quantitative figures not backed by any "
                        r"source (unverified).}")
        if f.source_refs:
            refs = ", ".join(f"[{n}]" for n in f.source_refs)
            card.append(r"\par\vspace{3pt}{\footnotesize\color{steel}\sffamily Traceability: cites "
                        + tex_escape(refs) + r" (see Source Register).}")
        card.append(r"\end{findingcard}\vspace{6pt}")
        out.append("\n".join(card))
    return "\n".join(out)


def _scorecard(sc: Scorecard) -> str:
    cols = "l" + "c" * len(sc.dimensions)
    head = " & ".join([r"\sffamily\bfseries "] + [
        r"\sffamily\bfseries\footnotesize " + tex_escape(d) for d in sc.dimensions])
    rows = []
    for e in sc.entities:
        vals = sc.scores.get(e, [])
        cells = [r"\sffamily\bfseries " + tex_escape(e)]
        for j in range(len(sc.dimensions)):
            cells.append(tex_escape(str(vals[j])) if j < len(vals) else "-")
        rows.append(" & ".join(cells) + r" \\")
    body = "\n".join(rows)
    return (r"\section{Decision Matrix}"
            r"\noindent\begin{tabular}{@{}" + cols + r"@{}}\toprule "
            + head + r" \\\midrule " + body + r"\bottomrule\end{tabular}"
            r"\par\vspace{3pt}{\footnotesize\color{mute}" + tex_escape(sc.methodology) + r"}")


def _visual(chart_keys) -> str:
    """Include chart figures (written into the compile dir as assets)."""
    if not chart_keys:
        return ""
    out = [r"\section{Visual Analysis}"]
    if "chart_bar.pdf" in chart_keys:
        out.append(r"\begin{center}\includegraphics[width=0.94\linewidth]{chart_bar.pdf}"
                   r"\end{center}\par{\footnotesize\color{mute}Figure 1 --- Analyst-derived "
                   r"capability scores (0--5), based on evidence collected during this "
                   r"mission. Not market-share or measured statistics.}")
    if "chart_radar.pdf" in chart_keys:
        out.append(r"\begin{center}\includegraphics[width=0.6\linewidth]{chart_radar.pdf}"
                   r"\end{center}\par{\footnotesize\color{mute}Figure 2 --- Capability radar "
                   r"of the same analyst-derived scores (0--5). Not market data.}")
    return "\n\n".join(out)


def _quality(r: Report) -> str:
    if not r.critic_flags:
        return ""
    items = "".join(
        r"\item {\color{conflow}\bfseries Critic flagged topic drift.}~" + tex_escape(fl)
        for fl in r.critic_flags)
    return (r"\section{Quality Control (Critic)}"
            r"\begin{itemize}[leftmargin=14pt,itemsep=3pt,topsep=3pt]" + items + r"\end{itemize}")


def _integrity(r: Report) -> str:
    ig = r.integrity
    if not ig:
        return ""
    extracted = ig.get("claims_extracted", 0)
    unv = ig.get("unverified_figures", 0)
    unv_cell = (r"{\color{conflow}" + str(unv) + r"}") if unv else str(unv)
    cells = [
        ("Sources analysed", str(ig.get("sources_analyzed", 0))),
        ("Findings", str(extracted)),
        ("Source-backed", f"{ig.get('claims_supported', 0)} / {extracted}"),
        ("Unsupported", str(ig.get("unsupported", 0))),
        ("High confidence", str(ig.get("high_confidence", 0))),
        ("Unverified figures", unv_cell),
    ]
    body = ""
    for i, (label, val) in enumerate(cells):
        body += (r"{\sffamily\footnotesize\color{mute}" + tex_escape(label.upper())
                 + r"}\newline{\sffamily\Large\bfseries " + val + r"}")
        body += r" \\" + "\n" if i % 3 == 2 else " & "
    return (r"\section{Research Integrity}\begin{integritybox}"
            r"\begin{tabularx}{\linewidth}{XXX}" + body + r"\end{tabularx}\end{integritybox}"
            r"\par{\footnotesize\color{mute}Metrics reflect this run's actual evidence "
            r"ledger; no values are fabricated.}")


def _coverage_freshness(r: Report) -> str:
    if not r.coverage:
        return ""
    cov = r.coverage
    out = [r"\section{Evidence Coverage}",
           f"{cov.coverage_pct}\\% of major claims are source-backed "
           f"({cov.claims_supported} of {cov.claims_supported + cov.assessments}); "
           f"{cov.sources_analyzed} source(s) analysed, {cov.assessments} analytical "
           f"assessment(s)."]
    if r.freshness and r.source_records:
        fr = r.freshness
        out.append(r"\par\vspace{2pt}{\footnotesize\color{mute}Source freshness --- "
                   f"Recent: {fr.get('Recent', 0)} $\\cdot$ Current: {fr.get('Current', 0)} "
                   f"$\\cdot$ Background: {fr.get('Background', 0)} "
                   f"$\\cdot$ Unknown: {fr.get('Unknown', 0)}.}}")
    return "\n\n".join(out)


def _table(t: Table) -> str:
    ncol = len(t.columns)
    if ncol == 0:
        return ""
    spec = " ".join(["L"] * ncol)
    head = " & ".join(r"\sffamily\bfseries " + tex_escape(c) for c in t.columns)
    body = ""
    for row in t.rows:
        cells = [tex_escape(str(row[j])) if j < len(row) else "" for j in range(ncol)]
        body += " & ".join(cells) + r" \\" + "\n"
    cap = (r"\par\vspace{2pt}{\footnotesize\color{mute}" + tex_escape(t.caption) + r"}") if t.caption else ""
    return (r"\par\vspace{3pt}\small\noindent\begin{tabularx}{\linewidth}{" + spec + r"}\toprule "
            + head + r" \\\midrule " + body + r"\bottomrule\end{tabularx}\normalsize" + cap)


def _md_table(header: list[str], rows: list[list[str]]) -> str:
    return _table(Table(header, rows, ""))


def _sections(secs: list[ReportSection]) -> str:
    out = []
    for s in secs:
        out.append(r"\section{" + tex_escape(s.heading) + r"}")
        # Task/LLM output is Markdown: parse structurally, then render to LaTeX
        # (headings, bold/italic, lists, tables, code) — never leak raw markup.
        body = md.strip_bare_urls("\n\n".join(s.paragraphs))
        out.append(md.to_latex(md.parse(body), tex_escape, table_fn=_md_table))
        if s.table:
            out.append(_table(s.table))
    return "\n\n".join(out)


def _il(text: str) -> str:
    return md.inline_to_latex(md.strip_bare_urls(text), tex_escape)


def _problem(r: Report) -> str:
    if not r.problem_definition:
        return ""
    return r"\section{Problem Definition}" + _il(r.problem_definition)


def _bullets(label: str, items: list) -> str:
    if not items:
        return ""
    li = "".join(r"\item " + _il(str(x)) for x in items)
    return (r"\subsection*{" + tex_escape(label) + r"}"
            r"\begin{itemize}[leftmargin=14pt,itemsep=1pt,topsep=2pt]" + li + r"\end{itemize}")


def _approaches(r: Report) -> str:
    if not r.approaches:
        return ""
    out = []
    for a in r.approaches:
        out.append(r"\section{" + tex_escape(str(a.get("name", "Approach"))) + r"}")
        if a.get("how_it_works"):
            out.append(r"\subsection*{How it works}" + _il(a["how_it_works"]))
        out.append(_bullets("Advantages", a.get("advantages", [])))
        out.append(_bullets("Disadvantages", a.get("disadvantages", [])))
        out.append(_bullets("Failure modes", a.get("failure_modes", [])))
        out.append(_bullets("Mitigations", a.get("mitigations", [])))
    return "\n\n".join(p for p in out if p)


def _comparative(r: Report) -> str:
    if not r.comparative_analysis:
        return ""
    return r"\section{Comparative Analysis}" + _il(r.comparative_analysis)


def _failure_analysis(r: Report) -> str:
    if not r.failure_analysis:
        return ""
    rows = ""
    for d in r.failure_analysis:
        rows += (_il(d.get("failure", "")) + " & " + _il(d.get("impact", "")) + " & "
                 + _il(d.get("mitigation", "")) + r" \\" + "\n")
    return (r"\section{Failure Mode Analysis}"
            r"\small\begin{tabularx}{\linewidth}{@{}L L L@{}}\toprule "
            r"\sffamily\bfseries Failure & \sffamily\bfseries Impact & "
            r"\sffamily\bfseries Mitigation \\\midrule " + rows
            + r"\bottomrule\end{tabularx}\normalsize")


def _recommendation(r: Report) -> str:
    if not r.recommendation and not r.decision_rationale:
        return ""
    out = [r"\section{Recommendation}"]
    if r.recommendation:
        out.append(md.inline_to_latex(md.strip_bare_urls(r.recommendation), tex_escape))
    if r.decision_rationale:
        rows = ""
        for d in r.decision_rationale:
            rows += (_il(d.get("requirement", "")) + " & " + _il(d.get("decision", "")) + " & "
                     + _il(d.get("reason", "")) + r" \\" + "\n")
        out.append(
            r"\vspace{4pt}\subsection*{Decision Rationale}"
            r"\small\begin{tabularx}{\linewidth}{@{}>{\RaggedRight\arraybackslash}p{34mm} "
            r">{\RaggedRight\arraybackslash}p{34mm} L@{}}\toprule "
            r"\sffamily\bfseries Requirement & \sffamily\bfseries Decision & "
            r"\sffamily\bfseries Reason \\\midrule " + rows
            + r"\bottomrule\end{tabularx}\normalsize")
    return "\n\n".join(out)


def _strategic(r: Report) -> str:
    if not r.strategic_implications:
        return ""
    items = "".join(r"\item " + _il(x) for x in r.strategic_implications)
    return (r"\section{Strategic Implications}"
            r"\begin{itemize}[leftmargin=14pt,itemsep=3pt,topsep=3pt]" + items + r"\end{itemize}")


def _closing(r: Report) -> str:
    out = []
    if r.methodology:
        out.append(r"\section{Methodology}" + _il(r.methodology))
    if r.limitations:
        items = "".join(r"\item " + _il(x) for x in r.limitations)
        out.append(r"\section{Limitations \& Caveats}"
                   r"\begin{itemize}[leftmargin=14pt,itemsep=2pt,topsep=3pt]" + items + r"\end{itemize}")
    return "\n\n".join(out)


def _ref_label(url: str) -> str:
    """A short, wrapping, human title for a reference (from the URL slug/domain)."""
    from urllib.parse import unquote
    path = url.split("?")[0].split("#")[0].rstrip("/")
    slug = path.rsplit("/", 1)[-1] if "/" in path.split("//")[-1] else ""
    label = unquote(slug).replace("_", " ").strip()
    if len(label) < 3:
        label = url.split("//")[-1].split("/")[0]  # fall back to the domain
    return label[:70]


def _href(url: str) -> str:
    """Clickable reference showing a readable title (wraps), linking to the URL."""
    target = url.replace("\\", "").replace("%", r"\%").replace("#", r"\#")
    return r"\href{" + target + r"}{\color{steel}" + tex_escape(_ref_label(url)) + "}"


def _sources(r: Report) -> str:
    if not r.source_records and not r.sources:
        # Compact, honest line instead of a near-empty Source Register page.
        return (r"\section{Source Verification}"
                r"{\color{mute}External verification unavailable for this run.}")
    out = [r"\section{References}"]
    if r.source_records:
        rows = ""
        for s in r.source_records:
            rows += (f"{s.ref} & " + _href(s.url) + " & " + tex_escape(s.stype) + " & "
                     + tex_escape(s.credibility) + " & " + tex_escape(s.freshness) + r" \\" + "\n")
        out.append(
            r"\small\begin{longtable}{@{}r >{\RaggedRight\arraybackslash}p{58mm}@{\hspace{6mm}} l l l@{}}"
            r"\toprule \# & Source & Type & Cred. & Freshness \\\midrule\endhead "
            + rows + r"\bottomrule\end{longtable}\normalsize"
            r"\par{\footnotesize\color{mute}Type, credibility and freshness are internal "
            r"analyst heuristics, not objective ratings.}")
    elif r.sources:
        items = "".join(r"\item " + _href(s) for s in r.sources)
        out.append(r"\begin{enumerate}[leftmargin=16pt,itemsep=1pt]" + items + r"\end{enumerate}")
    else:
        out.append(r"{\color{mute}External source verification was not available for this analysis.}")
    return "\n\n".join(out)


def _appendix(secs: list[ReportSection]) -> str:
    if not secs:
        return ""
    out = [r"\clearpage\section*{Appendix}\addcontentsline{toc}{section}{Appendix}"]
    for s in secs:
        out.append(r"\subsection*{" + tex_escape(s.heading) + r"}")
        for p in s.paragraphs:
            out.append(tex_escape(p))
        if s.table:
            out.append(_table(s.table))
    return "\n".join(out)


def render_tex(report: Report, chart_keys: set[str] | None = None) -> str:
    """Compose the full LaTeX source for a report.

    `chart_keys` names chart asset files (e.g. "chart_bar.pdf") that the caller
    will write into the compile directory; only those are \\includegraphics'd.
    """
    chart_keys = chart_keys or set()
    # When the LLM supplied structured per-approach analysis, it replaces the generic
    # task-result sections (which would otherwise duplicate the content).
    detailed = "" if report.approaches else _sections(report.sections)
    parts = [
        _PREAMBLE,
        _defs(report),
        r"\begin{document}",
        _cover(report),
        _exec_summary(report),
        _problem(report),
        _findings(report),
        _approaches(report),
        _comparative(report),
        _scorecard(report.scorecard) if report.scorecard else "",
        _visual(chart_keys),
        _failure_analysis(report),
        _recommendation(report),
        _quality(report),
        _integrity(report),
        _coverage_freshness(report),
        detailed,
        _strategic(report),
        _closing(report),
        _sources(report),
        _appendix(report.appendix),
        r"\end{document}",
    ]
    return "\n\n".join(p for p in parts if p)
