"""Leakage-free leave-one-out backtest over the kit's launch comparables."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from main import LEVELS, curve_ratios, quantile

kit = Path(sys.argv[1])
case = json.loads((kit / "input/p00.in").read_text())
curves = [(c["name"], curve_ratios(c)) for c in case["comparables"]]
curves = [(n, c) for n, c in curves if c and 1 in c]
z = (-1.645, -0.674, 0, 0.674, 1.645)
base_sigma = 0.15
ours, baseline = [], []
for _, held in curves:
    p1 = max(1.0, held[1])
    others = [c for _, c in curves if c is not held]
    for h in range(2, 25):
        if h not in held:
            continue
        actual = held[h]
        sample = [c[h] for c in others if h in c]
        qs = [p1 * quantile(sample, t) for t in LEVELS]
        bq = [p1 * math.exp(v * base_sigma * math.sqrt(h - 1)) for v in z]
        y = max(1e-9, actual)
        for pred, out in ((qs, ours), (bq, baseline)):
            for t, q in zip(LEVELS, pred):
                d = math.log(y) - math.log(max(q, 1e-9))
                out.append(2 * max(t * d, (t - 1) * d))
print(f"LOO items={len(ours)} analog_loss={sum(ours)/len(ours):.6f} baseline_loss={sum(baseline)/len(baseline):.6f} ratio={sum(ours)/sum(baseline):.4f}")
