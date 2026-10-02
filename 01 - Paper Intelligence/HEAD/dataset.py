"""Dataset code for the synthetic research repository fixture."""

import torch
from torch.utils.data import Dataset


class ToySequenceDataset(Dataset):
    def __init__(self, size, length):
        self.size = size
        self.length = length
        self.inputs = torch.randint(0, 128, (size, length))
        self.labels = torch.randint(0, 2, (size,))

    def __len__(self):
        return self.size

    def __getitem__(self, index):
        return self.inputs[index], self.labels[index]
