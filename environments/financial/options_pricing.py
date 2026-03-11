"""Options Pricing & Hedging RL Environment - Delta hedging with Black-Scholes benchmarking"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
from scipy.stats import norm
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics, RewardWeights


class BlackScholesModel:
    """Black-Scholes analytical formulas for benchmarking."""

    @staticmethod
    def call_price(S: float, K: float, T: float, r: float, sigma: float) -> float:
        if T <= 0:
            return max(S - K, 0)
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)
        return S * norm.cdf(d1) - K * np.exp(-r * T) * norm.cdf(d2)

    @staticmethod
    def delta(S: float, K: float, T: float, r: float, sigma: float) -> float:
        if T <= 0:
            return 1.0 if S > K else 0.0
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        return norm.cdf(d1)

    @staticmethod
    def gamma(S: float, K: float, T: float, r: float, sigma: float) -> float:
        if T <= 0:
            return 0.0
        d1 = (np.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * np.sqrt(T))
        return norm.pdf(d1) / (S * sigma * np.sqrt(T))


class OptionsPricingEnv(HealthcareRLEnvironment):
    """
    Options hedging environment where the RL agent learns delta hedging.

    The agent has sold call options and must hedge by trading the underlying.
    The goal is to minimize hedging P&L variance. Supports optional
    Heston-like stochastic volatility.

    State: [S/K, time_to_expiry_ratio, sigma, bs_delta, bs_gamma*S, hedge_ratio, pnl_normalized]
    Actions: continuous hedge ratio in [-0.5, 1.5]
    """
    ACTIONS = ["adjust_hedge"]

    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        reward_weights = RewardWeights(
            clinical=0.05, efficiency=0.30, financial=0.35,
            patient_satisfaction=0.05, risk_penalty=0.15, compliance_penalty=0.10
        )
        super().__init__(config, reward_weights=reward_weights, max_steps=200, **kwargs)

        cfg = config or {}
        self.S0 = cfg.get("S0", 100.0)
        self.K = cfg.get("K", 100.0)
        self.T = cfg.get("T", 30 / 252)
        self.r = cfg.get("r", 0.05)
        self.sigma = cfg.get("sigma", 0.20)
        self.dt = cfg.get("dt", 1.0 / 252)
        self.transaction_cost = cfg.get("transaction_cost", 0.001)
        self.n_options = cfg.get("n_options", 100)
        self.stochastic_vol = cfg.get("stochastic_vol", False)
        self.n_steps = int(self.T / self.dt)

        self.bs = BlackScholesModel()

        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(7,), dtype=np.float32
        )
        self.action_space = spaces.Box(
            low=-0.5, high=1.5, shape=(1,), dtype=np.float32
        )

        self.S = self.S0
        self.current_sigma = self.sigma
        self.time_remaining = self.T
        self.hedge_position = 0.0
        self.cash = 0.0
        self.pnl_history = []
        self.hedge_errors = []

    def _initialize_state(self) -> np.ndarray:
        self.S = self.S0
        self.current_sigma = self.sigma
        self.time_remaining = self.T
        self.hedge_position = 0.0
        self.pnl_history = []
        self.hedge_errors = []
        option_price = self.bs.call_price(self.S, self.K, self.T, self.r, self.sigma)
        self.cash = option_price * self.n_options
        return self._get_state_features()

    def _get_state_features(self) -> np.ndarray:
        bs_delta = self.bs.delta(self.S, self.K, max(self.time_remaining, 1e-8), self.r, self.current_sigma)
        bs_gamma = self.bs.gamma(self.S, self.K, max(self.time_remaining, 1e-8), self.r, self.current_sigma)
        current_pnl = self.pnl_history[-1] if self.pnl_history else 0.0
        return np.array([
            self.S / self.K,
            self.time_remaining / (self.T + 1e-8),
            self.current_sigma,
            bs_delta,
            bs_gamma * self.S,
            self.hedge_position / (self.n_options + 1e-8),
            current_pnl / (self.n_options * self.S0 + 1e-8) * 100,
        ], dtype=np.float32)

    def _apply_action(self, action) -> Dict[str, Any]:
        if isinstance(action, np.ndarray):
            target_hedge = float(np.clip(action[0] if action.ndim > 0 else action, -0.5, 1.5))
        else:
            target_hedge = float(np.clip(action, -0.5, 1.5))

        target_shares = target_hedge * self.n_options
        shares_to_trade = target_shares - self.hedge_position
        cost = abs(shares_to_trade) * self.S * self.transaction_cost
        self.cash -= shares_to_trade * self.S + cost
        self.hedge_position = target_shares

        # Stock price evolution (GBM, optionally stochastic vol)
        if self.stochastic_vol:
            kappa, theta, xi = 2.0, self.sigma ** 2, 0.3
            dv = kappa * (theta - self.current_sigma ** 2) * self.dt + \
                 xi * self.current_sigma * np.sqrt(self.dt) * self.np_random.standard_normal()
            self.current_sigma = np.sqrt(max(self.current_sigma ** 2 + dv, 0.01))

        dW = self.np_random.standard_normal() * np.sqrt(self.dt)
        dS = self.S * (self.r * self.dt + self.current_sigma * dW)
        self.S += dS
        self.time_remaining -= self.dt

        # Portfolio P&L
        hedge_value = self.hedge_position * self.S
        if self.time_remaining <= self.dt:
            option_liability = max(self.S - self.K, 0) * self.n_options
        else:
            option_liability = self.bs.call_price(
                self.S, self.K, max(self.time_remaining, 1e-8), self.r, self.current_sigma
            ) * self.n_options

        pnl = self.cash + hedge_value - option_liability
        self.pnl_history.append(pnl)

        bs_delta = self.bs.delta(self.S, self.K, max(self.time_remaining, 1e-8), self.r, self.current_sigma)
        hedge_error = abs(target_hedge - bs_delta)
        self.hedge_errors.append(hedge_error)

        return {
            "action_name": "adjust_hedge",
            "target_hedge": target_hedge,
            "bs_delta": bs_delta,
            "hedge_error": hedge_error,
            "pnl": pnl,
            "stock_price": self.S,
            "cost": cost,
        }

    def _calculate_reward_components(self, state: np.ndarray, action: Any, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        pnl = info.get("pnl", 0.0)
        hedge_error = info.get("hedge_error", 0.0)
        initial_pnl = self.pnl_history[0] if self.pnl_history else 0.0
        pnl_deviation = abs(pnl - initial_pnl) / (self.n_options * self.S0 + 1e-8)

        return {
            RewardComponent.CLINICAL: max(0.0, 1.0 - hedge_error * 2),
            RewardComponent.EFFICIENCY: max(0.0, 1.0 - pnl_deviation * 10),
            RewardComponent.FINANCIAL: max(0.0, 0.5 + pnl / (self.n_options * self.S0 + 1e-8)),
            RewardComponent.PATIENT_SATISFACTION: max(0.0, 1.0 - hedge_error * 3),
            RewardComponent.RISK_PENALTY: min(1.0, pnl_deviation * 5),
            RewardComponent.COMPLIANCE_PENALTY: min(1.0, hedge_error * 2),
        }

    def _is_done(self) -> bool:
        return self.time_remaining <= self.dt

    def _get_kpis(self) -> KPIMetrics:
        current_pnl = self.pnl_history[-1] if self.pnl_history else 0.0
        mean_hedge_error = np.mean(self.hedge_errors) if self.hedge_errors else 0.0
        pnl_arr = np.array(self.pnl_history) if len(self.pnl_history) > 1 else np.array([0.0])
        pnl_vol = pnl_arr.std() if len(pnl_arr) > 1 else 0.0

        return KPIMetrics(
            clinical_outcomes={
                "mean_hedge_error": round(mean_hedge_error, 4),
                "bs_delta": round(self.bs.delta(self.S, self.K, max(self.time_remaining, 1e-8), self.r, self.current_sigma), 4),
            },
            operational_efficiency={
                "steps_remaining": max(0, int(self.time_remaining / self.dt)),
                "current_sigma": round(self.current_sigma, 4),
            },
            financial_metrics={
                "pnl": round(current_pnl, 2),
                "pnl_volatility": round(pnl_vol, 2),
                "stock_price": round(self.S, 2),
            },
            patient_satisfaction=max(0.0, 1.0 - mean_hedge_error * 3),
            risk_score=round(min(1.0, abs(current_pnl) / (self.n_options * self.S0 + 1e-8)), 4),
            compliance_score=max(0.0, 1.0 - mean_hedge_error * 2),
            timestamp=self.time_step,
        )
