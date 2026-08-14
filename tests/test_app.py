from pathlib import Path


def test_dashboard_content_exists():
    app = Path(__file__).resolve().parents[1] / "streamlit_app.py"
    contents = app.read_text(encoding="utf-8")

    assert "Shadow Fleet Intelligence Dashboard" in contents
    assert "pydeck" in contents
