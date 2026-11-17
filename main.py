"""Forecast Twitch launch-day CCU using analogous game-launch trajectories."""
import json
import math
import os
from datetime import datetime, timedelta
from pathlib import Path

LEVELS = (0.05, 0.25, 0.5, 0.75, 0.95)
INPUT = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))


def parse_utc(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def quantile(values, p):
    """Linear empirical quantile, with deterministic interpolation."""
    xs = sorted(values)
    if not xs:
        return 1.0
    at = (len(xs) - 1) * p
    lo = int(at)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (at - lo)


def curve_ratios(comp):
    rows = comp.get("hourly", [])
    if not rows:
        return None
    start = parse_utc(comp["day_start"])
    end = start + timedelta(hours=24)
    by_hour = {}
    for row in rows:
        stamp = parse_utc(row["from"])
        if start <= stamp < end:
            hour = int((stamp - start).total_seconds() // 3600) + 1
            by_hour.setdefault(hour, []).append(max(0, float(row["viewers"])))
    if not by_hour.get(1):
        return None
    first = max(1.0, sum(by_hour[1]) / len(by_hour[1]))
    return {h: max(1.0, sum(v) / len(v)) / first for h, v in by_hour.items()}


def forecast(case):
    known = next((r for r in case["known"] if r["hour"] == 1), None)
    if known is None or case["levels"] != list(LEVELS):
        raise ValueError("missing hour-one observation or unsupported levels")
    p1 = max(1.0, float(known["viewers"]))
    curves = [curve_ratios(c) for c in case["comparables"]]
    curves = [c for c in curves if c is not None]
    rows = []
    for target in case["forecast"]:
        h = target["hour"]
        sample = [c[h] for c in curves if h in c and c[h] > 0]
        # A neutral persistence fallback is preferable to extrapolating missing data.
        if len(sample) < 4:
            sample = [math.exp(z * 0.15 * math.sqrt(h - 1)) for z in (-1.645, -0.674, 0, 0.674, 1.645)]
        q = [max(0.01, min(1e9, round(p1 * quantile(sample, level), 2))) for level in LEVELS]
        for i in range(1, len(q)):
            q[i] = max(q[i], q[i - 1])
        rows.append({"hour": h, "q": q})
    return {"hours": rows}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for path in sorted(INPUT.glob("*.in")):
        result = forecast(json.loads(path.read_text(encoding="utf-8")))
        (OUTPUT / (path.stem + ".out")).write_text(json.dumps(result, separators=(",", ":")) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
