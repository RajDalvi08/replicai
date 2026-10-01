STRICT_EXTRACTION_PROMPT = """
You are extracting structured research results from an academic paper PDF.
Return only valid JSON that matches the expected schema. Never invent values.
Use null when a value is not explicitly present.
Every important extracted value must include evidence with page number, quote, and confidence.
Follow these rules:
- Identify experiments from sections such as Experiments, Experimental Setup, Results, Ablation, Evaluation, Benchmark, Comparison.
- Extract only values explicitly stated in the paper.
- Use page numbers and table/section references from the text when available.
- Distinguish explicit facts from inferred values.
- If a value is not present, set it to null.
- For reported_results, use a mapping by metric name with value/unit/higher_is_better.
- Preserve evidence for every significant extraction.
- Do not fabricate page numbers or quotes.
Return JSON in this shape:
{
  "experiments": [
    {
      "experiment_id": "exp-1",
      "title": "Training setup",
      "description": "...",
      "dataset": "CIFAR-10",
      "model": "ResNet-50",
      "optimizer": "SGD",
      "learning_rate": 0.01,
      "batch_size": 64,
      "epochs": 50,
      "scheduler": null,
      "weight_decay": null,
      "dropout": null,
      "random_seed": 42,
      "metric": "accuracy",
      "reported_results": {
        "accuracy": {"value": 87.6, "unit": "%", "higher_is_better": true}
      },
      "procedure": "...",
      "evidence": [
        {"field": "batch_size", "value": 64, "page": 7, "source_type": "table", "source_label": "Table 3", "quote": "batch size 64", "confidence": 0.96}
      ],
      "extraction_confidence": 0.85,
      "warnings": []
    }
  ]
}
"""
