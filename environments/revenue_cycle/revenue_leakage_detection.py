"""Revenue Leakage Detection Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.financial_simulator import FinancialSimulator

class RevenueLeakageDetectionEnv(HealthcareRLEnvironment):
    ACTIONS = ["investigate", "recover", "write_off", "prevent", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.financial_simulator = FinancialSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.financial_simulator
        self.detected_leakage = 0.0
        self.recovered_amount = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.detected_leakage = 0.0
        self.recovered_amount = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        financial_state = self.financial_simulator.get_state()
        return np.array([
            financial_state.revenue_leakage / 50000.0,
            self.detected_leakage / 50000.0,
            self.recovered_amount / 50000.0,
            financial_state.claims_pending / 20.0,
            financial_state.denial_rate,
            *[0.0] * 11
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        financial_state = self.financial_simulator.get_state()
        if action_name == "investigate":
            self.detected_leakage = financial_state.revenue_leakage * 0.8
        elif action_name == "recover":
            self.recovered_amount += self.detected_leakage * 0.6
            self.detected_leakage = 0.0
        self.financial_simulator.update(1.0)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        financial_state = self.financial_simulator.get_state()
        clinical_score = 1.0 - financial_state.revenue_leakage / 50000.0
        efficiency_score = self.recovered_amount / 50000.0
        financial_score = self.recovered_amount / 50000.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - financial_state.revenue_leakage / 50000.0,
            RewardComponent.RISK_PENALTY: financial_state.revenue_leakage / 50000.0 if financial_state.revenue_leakage > 20000 else 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        financial_state = self.financial_simulator.get_state()
        return self.time_step >= 25 or financial_state.revenue_leakage < 5000
    def _get_kpis(self) -> KPIMetrics:
        financial_state = self.financial_simulator.get_state()
        return KPIMetrics(
            clinical_outcomes={"revenue_leakage": financial_state.revenue_leakage},
            operational_efficiency={"leakage_detected": self.detected_leakage, "recovered": self.recovered_amount},
            financial_metrics={"recovery_rate": self.recovered_amount / max(0.01, self.detected_leakage)},
            patient_satisfaction=1.0 - financial_state.revenue_leakage / 50000.0,
            risk_score=financial_state.revenue_leakage / 50000.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

