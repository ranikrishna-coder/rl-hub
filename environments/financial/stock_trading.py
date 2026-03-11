"""Stock Trading RL Environment - Single-asset trading with risk-adjusted rewards"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics, RewardWeights


def _generate_synthetic_prices(n_days: int = 2000, seed: int = None) -> np.ndarray:
    """Generate synthetic stock prices using Geometric Brownian Motion."""
    rng = np.random.default_rng(seed)
    mu = 0.0002
    sigma = 0.015
    S0 = 100.0
    returns = rng.normal(mu, sigma, n_days)
    prices = S0 * np.exp(np.cumsum(returns))
    return prices


def _compute_features(prices: np.ndarray, lookback: int = 30) -> np.ndarray:
    """Compute technical features from price series."""
    n = len(prices)
    features = np.zeros((n, 18), dtype=np.float32)
    for i in range(lookback, n):
        window = prices[i - lookback:i]
        ret = (prices[i] - prices[i - 1]) / prices[i - 1] if i > 0 else 0.0
        sma = np.mean(window)
        std = np.std(window)
        rsi_gains = np.mean([max(0, window[j] - window[j - 1]) for j in range(1, len(window))])
        rsi_losses = np.mean([max(0, window[j - 1] - window[j]) for j in range(1, len(window))])
        rsi = 100 - 100 / (1 + rsi_gains / (rsi_losses + 1e-8))
        features[i] = [
            ret, prices[i] / sma - 1, std / sma,
            (prices[i] - np.min(window)) / (np.max(window) - np.min(window) + 1e-8),
            rsi / 100.0,
            np.mean(np.diff(window[-5:])) / (prices[i] + 1e-8),
            np.log(prices[i] / (sma + 1e-8)),
            np.std(np.diff(window) / (window[:-1] + 1e-8)),
            *([0.0] * 10)
        ]
    return features


class StockTradingEnv(HealthcareRLEnvironment):
    """
    Single-asset stock trading environment.

    The agent learns to trade a single stock by choosing discrete actions
    (Strong Sell, Sell, Hold, Buy, Strong Buy). Rewards are risk-adjusted
    using the Differential Sharpe Ratio.

    State: market features + [position_fraction, cash_ratio, unrealized_pnl, drawdown]
    Actions: 5 discrete trading decisions
    """
    ACTIONS = ["strong_sell", "sell", "hold", "buy", "strong_buy"]
    ACTION_MAP = {0: -1.0, 1: -0.5, 2: 0.0, 3: 0.5, 4: 1.0}

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        reward_weights = RewardWeights(
            clinical=0.05, efficiency=0.25, financial=0.40,
            patient_satisfaction=0.05, risk_penalty=0.15, compliance_penalty=0.10
        )
        super().__init__(config, reward_weights=reward_weights, max_steps=1500, **kwargs)

        self.initial_balance = (config or {}).get("initial_balance", 100000.0)
        self.transaction_cost = (config or {}).get("transaction_cost", 0.001)
        self.slippage = (config or {}).get("slippage", 0.0005)
        self.max_position = (config or {}).get("max_position", 1.0)
        self.lookback_window = 30

        self.prices = _generate_synthetic_prices(2000)
        self.features = _compute_features(self.prices, self.lookback_window)

        n_features = self.features.shape[1]
        self.state_dim = n_features + 4

        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(self.state_dim,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(5)

        self.balance = self.initial_balance
        self.position = 0.0
        self.portfolio_value = self.initial_balance
        self.peak_portfolio = self.initial_balance
        self.returns_history = []
        self.trade_count = 0
        self.total_cost = 0.0
        self.current_step = self.lookback_window
        self._A = 0.0
        self._B = 0.0
        self._eta = 0.01

    def _initialize_state(self) -> np.ndarray:
        self.current_step = self.lookback_window
        self.balance = self.initial_balance
        self.position = 0.0
        self.portfolio_value = self.initial_balance
        self.peak_portfolio = self.initial_balance
        self.returns_history = []
        self.trade_count = 0
        self.total_cost = 0.0
        self._A = 0.0
        self._B = 0.0
        self.prices = _generate_synthetic_prices(2000)
        self.features = _compute_features(self.prices, self.lookback_window)
        return self._get_state_features()

    def _get_state_features(self) -> np.ndarray:
        idx = min(self.current_step, len(self.features) - 1)
        market_features = self.features[idx]
        pv = max(self.portfolio_value, 1e-8)
        position_frac = self.position * self.prices[min(self.current_step, len(self.prices) - 1)] / pv
        cash_ratio = self.balance / pv
        unrealized_pnl = (self.portfolio_value - self.initial_balance) / self.initial_balance
        drawdown = (self.peak_portfolio - self.portfolio_value) / self.peak_portfolio
        portfolio_features = np.array([position_frac, cash_ratio, unrealized_pnl, drawdown], dtype=np.float32)
        return np.concatenate([market_features, portfolio_features]).astype(np.float32)

    def _apply_action(self, action: int) -> Dict[str, Any]:
        target_position_frac = self.ACTION_MAP[int(action)] * self.max_position
        current_price = self.prices[min(self.current_step, len(self.prices) - 1)]
        target_value = target_position_frac * self.portfolio_value
        target_shares = target_value / (current_price + 1e-8)
        shares_to_trade = target_shares - self.position
        cost = 0.0

        if abs(shares_to_trade) > 1e-8:
            direction = np.sign(shares_to_trade)
            exec_price = current_price * (1 + direction * self.slippage)
            trade_value = abs(shares_to_trade) * exec_price
            cost = trade_value * self.transaction_cost
            self.balance -= shares_to_trade * exec_price + cost
            self.position = target_shares
            self.trade_count += 1
            self.total_cost += cost

        self.current_step += 1
        new_price = self.prices[min(self.current_step, len(self.prices) - 1)]
        old_portfolio = self.portfolio_value
        self.portfolio_value = self.balance + self.position * new_price
        step_return = (self.portfolio_value - old_portfolio) / (old_portfolio + 1e-8)
        self.returns_history.append(step_return)
        self.peak_portfolio = max(self.peak_portfolio, self.portfolio_value)

        # Differential Sharpe Ratio
        delta_A = step_return - self._A
        delta_B = step_return ** 2 - self._B
        self._A += self._eta * delta_A
        self._B += self._eta * delta_B
        denom = self._B - self._A ** 2
        dsr = (self._B * delta_A - 0.5 * self._A * delta_B) / (denom ** 1.5) if denom > 1e-8 else step_return

        return {
            "action_name": self.ACTIONS[int(action)],
            "step_return": step_return,
            "dsr": float(np.clip(dsr, -5, 5)),
            "trade_cost": cost,
            "portfolio_value": self.portfolio_value,
        }

    def _calculate_reward_components(self, state: np.ndarray, action: Any, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        step_return = info.get("step_return", 0.0)
        dsr = info.get("dsr", 0.0)
        drawdown = (self.peak_portfolio - self.portfolio_value) / (self.peak_portfolio + 1e-8)
        total_return = (self.portfolio_value - self.initial_balance) / self.initial_balance

        return {
            RewardComponent.CLINICAL: min(1.0, max(0.0, 0.5 + total_return)),
            RewardComponent.EFFICIENCY: float(np.clip(dsr, -1, 1) * 0.5 + 0.5),
            RewardComponent.FINANCIAL: float(np.clip(step_return * 100, -1, 1) * 0.5 + 0.5),
            RewardComponent.PATIENT_SATISFACTION: 1.0 - min(1.0, drawdown * 5),
            RewardComponent.RISK_PENALTY: min(1.0, drawdown * 3),
            RewardComponent.COMPLIANCE_PENALTY: min(1.0, self.total_cost / (self.initial_balance * 0.01)),
        }

    def _is_done(self) -> bool:
        if self.portfolio_value <= self.initial_balance * 0.5:
            return True
        if self.current_step >= len(self.prices) - 2:
            return True
        return False

    def _get_kpis(self) -> KPIMetrics:
        total_return = (self.portfolio_value - self.initial_balance) / self.initial_balance
        returns_arr = np.array(self.returns_history) if self.returns_history else np.array([0.0])
        sharpe = (returns_arr.mean() / (returns_arr.std() + 1e-8) * np.sqrt(252)) if len(returns_arr) > 1 else 0.0
        drawdown = (self.peak_portfolio - self.portfolio_value) / (self.peak_portfolio + 1e-8)
        downside = returns_arr[returns_arr < 0]
        sortino = (returns_arr.mean() / (downside.std() + 1e-8) * np.sqrt(252)) if len(downside) > 2 else 0.0

        return KPIMetrics(
            clinical_outcomes={"total_return_pct": round(total_return * 100, 2), "sharpe_ratio": round(sharpe, 3)},
            operational_efficiency={"trade_count": self.trade_count, "sortino_ratio": round(sortino, 3)},
            financial_metrics={
                "portfolio_value": round(self.portfolio_value, 2),
                "total_cost": round(self.total_cost, 2),
                "profit_loss": round(self.portfolio_value - self.initial_balance, 2),
            },
            patient_satisfaction=max(0.0, 1.0 - drawdown * 5),
            risk_score=round(drawdown, 4),
            compliance_score=max(0.0, 1.0 - self.total_cost / (self.initial_balance * 0.01)),
            timestamp=self.time_step,
        )
