from ml.anomaly import benford_test, score_invoices
from ml.evaluate import evaluate


def test_benford_flags_uniform_first_digits():
    uniform = [float(f"{d}00") for d in range(1, 10)] * 10
    assert benford_test(uniform)["conforms"] is False


def test_benford_accepts_log_uniform_amounts():
    import random
    rng = random.Random(1)
    amounts = [10 ** rng.uniform(1, 5) for _ in range(400)]
    assert benford_test(amounts)["conforms"] is True


def test_duplicate_invoice_is_detected():
    base = [{"id": str(i), "number": f"I{i}", "vendor": "Acme", "amount": 100 + i * 7} for i in range(15)]
    base.append({"id": "dup", "number": "DUP", "vendor": "Acme", "amount": 107})
    report = score_invoices(base)
    dup = next(r for r in report["results"] if r["id"] == "dup")
    assert dup["is_anomaly"] and any("Duplicate" in r for r in dup["reasons"])


def test_structuring_just_below_threshold_is_detected():
    base = [{"id": str(i), "number": f"I{i}", "vendor": "V", "amount": 200 + i * 13} for i in range(20)]
    base.append({"id": "s", "number": "S", "vendor": "V", "amount": 4990})
    report = score_invoices(base)
    hit = next(r for r in report["results"] if r["id"] == "s")
    assert hit["is_anomaly"] and any("threshold" in r for r in hit["reasons"])


def test_small_population_falls_back_to_rules():
    report = score_invoices([{"id": "a", "number": "A", "vendor": "V", "amount": 120}])
    assert report["model"] == "rules_only" and report["flagged"] == 0


def test_evaluation_harness_meets_quality_bar():
    result = evaluate(n=300, fraud_rate=0.1, seed=7)
    assert result["recall"] >= 0.7, result
    assert result["precision"] >= 0.5, result
