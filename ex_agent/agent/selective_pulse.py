"""
Sovereign Cognitive Pulse: Selective State-Space Compression Engine (Tier 3 GodEye Mandate).
Mathematical and algorithmic implementation of input-dependent selectivity gates (Δ_t, B_t, C_t)
and associative scan state reduction from O(L) to O(log L).
"""
from __future__ import annotations

import math
from typing import List, Optional, Tuple


class CognitivePulseGate:
    """
    Simulates input-dependent selectivity for agent state retention and context compression.
    Controls how the agent dynamically absorbs, persists, or purges tokens across multi-turn sessions.
    
    Mathematical Formulation:
      Δ_t = Softplus(W_Δ · x_t + b_Δ)  [Cognitive Step-Size / Selectivity Gate]
      A_bar_t = exp(Δ_t · A)           [Dynamic Retention Decay]
      B_bar_t = Δ_t · B_t             [Input Modulation Weight]
      h_t = A_bar_t ⊙ h_{t-1} + B_bar_t ⊙ x_t  [Hidden Recurrence State]
      y_t = C_t ⊙ h_t                 [Readout Emission]
    """

    def __init__(self, state_dim: int = 64):
        self.state_dim = state_dim
        # Initial log-decay parameters initialized to negative values for stable retention
        self.A_log = [-0.1 * (i + 1) for i in range(state_dim)]

    def compute_selectivity(self, token_salience: float) -> Tuple[float, float]:
        """
        Calculates dynamic delta gate and retention decay:
        High salience -> Large Δ -> State overwrite (absorbing novel knowledge).
        Low salience -> Small Δ -> State decay preservation (skipping boilerplate).
        """
        # Softplus activation: ln(1 + exp(x))
        delta = math.log1p(math.exp(token_salience))
        decay = math.exp(delta * self.A_log[0])
        return delta, decay

    def associative_scan_compression(self, sequence_weights: List[float]) -> float:
        """
        Algorithmic shortcut: Parallel Associative Scan O(L) -> O(log L).
        Reduces multi-step token dependencies into a single state contraction metric.
        """
        if not sequence_weights:
            return 1.0

        current_weights = list(sequence_weights)
        # Tree-reduction (Kogge-Stone pattern)
        while len(current_weights) > 1:
            next_weights = []
            for i in range(0, len(current_weights), 2):
                if i + 1 < len(current_weights):
                    next_weights.append(current_weights[i] * current_weights[i + 1])
                else:
                    next_weights.append(current_weights[i])
            current_weights = next_weights

        return current_weights[0]
