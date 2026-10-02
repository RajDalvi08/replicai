"""Evaluation script for the synthetic research repository fixture."""


def evaluate(model, loader):
    model.eval()
    correct = 0
    total = 0
    with torch.no_grad():
        for inputs, labels in loader:
            outputs = model(inputs)
            predictions = outputs.argmax(dim=-1)
            correct += (predictions == labels).sum().item()
            total += labels.numel()
    accuracy = correct / total if total else 0.0
    return {"accuracy": accuracy}


def run_evaluation(checkpoint_path, loader):
    model = build_model()
    model.load_state_dict(torch.load(checkpoint_path))
    return evaluate(model, loader)
