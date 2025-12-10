import io
import pytest

from app.stats import load_experiment_csv, compute_conversion_stats


def test_compute_conversion_stats_basic():
    # This CSV matches what your app expects from a real upload
    csv_content = (
        "variant,users,conversions\n"
        "A,2,1\n"
        "B,2,2\n"
    )

    # Create a file-like object, just like UploadFile.file in FastAPI
    file_like = io.BytesIO(csv_content.encode("utf-8"))

    # IMPORTANT: use the SAME pre-processing as the real app
    df = load_experiment_csv(file_like)

    # Now df has the same shape/columns as in your app
    stats = compute_conversion_stats(df)

    # Assertions on the resulting stats dict
    assert "A" in stats
    assert "B" in stats

    a = stats["A"]
    b = stats["B"]

    # Users & conversions
    assert a["users"] == 2
    assert a["conversions"] == 1
    assert b["users"] == 2
    assert b["conversions"] == 2

    # Conversion rates
    assert a["conversion_rate"] == pytest.approx(0.5, rel=1e-6)
    assert b["conversion_rate"] == pytest.approx(1.0, rel=1e-6)

    # Uplift & p-value, but only if your code sets them
    if "uplift" in b:
        assert b["uplift"] > 0

    if "p_value" in b and b["p_value"] is not None:
        assert 0 <= b["p_value"] <= 1
