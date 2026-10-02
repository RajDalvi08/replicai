"""Section-aware experiment extraction from academic paper text.

Replaces naive full-text regex with contextual extraction that:
1. Detects section/subsection headings to segment the paper.
2. Resolves datasets, models, optimizers via known-entity vocabularies.
3. Extracts config with natural-language patterns (not just key=value).
4. Generates evidence with real quotes and correct page numbers.
5. Returns multiple experiments for papers with distinct subsections.
"""

from __future__ import annotations

import re
from typing import Any

# ── Known entities (longest-first for greedy match) ────────────────────────

_KNOWN_DATASETS: list[str] = [
    "WMT 2014 English-to-German", "WMT 2014 English-to-French",
    "Fashion-MNIST", "CIFAR-100", "CIFAR-10",
    "ImageNet", "ILSVRC 2012", "WMT 2014",
    "MS COCO", "Pascal VOC", "VOC 2007", "VOC 2012",
    "SuperGLUE", "SQuAD", "GLUE", "MNIST", "SVHN", "STL-10", "COCO",
    "Penn Treebank", "WikiText-103", "WikiText",
    "Cityscapes", "ADE20K", "LibriSpeech", "CelebA", "LSUN",
]

_KNOWN_MODELS: list[str] = [
    "Faster R-CNN", "Wide ResNet", "WideResNet", "ResNeXt", "ResNet",
    "VGG", "AlexNet", "GoogLeNet", "Inception", "DenseNet",
    "EfficientNet", "MobileNet", "ShuffleNet",
    "Transformer", "BERT", "GPT", "T5", "RoBERTa", "XLNet",
    "LSTM", "GRU", "BiLSTM", "U-Net", "SegNet", "DeepLab",
    "YOLO", "SSD", "RetinaNet", "ViT", "DeiT", "Swin", "MLP",
]

_KNOWN_OPTIMIZERS: list[str] = [
    "SGD", "Adam", "AdamW", "Adagrad", "RMSprop", "Adadelta", "LAMB", "LARS",
]

# ── Heading patterns ──────────────────────────────────────────────────────

_SECTION_RE = re.compile(
    r"(?:^|\n)\s*(?:\d+(?:\.\d+)*\.?\s+)?"
    r"(experiment(?:s|al)?(?:\s+(?:setup|results?|settings?|evaluation|details?))?"
    r"|evaluation(?:\s+results?)?"
    r"|results?(?:\s+and\s+(?:discussion|analysis))?"
    r"|ablation\s+stud(?:y|ies)"
    r"|training\s+details?"
    r"|implementation\s+details?)"
    r"\s*(?:\n|$)",
    re.IGNORECASE,
)

_SUBSECTION_RE = re.compile(r"(?:^|\n)\s*(\d+\.\d+\.?\s+[A-Z].+?)\s*(?:\n|$)")

# ── Quote helpers ─────────────────────────────────────────────────────────


