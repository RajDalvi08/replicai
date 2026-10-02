"""Regression tests for section-aware experiment extraction."""

from backend.paper.experiment_extractor import build_experiment_payload


def _pages(texts: list[str]) -> list[dict]:
    return [{"page": i + 1, "text": t} for i, t in enumerate(texts)]


# ── Dataset extraction ────────────────────────────────────────────────────


def test_cifar10_detected_in_natural_language():
    pages = _pages([
        "4. Experiments\n4.2 CIFAR-10\n"
        "We conduct experiments on the CIFAR-10 dataset.\n"
        "We use a mini-batch size of 128 on 2 GPUs.\n"
        "We start with a learning rate of 0.1.\n"
        "We use a weight decay of 0.0001.\n"
    ])
    exps = build_experiment_payload(pages)
    cifar = next((e for e in exps if e.get("dataset") == "CIFAR-10"), None)
    assert cifar is not None, f"CIFAR-10 not found in {[e.get('dataset') for e in exps]}"
    assert cifar["batch_size"] == 128
    assert cifar["learning_rate"] == 0.1
    assert cifar["weight_decay"] == 0.0001


def test_wmt_dataset_detected():
    pages = _pages([
        "Our model achieves 28.4 BLEU on the "
        "WMT 2014 English-to-German translation task."
    ])
    exps = build_experiment_payload(pages)
    assert exps[0]["dataset"] == "WMT 2014 English-to-German"


# ── Model extraction ─────────────────────────────────────────────────────


def test_resnet_detected_not_output_map_size():
    pages = _pages([
        "4. Experiments\n"
        "We evaluate ResNet on image classification.\n"
        "Table 1. Network architectures\n"
        "layer name  output map size  filters\n"
    ])
    exps = build_experiment_payload(pages)
    model = exps[0].get("model")
    assert model is not None and "ResNet" in model
    assert "output map size" not in (model or "")


def test_transformer_detected():
    pages = _pages([
        "We propose a new architecture, the Transformer, "
        "based solely on attention mechanisms."
    ])
    exps = build_experiment_payload(pages)
    assert exps[0]["model"] == "Transformer"


# ── Metric disambiguation ────────────────────────────────────────────────


def test_map_not_selected_for_cifar10():
    pages = _pages([
        "4. Experiments\n4.2 CIFAR-10\n"
        "We evaluate on the CIFAR-10 dataset using ResNet.\n"
        "The test error is 6.43%.\n",
        "4.3 Object Detection\n"
        "We report mAP@.5 and mAP@[.5, .95] on COCO.\n",
    ])
    exps = build_experiment_payload(pages)
    cifar = next((e for e in exps if e.get("dataset") == "CIFAR-10"), None)
    if cifar:
        assert cifar.get("metric") != "map", "mAP should not be CIFAR-10 metric"


def test_accuracy_key_value_works():
    pages = _pages(["Accuracy: 87.6%"])
    exps = build_experiment_payload(pages)
    assert exps[0]["metric"] == "accuracy"
    assert exps[0]["reported_results"]["accuracy"]["value"] == 87.6


# ── Multi-experiment ──────────────────────────────────────────────────────


def test_subsections_yield_multiple_experiments():
    pages = _pages([
        "4. Experiments\n"
        "4.1 ImageNet Classification\n"
        "We evaluate on ImageNet with ResNet-50.\n"
        "The top-1 error of 23.6%.\n",
        "4.2 CIFAR-10\n"
        "We evaluate on the CIFAR-10 dataset.\n",
    ])
    exps = build_experiment_payload(pages)
    datasets = {e.get("dataset") for e in exps}
    assert "CIFAR-10" in datasets


# ── Evidence quality ─────────────────────────────────────────────────────


def test_evidence_quotes_are_real_sentences():
    pages = _pages([
        "Introduction paragraph here is long filler text.\n"
        "Experimental Setup\nBatch size: 64\nLearning rate: 0.01\n"
    ])
    exps = build_experiment_payload(pages)
    for item in exps[0].get("evidence", []):
        if item["field"] == "batch_size":
            assert "64" in (item.get("quote") or "")
            assert item.get("quote") != pages[0]["text"][:180]


def test_bleu_evidence_contains_value():
    pages = _pages([
        "Our model achieves 28.4 BLEU on the "
        "WMT 2014 English-to-German translation task."
    ])
    exps = build_experiment_payload(pages)
    ev = exps[0].get("evidence", [])
    bleu_ev = [e for e in ev if e["field"] == "metric"]
    assert bleu_ev
    assert "28.4 BLEU" in (bleu_ev[0].get("quote") or "")


# ── Empty / edge cases ───────────────────────────────────────────────────


def test_empty_pages_return_warning():
    exps = build_experiment_payload([{"page": 1, "text": ""}])
    assert exps[0]["warnings"]
    assert exps[0]["extraction_confidence"] == 0.0


def test_resnet_paper_multi_experiment():
    pages = _pages([
        "Deep Residual Learning for Image Recognition\nAbstract\nWe present a residual learning framework.",
        "4. Experiments\n"
        "4.1. ImageNet Classification\n"
        "We evaluate our method on the ImageNet 2012 classification dataset.\n"
        "We evaluate ResNet-34 and ResNet-152.\n"
        "The learning rate starts from 0.1. We use a mini-batch size of 256.\n"
        "Weight decay of 0.0001 and SGD with momentum 0.9.\n"
        "ResNet-152 achieves a top-5 error rate of 3.57% on the ImageNet validation set.\n",
        "4.2. CIFAR-10 and Analysis\n"
        "We conduct more studies on the CIFAR-10 dataset.\n"
        "We test ResNet-110. The learning rate starts from 0.1. Mini-batch size of 128.\n"
        "Our ResNet-110 achieves test error 6.43% on CIFAR-10.\n",
    ])
    exps = build_experiment_payload(pages)
    assert len(exps) >= 2

    # Exp 1: ImageNet
    exp1 = exps[0]
    assert exp1["dataset"] == "ImageNet"
    assert "ResNet" in exp1["model"]
    assert exp1["model"] != "output map size"
    assert exp1["optimizer"] == "SGD"
    assert exp1["learning_rate"] == 0.1
    assert exp1["batch_size"] == 256
    assert exp1["metric"] == "error"
    assert exp1["reported_results"]["error"]["value"] == 3.57

    # Exp 2: CIFAR-10
    exp2 = exps[1]
    assert exp2["dataset"] == "CIFAR-10"
    assert "ResNet" in exp2["model"]
    assert exp2["learning_rate"] == 0.1
    assert exp2["batch_size"] == 128
    assert exp2["metric"] == "error"
    assert exp2["reported_results"]["error"]["value"] == 6.43

