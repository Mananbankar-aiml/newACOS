"""
Invoice anomaly detection: statistics + unsupervised ML, no LLM involved.

* Isolation Forest over engineered per-invoice features (amount, log-amount, vendor z-score,
  vendor frequency, round-amount flag, threshold-proximity flag, duplicate count).
* Benford's-law first-digit chi-square test across the whole population.
* Per-vendor robust z-scores (median / MAD) so a single big vendor can't mask outliers.

Output is a per-invoice score in [0, 1] plus human-readable reasons, which the Finance agent
then explains and a human approves.  ML detects -> LLM explains -> human decides.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Dict, List

import numpy as np
from sklearn.ensemble import IsolationForest

BENFORD_EXPECTED = {d: math.log10(1 + 1 / d) for d in range(1, 10)}
APPROVAL_THRESHOLDS = (1000, 5000, 10000, 25000)
MIN_SAMPLES_FOR_FOREST = 12


def _first_digit(x: float) -> int:
    s = f"{abs(x):.10g}".lstrip("0.")
    return int(s[0]) if s and s[0].isdigit() and s[0] != "0" else 0


def benford_test(amounts: List[float]) -> Dict:
    digits = [_first_digit(a) for a in amounts if a and a > 0]
    digits = [d for d in digits if d > 0]
    n = len(digits)
    counts = Counter(digits)
    observed = {d: counts.get(d, 0) / n if n else 0.0 for d in range(1, 10)}
    chi2 = sum(((counts.get(d, 0) - n * BENFORD_EXPECTED[d]) ** 2) / (n * BENFORD_EXPECTED[d]) for d in range(1, 10)) if n else 0.0
    # chi-square critical value, 8 degrees of freedom, alpha = 0.05
    critical = 15.507
    return {
        "n": n,
        "chi_square": round(chi2, 3),
        "critical_value_0_05": critical,
        "conforms": n < 30 or chi2 < critical,
        "note": "Benford's law needs >= 30 observations to be meaningful" if n < 30 else None,
        "observed": {str(d): round(observed[d], 3) for d in range(1, 10)},
        "expected": {str(d): round(BENFORD_EXPECTED[d], 3) for d in range(1, 10)},
    }


def _robust_z(values: List[float]) -> List[float]:
    arr = np.asarray(values, dtype=float)
    med = np.median(arr)
    mad = np.median(np.abs(arr - med)) or (np.std(arr) or 1.0)
    return list(0.6745 * (arr - med) / mad)


def build_features(invoices: List[dict]) -> np.ndarray:
    amounts = [float(i.get("amount") or 0) for i in invoices]
    vendors = [str(i.get("vendor") or "").strip().lower() for i in invoices]
    vendor_counts = Counter(vendors)
    by_vendor: Dict[str, List[int]] = defaultdict(list)
    for idx, v in enumerate(vendors):
        by_vendor[v].append(idx)
    vendor_z = [0.0] * len(invoices)
    for v, idxs in by_vendor.items():
        if len(idxs) >= 3:
            zs = _robust_z([amounts[i] for i in idxs])
            for i, z in zip(idxs, zs):
                vendor_z[i] = float(z)
    global_z = _robust_z(amounts) if len(amounts) >= 3 else [0.0] * len(amounts)
    dup_counts = Counter((v, round(a, 2)) for v, a in zip(vendors, amounts))
    rows = []
    for a, v, vz, gz in zip(amounts, vendors, vendor_z, global_z):
        rows.append([
            a,
            math.log1p(max(a, 0)),
            abs(vz),
            abs(gz),
            1.0 / vendor_counts[v],
            1.0 if a >= 500 and a == round(a, -2) else 0.0,
            1.0 if any(0 < t - a <= 0.02 * t for t in APPROVAL_THRESHOLDS) else 0.0,
            float(dup_counts[(v, round(a, 2))] - 1),
        ])
    return np.asarray(rows, dtype=float)


def _reasons(inv: dict, feats: np.ndarray, forest_flag: bool) -> List[str]:
    amount, _, vz, gz, vfreq, is_round, near_thr, dups = feats
    reasons = []
    if dups >= 1:
        reasons.append(f"Duplicate: {int(dups)} other invoice(s) from this vendor with identical amount ${amount:,.2f}")
    if near_thr:
        reasons.append("Amount sits just below an approval threshold (structuring pattern)")
    if vz > 3.5:
        reasons.append(f"Amount is {vz:.1f} robust-σ away from this vendor's median")
    if gz > 3.5:
        reasons.append(f"Amount is {gz:.1f} robust-σ away from the company-wide median")
    if is_round and amount >= 5000:
        reasons.append("Large perfectly round amount")
    if vfreq == 1.0 and amount >= 5000:
        reasons.append("First invoice ever from this vendor and it is large")
    if forest_flag and not reasons:
        reasons.append("Isolation Forest isolated this invoice as a multivariate outlier")
    return reasons


def score_invoices(invoices: List[dict], contamination: float = 0.08, random_state: int = 42) -> Dict:
    live = [i for i in invoices if not i.get("is_deleted")]
    if not live:
        return {"model": "none", "n": 0, "results": [], "benford": benford_test([]), "flagged": 0}
    X = build_features(live)
    forest_scores = np.zeros(len(live))
    forest_flags = np.zeros(len(live), dtype=bool)
    model_used = "rules_only"
    if len(live) >= MIN_SAMPLES_FOR_FOREST:
        forest = IsolationForest(n_estimators=200, contamination=contamination, random_state=random_state)
        forest.fit(X)
        raw = -forest.score_samples(X)
        lo, hi = raw.min(), raw.max()
        forest_scores = (raw - lo) / (hi - lo) if hi > lo else np.zeros_like(raw)
        forest_flags = forest.predict(X) == -1
        model_used = "isolation_forest+rules"
    results = []
    for inv, feats, fscore, fflag in zip(live, X, forest_scores, forest_flags):
        reasons = _reasons(inv, feats, bool(fflag))
        rule_score = min(1.0, 0.35 * len(reasons))
        score = round(float(max(fscore if fflag else fscore * 0.6, rule_score)), 3)
        results.append({
            "id": inv.get("id"), "number": inv.get("number"), "vendor": inv.get("vendor"),
            "amount": float(inv.get("amount") or 0), "status": inv.get("status"),
            "anomaly_score": score, "is_anomaly": bool(fflag or reasons),
            "severity": "high" if score >= 0.7 else "medium" if score >= 0.4 else "low",
            "reasons": reasons,
        })
    results.sort(key=lambda r: r["anomaly_score"], reverse=True)
    return {
        "model": model_used, "n": len(live),
        "flagged": sum(1 for r in results if r["is_anomaly"]),
        "benford": benford_test([r["amount"] for r in results]),
        "results": results,
    }