def _sentence_around(text: str, start: int, end: int, max_len: int = 200) -> str:
    s = start
    while s > 0:
        c = text[s - 1]
        if c == "\n":
            break
        if c == ".":
            is_decimal = (
                s >= 2 and text[s - 2].isdigit() and s < len(text) and text[s].isdigit()
            )
            if not is_decimal:
                break
        s -= 1

    e = end
    while e < len(text):
        c = text[e]
        if c == "\n":
            break
        if c == ".":
            is_decimal = (
                e > 0 and text[e - 1].isdigit() and e + 1 < len(text) and text[e + 1].isdigit()
            )
            if not is_decimal:
                e += 1  # Include trailing sentence-ending period
                break
        e += 1

    quote = text[s:e].strip()
    if len(quote) > max_len:
        mid = (start + end) // 2 - s
        qs = max(0, mid - max_len // 2)
        quote = quote[qs : qs + max_len].strip()
    return quote


def _quote_for(text: str, needle: str) -> str | None:
    idx = text.lower().find(needle.lower())
    if idx < 0:
        return None
    return _sentence_around(text, idx, idx + len(needle))


def _page_with(pages: list[dict[str, Any]], needle: str) -> int:
    low = needle.lower()
    for p in pages:
        if low in p.get("text", "").lower():
            return p.get("page", 1)
    return pages[0].get("page", 1) if pages else 1


def _text_of(pages: list[dict[str, Any]], page_num: int) -> str:
    for p in pages:
        if p.get("page") == page_num:
            return p.get("text", "")
    return ""


# ── Entity lookup ─────────────────────────────────────────────────────────


def _lookup(
    text: str, vocab: list[str], *, allow_suffix: bool = False,
) -> tuple[str | None, re.Match[str] | None]:
    for name in vocab:
        if allow_suffix:
            pat = rf"\b{re.escape(name)}(?:\s*[-/]?\s*\d+[A-Za-z]*)?\b"
        elif len(name) <= 3:
            pat = rf"\b{re.escape(name)}\b"
        else:
            pat = rf"(?<![A-Za-z]){re.escape(name)}"
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return (m.group(0).strip() if allow_suffix else name), m
    return None, None


# ── Config extraction ─────────────────────────────────────────────────────

_CONFIG: dict[str, tuple[list[str], type | None]] = {
    "learning_rate": ([
        r"learning\s+rate\s+(?:of\s+|is\s+|starts?\s+(?:at|from)\s+)?(\d+\.?\d*(?:e[+-]?\d+)?)",
        r"learning\s+rate\s*[:=]\s*(\d+\.?\d*(?:e[+-]?\d+)?)",
        r"\blr\s*[:=]\s*(\d+\.?\d*(?:e[+-]?\d+)?)",
    ], float),
    "batch_size": ([
        r"(?:mini-?)?batch\s+size\s+(?:of\s+|is\s+)?(\d+)",
        r"(?:mini-?)?batch[\s_-]*size\s*[:=]\s*(\d+)",
        r"batches\s+of\s+(\d+)",
    ], int),
    "epochs": ([
        r"(?:for\s+)?(\d+)\s+epochs?\b",
        r"epochs?\s*[:=]\s*(\d+)",
    ], int),
    "weight_decay": ([
        r"weight\s+decay\s+(?:of\s+|is\s+)?(\d+\.?\d*(?:e[+-]?\d+)?)",
        r"weight\s+decay\s*[:=]\s*(\d+\.?\d*(?:e[+-]?\d+)?)",
    ], float),
    "dropout": ([
        r"dropout\s+(?:rate\s+)?(?:of\s+)?(\d+\.?\d*)",
        r"dropout\s*[:=]\s*(\d+\.?\d*)",
    ], float),
    "random_seed": ([r"(?:random\s+)?seed\s*[:=]\s*(\d+)"], int),
    "scheduler": ([r"(?:learning\s+rate\s+)?scheduler\s*[:=]\s*([A-Za-z0-9 _-]+)"], None),
}


def _match_config(
    text: str, patterns: list[str], cast: type | None,
) -> tuple[Any | None, re.Match[str] | None]:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            raw = m.group(1).strip()
            if cast is not None:
                try:
                    return cast(raw), m
                except (ValueError, TypeError):
                    continue
            return raw, m
    return None, None


# ── Metric / result extraction ────────────────────────────────────────────

# (pattern, value_group, metric_group_or_literal, higher_is_better)
_RESULT_RULES: list[tuple[str, int, int | str, bool]] = [
    (r"achiev\w*\s+(\d+\.?\d*)\s*%?\s*(accuracy|BLEU|F1|precision|recall|mIoU)\b", 1, 2, True),
    (r"\b(accuracy|BLEU|F1|precision|recall|perplexity)\s+(?:score\s+)?(?:of\s+)?(\d+\.?\d*)\s*%?", 2, 1, True),
    (r"(\d+\.?\d*)\s+(BLEU)\b", 1, 2, True),
    (r"(?:top-\d+\s+)?error\s+(?:rate\s+)?(?:of\s+)?(\d+\.?\d*)\s*%?", 1, "error", False),
    (r"test\s+error\s+(\d+\.?\d*)\s*%?", 1, "error", False),
    (r"\b(accuracy|BLEU|F1|precision|recall|loss|perplexity)\s*[:=]\s*(\d+\.?\d*)\s*%?", 2, 1, True),
]


def _find_results(text: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for pat, vg, mg, hib in _RESULT_RULES:
        for m in re.finditer(pat, text, re.IGNORECASE):
            val = float(m.group(vg))
            met = m.group(mg).lower() if isinstance(mg, int) else mg
            if met in seen:
                continue
            if met in {"loss", "perplexity", "error"}:
                hib = False
            seen.add(met)
            out.append({
                "metric": met, "value": val,
                "unit": "%" if "%" in m.group(0) else "",
                "higher_is_better": hib,
                "text": m.group(0),
            })
    return out


# ── Context segmentation ─────────────────────────────────────────────────


def _experiment_start(pages: list[dict[str, Any]]) -> int | None:
    for i, p in enumerate(pages):
        if _SECTION_RE.search(p.get("text", "")):
            return i
    return None


def _split_subsections(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ctxs: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None

    for page in pages:
        text = page.get("text", "")
        pnum = page.get("page", 0)
        subs = list(_SUBSECTION_RE.finditer(text))

        if subs:
            pre = text[: subs[0].start()].strip()
            if pre:
                if cur is not None:
                    cur["pages"].append({"page": pnum, "text": pre})
                else:
                    cur = {"title": None, "pages": [{"page": pnum, "text": pre}]}

            for i, sub in enumerate(subs):
                if cur is not None:
                    ctxs.append(cur)
                seg_end = subs[i + 1].start() if i + 1 < len(subs) else len(text)
                cur = {
                    "title": sub.group(1).strip(),
                    "pages": [{"page": pnum, "text": text[sub.start() : seg_end]}],
                }
        elif cur is not None:
            cur["pages"].append({"page": pnum, "text": text})
        else:
            cur = {"title": None, "pages": [{"page": pnum, "text": text}]}

    if cur is not None:
        ctxs.append(cur)

    for c in ctxs:
        c["combined"] = "\n".join(p.get("text", "") for p in c["pages"])
    return ctxs


def _contexts(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    start = _experiment_start(pages)
    target = pages[start:] if start is not None else pages
    ctxs = _split_subsections(target)
    if not ctxs:
        ctxs = [{
            "title": None,
            "pages": [{"page": p["page"], "text": p.get("text", "")} for p in pages],
            "combined": "\n".join(p.get("text", "") for p in pages),
        }]
    return ctxs


# ── Per-context extraction ────────────────────────────────────────────────


def _make_evidence(
    field: str, value: Any, pages: list[dict[str, Any]],
    text: str, needle: str, confidence: float = 0.90,
) -> dict[str, Any]:
    pg = _page_with(pages, needle)
    q = _quote_for(_text_of(pages, pg) or text, needle) or needle
    src = "table" if "table" in q.lower() else "text"
    return {
        "field": field, "value": value, "page": pg,
        "source_type": src, "source_label": "Table" if src == "table" else "Text",
        "quote": q, "confidence": confidence,
    }


def _extract(ctx: dict[str, Any], idx: int) -> dict[str, Any]:
    text = ctx["combined"]
    cpages = ctx["pages"]
    ev: list[dict[str, Any]] = []
    warns: list[str] = []
    title = ctx.get("title") or "Experimental setup"

    # Dataset
    dataset, ds_m = _lookup(text, _KNOWN_DATASETS)
    if dataset:
        ev.append(_make_evidence("dataset", dataset, cpages, text, dataset, 0.92))

    # Model
    model, mdl_m = _lookup(text, _KNOWN_MODELS, allow_suffix=True)
    if model and mdl_m:
        ev.append(_make_evidence("model", model, cpages, text, mdl_m.group(0), 0.90))

    # Optimizer
    optimizer, _ = _lookup(text, _KNOWN_OPTIMIZERS)
    if optimizer:
        ev.append(_make_evidence("optimizer", optimizer, cpages, text, optimizer, 0.88))

    # Config fields
    cfg: dict[str, Any] = {}
    for field, (pats, cast) in _CONFIG.items():
        val, m = _match_config(text, pats, cast)
        if val is not None and m is not None:
            cfg[field] = val
            ev.append(_make_evidence(field, val, cpages, text, m.group(0), 0.90))

    # Metrics / results
    results = _find_results(text)
    primary = results[0] if results else None
    reported: dict[str, dict[str, Any]] = {}
    for r in results:
        reported[r["metric"]] = {
            "value": r["value"], "unit": r["unit"],
            "higher_is_better": r["higher_is_better"],
        }
        ev.append(_make_evidence("metric", r["value"], cpages, text, r["text"], 0.92))

    # Description
    parts = []
    if dataset:
        parts.append(f"Experiment on {dataset}")
    if model:
        parts.append(f"using {model}")
    desc = " ".join(parts) + "." if parts else "Training procedure described in the paper."

    if not ev:
        warns.append("No explicit experiment parameters were identified from page text.")

    return {
        "experiment_id": f"exp-{idx}",
        "title": title,
        "description": desc,
        "dataset": dataset,
        "model": model,
        "optimizer": optimizer,
        "learning_rate": cfg.get("learning_rate"),
        "batch_size": cfg.get("batch_size"),
        "epochs": cfg.get("epochs"),
        "scheduler": cfg.get("scheduler"),
        "weight_decay": cfg.get("weight_decay"),
        "dropout": cfg.get("dropout"),
        "random_seed": cfg.get("random_seed"),
        "metric": primary["metric"] if primary else None,
        "reported_results": reported,
        "procedure": desc,
        "evidence": ev,
        "extraction_confidence": 0.8,
        "warnings": warns,
    }


# ── Public API ────────────────────────────────────────────────────────────


def build_experiment_payload(pages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract structured experiments from PDF page dicts.

    Each page dict must have ``page`` (int) and ``text`` (str).
    Returns a list of experiment dicts matching the Experiment schema.
    """
    if not pages or not any(p.get("text") for p in pages):
        return [{
            "experiment_id": "exp-1",
            "title": "Unspecified experiment",
            "description": "No extractable text was found in the PDF.",
            "dataset": None, "model": None, "optimizer": None,
            "learning_rate": None, "batch_size": None, "epochs": None,
            "scheduler": None, "weight_decay": None, "dropout": None,
            "random_seed": None, "metric": None, "reported_results": {},
            "procedure": None, "evidence": [],
            "extraction_confidence": 0.0,
            "warnings": ["No experiment text was detected in the PDF."],
        }]

    ctxs = _contexts(pages)
    experiments = []
    for i, ctx in enumerate(ctxs, 1):
        exp = _extract(ctx, i)
        if exp["evidence"] or exp["dataset"] or exp["model"] or exp["metric"]:
            experiments.append(exp)

    # Fallback: no contexts produced results → extract from all pages
    if not experiments:
        fallback = {
            "title": None,
            "pages": [{"page": p["page"], "text": p.get("text", "")} for p in pages],
            "combined": "\n".join(p.get("text", "") for p in pages),
        }
        experiments = [_extract(fallback, 1)]

    return experiments
