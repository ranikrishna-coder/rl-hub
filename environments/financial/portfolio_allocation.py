"""Portfolio Allocation RL Environment - Multi-asset portfolio optimization with CRRA utility rewards"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics, RewardWeights


def _generate_correlated_assets(n_assets: int = 5, n_days: int = 2000, seed: int = None):
    """Generate correlated synthetic asset returns and prices."""
    rng = np.random.default_rng(seed)
    mus = rng.uniform(0.0001, 0.0004, n_assets)
    sigmas = rng.uniform(0.01, 0.025, n_assets)
    # Random correlation via Cholesky
    A = rng.standard_normal((n_assets, n_assets))
    cov = A @ A.T
    D = np.diag(1.0 / np.sqrt(np.diag(cov)))
    corr = D @ cov @ D
    L = np.linalg.cholesky(corr)
    raw = rng.standard_normal((n_days, n_assets))
    correlated = raw @ L.T
    returns = mus + sigmas * correlated
    prices = 100.0 * np.exp(np.cumsum(returns, axis=0))
    return prices, returns


class PortfolioAllocationEnv(HealthcareRLEnvironment):
    """
    Multi-asset portfolio allocation environment.

    The agent outputs portfolio weights across N assets at each step.
    Rewards use CRRA utility to balance return and risk aversion.

    State: recent asset returns (N*lookback) + current weights (N) + portfolio stats (4)
    Actions: continuous portfolio weights (normalized to sum=1)
    """
    ACTIONS = ["rebalance_portfolio"]

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        reward_weights = RewardWeights(
            clinical=0.05, efficiency=0.25, financial=0.40,
            patient_satisfaction=0.05, risk_penalty=0.15, compliance_penalty=0.10
        )
        super().__init__(config, reward_weights=reward_weights, max_steps=1500, **kwargs)

        self.n_assets = (config or {}).get("n_assets", 5)
        self.initial_balance = (config or {}).get("initial_balance", 1000000.0)
        self.transaction_cost = (config or {}).get("transaction_cost", 0.001)
        self.risk_aversion = (config or {}).get("risk_aversion", 1.0)
        self.lookback = 20

        self.prices, self.returns = _generate_correlated_assets(self.n_assets, 2000)

        state_dim = self.n_assets * self.lookback + self.n_assets + 4
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(state_dim,), dtype=np.float32
        )
        self.action_space = spaces.Box(
            low=0.0, high=1.0, shape=(self.n_assets,), dtype=np.float32
        )

        self.current_step = self.lookback
        self.portfolio_value = self.initial_balance
        self.weights = np.ones(self.n_assets) / self.n_assets
        self.peak_value = self.initial_balance
        self.returns_history = []

    def _initialize_state(self) -> np.ndarray:
        self.prices, self.returns = _generate_correlated_assets(self.n_assets, 2000)
        self.current_step = self.lookback
        self.portfolio_value = self.initial_balance
        self.weights = np.ones(self.n_assets) / self.n_assets
        self.peak_value = self.initial_balance
        self.returns_history = []
        return self._get_state_features()

    def _get_state_features(self) -> np.ndarray:
        start = max(0, self.current_step - self.lookback)
        end = self.current_step
        recent_returns = self.returns[start:end]
        if len(recent_returns) < self.lookback:
            pad = np.zeros((self.lookback - len(recent_returns), self.n_assets))
            recent_returns = np.vstack([pad, recent_returns])
        flat_returns = recent_returns.flatten()

        portfolio_return = (self.portfolio_value - self.initial_balance) / self.initial_balance
        drawdown = (self.peak_value - self.portfolio_value) / (self.peak_value + 1e-8)
        vol = np.std(self.returns_history[-30:]) * np.sqrt(252) if len(self.returns_history) > 1 else 0.0
        sharpe = (np.mean(self.returns_history) / (np.std(self.returns_history) + 1e-8) * np.sqrt(252)) if len(self.returns_history) > 1 else 0.0
        portfolio_stats = np.array([portfolio_return, drawdown, vol, sharpe], dtype=np.float32)

        return np.concatenate([flat_returns, self.weights, portfolio_stats]).astype(np.float32)

    def _apply_action(self, action: np.ndarray) -> Dict[str, Any]:
        new_weights = np.clip(np.asarray(action, dtype=np.float64), 0, None)
        weight_sum = new_weights.sum()
        if weight_sum > 0:
            new_weights /= weight_sum
        else:
            new_weights = np.ones(self.n_assets) / self.n_assets

        turnover = np.sum(np.abs(new_weights - self.weights))
        cost = turnover * self.transaction_cost * self.portfolio_value

        step_idx = min(self.current_step, len(self.returns) - 1)
        asset_returns = self.returns[step_idx]
        portfolio_return = np.dot(new_weights, asset_returns)

        old_value = self.portfolio_value
        self.portfolio_value = self.portfolio_value * (1 + portfolio_return) - cost
        self.weights = new_weights * (1 + asset_returns)
        w_sum = self.weights.sum()
        if w_sum > 0:
            self.weights /= w_sum
        else:
            self.weights = np.ones(self.n_assets) / self.n_assets

        realized_return = (self.portfolio_value - old_value) / (old_value + 1e-8)
        self.returns_history.append(realized_return)
        self.peak_value = max(self.peak_value, self.portfolio_value)
        self.current_step += 1

        # CRRA utility
        gamma = self.risk_aversion
        if gamma == 1:
            utility = np.log(max(1 + realized_return, 1e-8))
        else:
            utility = ((max(1 + realized_return, 1e-8)) ** (1 - gamma) - 1) / (1 - gamma)

        return {
            "action_name": "rebalance_portfolio",
            "realized_return": realized_return,
            "turnover": turnover,
            "cost": cost,
            "utility": float(utility),
            "portfolio_value": self.portfolio_value,
            "weights": new_weights.tolist(),
        }

    def _calculate_reward_components(self, state: np.ndarray, action: Any, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        ret = info.get("realized_return", 0.0)
        utility = info.get("utility", 0.0)
        turnover = info.get("turnover", 0.0)
        drawdown = (self.peak_value - self.portfolio_value) / (self.peak_value + 1e-8)
        total_return = (self.portfolio_value - self.initial_balance) / self.initial_balance

        return {
            RewardComponent.CLINICAL: min(1.0, max(0.0, 0.5 + total_return)),
            RewardComponent.EFFICIENCY: float(np.clip(utility, -1, 1) * 0.5 + 0.5),
            RewardComponent.FINANCIAL: float(np.clip(ret * 100, -1, 1) * 0.5 + 0.5),
            RewardComponent.PATIENT_SATISFACTION: max(0.0, 1.0 - drawdown * 5),
            RewardComponent.RISK_PENALTY: min(1.0, drawdown * 3),
            RewardComponent.COMPLIANCE_PENALTY: min(1.0, turnover * 2),
        }

    def _is_done(self) -> bool:
        if self.portfolio_value <= self.initial_balance * 0.5:
            return True
        if self.current_step >= len(self.returns) - 1:
            return True
        return False

    def _get_kpis(self) -> KPIMetrics:
        total_return = (self.portfolio_value - self.initial_balance) / self.initial_balance
        returns_arr = np.array(self.returns_history) if self.returns_history else np.array([0.0])
        sharpe = (returns_arr.mean() / (returns_arr.std() + 1e-8) * np.sqrt(252)) if len(returns_arr) > 1 else 0.0
        drawdown = (self.peak_value - self.portfolio_value) / (self.peak_value + 1e-8)
        vol = returns_arr.std() * np.sqrt(252) if len(returns_arr) > 1 else 0.0

        return KPIMetrics(
            clinical_outcomes={"total_return_pct": round(total_return * 100, 2), "sharpe_ratio": round(sharpe, 3)},
            operational_efficiency={"n_assets": self.n_assets, "annualized_vol": round(vol, 4)},
            financial_metrics={
                "portfolio_value": round(self.portfolio_value, 2),
                "profit_loss": round(self.portfolio_value - self.initial_balance, 2),
            },
            patient_satisfaction=max(0.0, 1.0 - drawdown * 5),
            risk_score=round(drawdown, 4),
            compliance_score=1.0,
            timestamp=self.time_step,
        )
