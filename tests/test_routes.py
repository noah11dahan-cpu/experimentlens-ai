import io

from fastapi.testclient import TestClient

from app.main import app
from app.db import SessionLocal
from app import models


client = TestClient(app)


def _create_test_csv_bytes() -> bytes:
    """
    Create a tiny in-memory CSV that matches the expected format
    of load_experiment_csv: variant, users, conversions.
    """
    csv_content = (
        "variant,users,conversions\n"
        "A,2,1\n"
        "B,2,2\n"
    )
    return csv_content.encode("utf-8")



def test_upload_creates_experiment_and_redirects():
    # Prepare form data
    data = {
        "name": "Day 11 Test Experiment",
        "hypothesis": "Test hypothesis for upload route",
        "alpha": "0.05",
    }
    file_bytes = _create_test_csv_bytes()

    files = {
        "file": ("test.csv", io.BytesIO(file_bytes), "text/csv"),
    }

    # Call POST /upload
    response = client.post("/upload", data=data, files=files, follow_redirects=False)

    # Day 11: assert response status is 200 or 302 (or 303)
    assert response.status_code in (200, 302, 303)

    # Check that an experiment was actually created in the DB
    db = SessionLocal()
    try:
        experiments = db.query(models.Experiment).all()
        assert len(experiments) >= 1

        # Grab the latest experiment
        exp = experiments[-1]
        assert exp.name == "Day 11 Test Experiment"
    finally:
        db.close()


def test_experiment_appears_in_list_page():
    # First, ensure at least one experiment exists by reusing the upload
    data = {
        "name": "List Page Experiment",
        "hypothesis": "Hypothesis for list page test",
        "alpha": "0.05",
    }
    file_bytes = _create_test_csv_bytes()
    files = {
        "file": ("test.csv", io.BytesIO(file_bytes), "text/csv"),
    }
    upload_response = client.post("/upload", data=data, files=files, follow_redirects=True)
    assert upload_response.status_code in (200, 302, 303)

    # Now check GET /experiments
    list_response = client.get("/experiments")
    assert list_response.status_code == 200

    # HTML content should contain the experiment name
    body = list_response.text
    assert "List Page Experiment" in body
