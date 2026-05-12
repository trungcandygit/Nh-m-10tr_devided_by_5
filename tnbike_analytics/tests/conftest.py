"""conftest.py — tự động sinh output/test_report.md sau khi chạy toàn bộ test suite."""


def pytest_sessionfinish(session, exitstatus):
    try:
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))
        from tests.test_prediction_engine import _write_report
        _write_report()
    except Exception:
        pass
