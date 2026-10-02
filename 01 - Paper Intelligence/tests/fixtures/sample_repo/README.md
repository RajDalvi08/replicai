# Synthetic Research Repository

A minimal, self-contained research codebase used to exercise the ReplicAI
Code Intelligence analyzers. It contains:

- `train.py` — training entry point with an argparse CLI, a fixed seed, an
  `AdamW` optimizer, a `CosineAnnealingLR` scheduler and a checkpoint write
- `evaluate.py` — evaluation entry point computing accuracy
- `config.py` — dictionary based configuration plus alias names (`lr`, `bs`)
- `model.py` — an `nn.Module` subclass
- `dataset.py` — a `torch.utils.data.Dataset` subclass

The expected paper parameters for this repository live in
`tests/fixtures/sample_repo_expected.json`.