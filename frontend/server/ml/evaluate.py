"""Evaluation harness: synthetic labelled invoices -> precision / recall / F1 for the detector."""
from __future__ import annotations

import random
from typing import Dict, List, Tuple

from ml.anomaly import score_invoices

VENDORS = ["CloudNet", "PixelPress", "Northwind", "Aurora", "Silverline", "OfficePro", "PowerPlus", "CableWorks"]


def generate_dataset(n: int = 200, fraud_rate: float = 0.1, seed: int = 42) -> Tuple[List[dict], Dict[str, bool]]:
    rng = random.Random(seed)
    vendor_mu = {v: rng.uniform(5.5, 8.5) for v in VENDORS}
    invoices, labels = [], {}
    n_fraud = max(1, int(n * fraud_rate))
    for i in range(n - n_fraud):
        v = rng.choice(VENDORS)
        amt = round(rng.lognormvariate(vendor_mu[v], 0.35), 2)
        inv = {"id": f"n{i}", "number": f"INV-{1000 + i}", "vendor": v, "amount": amt, "status": "unpaid"}
        invoices.append(inv)
        labels[inv["id"]] = False
    patterns = ["duplicate", "structuring", "outlier", "round_large", "new_vendor"]
    for j in range(n_fraud):
        kind = patterns[j % len(patterns)]
        v = rng.choice(VENDORS)
        if kind == "duplicate":
            src = rng.choice([x for x in invoices if not labels[x["id"]]])
            inv = {**src, "id": f"f{j}", "number": f"INV-9{j:03d}"}
        elif kind == "structuring":
            thr = rng.choice([1000, 5000, 10000, 25000])
            inv = {"id": f"f{j}", "number": f"INV-9{j:03d}", "vendor": v, "amount": round(thr - rng.uniform(1, thr * 0.015), 2), "status": "unpaid"}
        elif kind == "outlier":
            inv = {"id": f"f{j}", "number": f"INV-9{j:03d}", "vendor": v, "amount": round(rng.lognormvariate(vendor_mu[v] + 2.5, 0.2), 2), "status": "unpaid"}
        elif kind == "round_large":
            inv = {"id": f"f{j}", "number": f"INV-9{j:03d}", "vendor": v, "amount": float(rng.choice([10000, 20000, 50000])), "status": "unpaid"}
        else:
            inv = {"id": f"f{j}", "number": f"INV-9{j:03d}", "vendor": f"ShellCo-{j}", "amount": round(rng.uniform(8000, 40000), 2), "status": "unpaid"}
        invoices.append(inv)
        labels[inv["id"]] = True
    rng.shuffle(invoices)
    return invoices, labels


def evaluate(n: int = 200, fraud_rate: float = 0.1, seed: int = 42) -> Dict:
    invoices, labels = generate_dataset(n, fraud_rate, seed)
    report = score_invoices(invoices)
    tp = fp = fn = tn = 0
    for r in report["results"]:
        truth, pred = labels[r["id"]], r["is_anomaly"]
        tp += truth and pred
        fp += (not truth) and pred
        fn += truth and (not pred)
        tn += (not truth) and (not pred)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "dataset": {"n": n, "fraud_rate": fraud_rate, "seed": seed, "positives": sum(labels.values())},
        "model": report["model"],
        "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn},
        "precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3),
        "benford": report["benford"],
    }


if __name__ == "__main__":
    import json
    print(json.dumps(evaluate(), indent=2))
