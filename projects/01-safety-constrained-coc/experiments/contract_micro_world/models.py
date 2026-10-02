from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import torch
from torch import nn

from .micro_world import featurize


class TinyPolicy(nn.Module):
    def __init__(self, input_dim: int, hidden_dim: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, hidden_dim),
            nn.Tanh(),
            nn.Linear(hidden_dim, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


@dataclass(frozen=True)
class TrainingSummary:
    final_loss: float
    epochs: int
    examples: int
    parameters: int


def train_policy(
    transitions,
    variant: str,
    seed: int,
    epochs: int = 35,
    batch_size: int = 512,
) -> tuple[TinyPolicy, TrainingSummary]:
    torch.manual_seed(seed)
    np.random.seed(seed)
    x_np = np.stack([featurize(state, variant) for state, _ in transitions]).astype(np.float32)
    y_np = np.asarray([action for _, action in transitions], dtype=np.float32)
    x = torch.from_numpy(x_np)
    y = torch.from_numpy(y_np)
    model = TinyPolicy(x.shape[1])
    optimizer = torch.optim.AdamW(model.parameters(), lr=2e-3, weight_decay=1e-5)
    generator = torch.Generator().manual_seed(seed + 1000)
    last_loss = float("nan")
    model.train()
    for _ in range(epochs):
        permutation = torch.randperm(len(x), generator=generator)
        total = 0.0
        seen = 0
        for start in range(0, len(x), batch_size):
            index = permutation[start : start + batch_size]
            prediction = model(x[index])
            loss = nn.functional.smooth_l1_loss(prediction, y[index])
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
            total += float(loss.detach()) * len(index)
            seen += len(index)
        last_loss = total / seen
    model.eval()
    parameters = sum(p.numel() for p in model.parameters())
    return model, TrainingSummary(last_loss, epochs, len(x), parameters)


def policy_callable(model: TinyPolicy):
    def predict(features: np.ndarray) -> float:
        with torch.no_grad():
            tensor = torch.from_numpy(features.astype(np.float32)).unsqueeze(0)
            return float(model(tensor).item())

    return predict

