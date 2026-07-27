from app.tools import python_exec as pe


async def test_runs_and_captures_stdout():
    r = await pe.run_python("print('hello world')")
    assert r.ok is True
    assert "hello world" in r.stdout
    assert r.returncode == 0


async def test_computation():
    out = await pe.python_exec("print(sum(range(1, 6)))")
    assert out == "15"


async def test_runtime_error_is_captured():
    r = await pe.run_python("1 / 0")
    assert r.ok is False
    assert "ZeroDivisionError" in r.stderr


async def test_handler_reports_error():
    out = await pe.python_exec("raise ValueError('boom')")
    assert out.startswith("error")
    assert "ValueError" in out


async def test_no_output_message():
    out = await pe.python_exec("x = 1 + 1")
    assert out == "(no output)"


async def test_timeout_kills_process():
    r = await pe.run_python("import time; time.sleep(5)", timeout=1)
    assert r.ok is False
    assert "timeout" in r.stderr


def test_python_exec_registered():
    from app.tools.registry import default_registry
    assert "python_exec" in default_registry.names()
