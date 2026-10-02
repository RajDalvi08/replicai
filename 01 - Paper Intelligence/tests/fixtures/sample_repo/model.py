"""Model definition for the synthetic research repository fixture."""

from torch import nn


class EncoderClassifier(nn.Module):
    def __init__(self, vocab_size, hidden_size, num_layers, dropout):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, hidden_size)
        self.dropout = nn.Dropout(dropout)
        self.encoder = nn.GRU(hidden_size, hidden_size, num_layers=num_layers, batch_first=True)
        self.classifier = nn.Linear(hidden_size, 2)

    def forward(self, inputs):
        embedded = self.dropout(self.embedding(inputs))
        outputs, _ = self.encoder(embedded)
        return self.classifier(outputs[:, -1, :])
