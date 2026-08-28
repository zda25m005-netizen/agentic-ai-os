"""Markdown -> AST -> LaTeX: structural parsing, no raw markup leaks."""
from app.exec import markdown as md
from app.exec.latex.escape import tex_escape


def test_parses_block_structure():
    blocks = md.parse(
        "# Title\n\nA paragraph.\n\n## Sub\n\n- one\n- two\n\n1. first\n2. second\n"
        "\n```\ncode line\n```\n"
    )
    kinds = [type(b).__name__ for b in blocks]
    assert kinds == ["Heading", "Para", "Heading", "ListBlock", "ListBlock", "Code"]
    assert blocks[0].level == 1
    assert blocks[3].ordered is False and blocks[3].items == ["one", "two"]
    assert blocks[4].ordered is True and blocks[4].items == ["first", "second"]
    assert "code line" in blocks[5].text


def test_parses_gfm_table():
    blocks = md.parse("| A | B |\n| --- | --: |\n| 1 | 2 |\n| 3 | 4 |\n")
    assert len(blocks) == 1 and isinstance(blocks[0], md.Table)
    assert blocks[0].header == ["A", "B"]
    assert blocks[0].rows == [["1", "2"], ["3", "4"]]


def test_inline_to_latex_emphasis_and_escaping():
    out = md.inline_to_latex("**bold** and *italic* and `code` with 50% & _x_", tex_escape)
    assert r"\textbf{bold}" in out
    assert r"\textit{italic}" in out
    assert r"\texttt{code}" in out
    assert r"\textit{x}" in out
    assert r"\%" in out and r"\&" in out       # specials escaped
    assert "**" not in out and "`" not in out  # no raw markup


def test_inline_link_keeps_text_not_url():
    out = md.inline_to_latex("see [the docs](https://x.com/a_b)", tex_escape)
    assert "the docs" in out
    assert "https://" not in out               # URL dropped (lives in register)


def test_to_latex_has_no_raw_markdown():
    latex = md.to_latex(md.parse(
        "### Heading\n\n**Bold intro**\n\n- alpha\n- beta\n"
    ), tex_escape)
    assert r"\subsubsection*{Heading}" in latex
    assert r"\begin{itemize}" in latex and r"\item " in latex
    assert r"\textbf{Bold intro}" in latex
    for raw in ("###", "**", "\n- "):
        assert raw not in latex


def test_inline_to_plain_flattens():
    assert md.inline_to_plain("**b** *i* `c` [t](u)") == "b i c t"


def test_strip_bare_urls_keeps_markdown_links():
    s = md.strip_bare_urls("see https://bare.com and [ok](https://kept.com)")
    assert "https://bare.com" not in s
    assert "[ok](https://kept.com)" in s        # markdown link preserved
