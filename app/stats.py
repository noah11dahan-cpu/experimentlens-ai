from typing import Dict, Any
import math

import pandas as pd


def load_experiment_csv(file_obj) -> pd.DataFrame:
    """
    Read a CSV file object into a pandas DataFrame.

    Expected columns:
    - variant (e.g. "A", "B")
    - users (int)
    - conversions (int)
    """
    df = pd.read_csv(file_obj)
    # Basic sanity check
    required_cols = {"variant", "users", "conversions"}
    if not required_cols.issubset(df.columns):
        missing = required_cols - set(df.columns)
        raise ValueError(f"CSV is missing required columns: {', '.join(missing)}")
    return df


def _normal_cdf(x: float) -> float:
    """
    Cumulative distribution function for a standard normal variable.
    Uses the error function from the math module (no external deps).
    """
    return 0.5 * (1 + math.erf(x / math.sqrt(2)))


def _z_test_proportions(
    conv_a: int,
    users_a: int,
    conv_b: int,
    users_b: int,
) -> float:
    """
    Two-proportion z-test for variant B vs variant A.
    Returns the p-value (two-sided).
    """
    if users_a == 0 or users_b == 0:
        return 1.0  # no users = cannot test

    p1 = conv_a / users_a
    p2 = conv_b / users_b
    p_pool = (conv_a + conv_b) / (users_a + users_b)

    # Standard error
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / users_a + 1 / users_b))
    if se == 0:
        return 1.0

    z = (p2 - p1) / se

    # Two-sided p-value
    p_value = 2 * (1 - _normal_cdf(abs(z)))
    return p_value


def compute_conversion_stats(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """
    Compute conversion stats for each variant.

    Returns a dict like:
    {
      "A": {"users": 1000, "conversions": 120, "conversion_rate": 0.12},
      "B": {"users": 980, "conversions": 150, "conversion_rate": 0.153,
            "uplift": 0.033, "p_value": 0.04},
    }
    """

    stats: Dict[str, Dict[str, Any]] = {}

    # Expect one row per variant (A and B)
    for _, row in df.iterrows():
        variant = str(row["variant"])
        users = int(row["users"])
        conversions = int(row["conversions"])
        if users <= 0:
            conv_rate = 0.0
        else:
            conv_rate = conversions / users

        stats[variant] = {
            "users": users,
            "conversions": conversions,
            "conversion_rate": conv_rate,
        }

    # Compute uplift and p-value for B vs A (if both exist)
    if "A" in stats and "B" in stats:
        a = stats["A"]
        b = stats["B"]

        uplift = b["conversion_rate"] - a["conversion_rate"]
        p_value = _z_test_proportions(
            conv_a=a["conversions"],
            users_a=a["users"],
            conv_b=b["conversions"],
            users_b=b["users"],
        )

        stats["B"]["uplift"] = uplift
        stats["B"]["p_value"] = p_value

    return stats
