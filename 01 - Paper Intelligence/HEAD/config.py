"""Static configuration for the synthetic research repository fixture."""

DEFAULT_CONFIG = {
    "learning_rate": 0.001,
    "batch_size": 64,
    "epochs": 10,
    "weight_decay": 0.01,
    "dropout": 0.1,
    "random_seed": 42,
    "dataset": "synthetic-toy-corpus",
    "model": "EncoderClassifier",
    "metric": "accuracy",
    "scheduler": "CosineAnnealingLR",
    "optimizer": "AdamW",
    "loss_function": "CrossEntropyLoss",
}

SWEEP_CONFIG = {
    "lr": 0.0001,
    "bs": 32,
    "n_epochs": 5,
}

OUTPUT_DIR = "runs/experiment"
