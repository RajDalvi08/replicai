"""Synthetic research repository fixture.

This file is *data* for the Code Intelligence tests. It is never imported or
executed by the test suite; it is only read as text and parsed with ``ast``.
"""

import argparse
import json
import os
import random

import numpy as np
import torch
from dataset import ToySequenceDataset
from model import EncoderClassifier
from torch import nn
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR
from torch.utils.data import DataLoader

# --- configuration -----------------------------------------------------------
learning_rate = 0.001
batch_size = 64
epochs = 10
weight_decay = 0.01
dropout = 0.1
seed = 42
dataset_name = "synthetic-toy-corpus"
model_name = "EncoderClassifier"
metric = "accuracy"


class TrainingConfig:
    def __init__(self, lr, bs, num_epochs, wd, drop):
        self.lr = lr
        self.bs = bs
        self.num_epochs = num_epochs
        self.wd = wd
        self.drop = drop


def build_parser():
    parser = argparse.ArgumentParser(description="Train the toy encoder classifier")
    parser.add_argument("--learning_rate", type=float, default=learning_rate)
    parser.add_argument("--batch_size", type=int, default=batch_size)
    parser.add_argument("--epochs", type=int, default=epochs)
    parser.add_argument("--seed", type=int, default=seed)
    parser.add_argument("--resume", type=str, default=None)
    return parser


def set_seed(random_seed):
    random.seed(random_seed)
    np.random.seed(random_seed)
    torch.manual_seed(random_seed)


def build_loaders():
    dataset = ToySequenceDataset(size=2048, length=32)
    loader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    return loader


def build_model():
    model = EncoderClassifier(
        vocab_size=128, hidden_size=256, num_layers=2, dropout=dropout
    )
    return model


def train(loader, model, config, output_dir):
    criterion = nn.CrossEntropyLoss()
    optimizer = AdamW(
        model.parameters(),
        lr=config.lr,
        weight_decay=config.wd,
    )
    scheduler = CosineAnnealingLR(optimizer, T_max=config.num_epochs)

    for epoch in range(config.num_epochs):
        model.train()
        total_loss = 0.0
        for inputs, labels in loader:
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
        scheduler.step()
        print(f"epoch={epoch} loss={total_loss:.4f}")

    os.makedirs(output_dir, exist_ok=True)
    torch.save(model.state_dict(), os.path.join(output_dir, "checkpoint.pt"))
    return model


def main():
    args = build_parser().parse_args()
    set_seed(args.seed)
    config = TrainingConfig(
        lr=args.learning_rate,
        bs=args.batch_size,
        num_epochs=args.epochs,
        wd=weight_decay,
        drop=dropout,
    )
    loader = build_loaders()
    model = build_model()
    model = train(loader, model, config, "runs/experiment")
    results = evaluate(model, loader)
    with open("runs/experiment/metrics.json", "w", encoding="utf-8") as handle:
        json.dump(results, handle, indent=2)


if __name__ == "__main__":
    main()
