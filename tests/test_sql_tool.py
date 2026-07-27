import sqlite3

from app.tools import sql_tool


def _seeded_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE employees (id INTEGER, name TEXT, dept TEXT, salary INTEGER)")
    conn.executemany(
        "INSERT INTO employees VALUES (?, ?, ?, ?)",
        [(1, "Ada", "eng", 120), (2, "Bo", "sales", 90), (3, "Cy", "eng", 110)],
    )
    conn.commit()
    return conn


def test_is_read_only_allows_select_and_with():
    assert sql_tool.is_read_only("SELECT * FROM t")
    assert sql_tool.is_read_only("with x as (select 1) select * from x")
    assert sql_tool.is_read_only("select * from t;")


def test_is_read_only_blocks_writes_and_ddl():
    assert not sql_tool.is_read_only("INSERT INTO t VALUES (1)")
    assert not sql_tool.is_read_only("DROP TABLE t")
    assert not sql_tool.is_read_only("UPDATE t SET x=1")


def test_is_read_only_blocks_stacked_statements():
    assert not sql_tool.is_read_only("SELECT 1; DROP TABLE t")


def test_run_query_returns_dicts():
    conn = _seeded_conn()
    sql = "SELECT name, salary FROM employees WHERE dept='eng' ORDER BY id"
    rows = sql_tool.run_query(sql, conn)
    assert rows == [{"name": "Ada", "salary": 120}, {"name": "Cy", "salary": 110}]


def test_format_rows_markdown():
    out = sql_tool.format_rows([{"name": "Ada", "salary": 120}])
    assert "| name | salary |" in out
    assert "| Ada | 120 |" in out


def test_format_rows_empty():
    assert sql_tool.format_rows([]) == "(0 rows)"


async def test_sql_query_handler(monkeypatch):
    conn = _seeded_conn()
    monkeypatch.setattr(sql_tool, "get_connection", lambda: conn)
    sql = "SELECT dept, COUNT(*) AS n FROM employees GROUP BY dept ORDER BY dept"
    out = await sql_tool.sql_query(sql)
    assert "| dept | n |" in out
    assert "| eng | 2 |" in out
    assert "| sales | 1 |" in out


async def test_sql_query_rejects_writes():
    out = await sql_tool.sql_query("DELETE FROM employees")
    assert out.startswith("error")
    assert "read-only" in out


def test_sql_query_registered():
    from app.tools.registry import default_registry
    assert "sql_query" in default_registry.names()
