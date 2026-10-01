import json

from backend.paper.llm import StructuredLLMAdapter


def test_llm_retries_after_malformed_json(monkeypatch):
    calls = []

    class FirstResponse:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "not valid json"}}]}

    class SecondResponse:
        status_code = 200

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "experiments": [
                                        {
                                            "experiment_id": "exp-1",
                                            "title": "Translation run",
                                            "description": "A valid extracted experiment.",
                                            "dataset": "WMT 2014 English-to-German",
                                            "model": "Transformer",
                                            "optimizer": "Adam",
                                            "learning_rate": 0.0003,
                                            "batch_size": 4096,
                                            "epochs": 100,
                                            "scheduler": None,
                                            "weight_decay": None,
                                            "dropout": None,
                                            "random_seed": 42,
                                            "metric": "BLEU",
                                            "reported_results": {
                                                "BLEU": {
                                                    "value": 28.4,
                                                    "unit": "",
                                                    "higher_is_better": True,
                                                }
                                            },
                                            "procedure": "Train the transformer model.",
                                            "evidence": [],
                                            "extraction_confidence": 0.9,
                                            "warnings": [],
                                        }
                                    ]
                                }
                            )
                        }
                    }
                ]
            }

    def fake_post(self, url, headers=None, json=None):
        calls.append((url, json))
        return FirstResponse() if len(calls) == 1 else SecondResponse()

    monkeypatch.setattr("httpx.Client.post", fake_post)

    adapter = StructuredLLMAdapter(
        api_key="test-key",
        base_url="https://example.test/v1/chat/completions",
        model="gpt-test",
    )
    experiments = adapter.extract_experiments([{"page": 1, "text": "Transformer"}])

    assert len(experiments) == 1
    assert experiments[0]["model"] == "Transformer"
    assert len(calls) == 2
