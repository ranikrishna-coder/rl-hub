"""Clinical-Financial Tradeoff Environment - Balances clinical outcomes and financial constraints"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.hospital_simulator import HospitalSimulator
from simulator.financial_simulator import FinancialSimulator

class ClinicalFinancialTradeoffEnv(HealthcareRLEnvironment):
    ACTIONS = ["prioritize_clinical", "prioritize_financial", "balance", "optimize_both", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.financial_simulator = FinancialSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        self.tradeoff_score = 0.5
    def _initialize_state(self) -> np.ndarray:
        self.tradeoff_score = 0.5
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        hospital_state = self.hospital_simulator.get_state()
        financial_state = self.financial_simulator.get_state()
        return np.array([
            hospital_state.occupancy_rate, financial_state.collection_rate,
            self.tradeoff_score, financial_state.total_revenue / 100000.0,
            *[0.0] * 13
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if action_name == "balance" or action_name == "optimize_both":
            self.tradeoff_score = min(1.0, self.tradeoff_score + 0.1)
        self.hospital_simulator.update(1.0)
        self.financial_simulator.update(1.0)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        hospital_state = self.hospital_simulator.get_state()
        financial_state = self.financial_simulator.get_state()
        clinical_score = hospital_state.occupancy_rate
        efficiency_score = self.tradeoff_score
        financial_score = financial_state.collection_rate
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.tradeoff_score,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 35
    def _get_kpis(self) -> KPIMetrics:
        hospital_state = self.hospital_simulator.get_state()
        financial_state = self.financial_simulator.get_state()
        return KPIMetrics(
            clinical_outcomes={"occupancy_rate": hospital_state.occupancy_rate},
            operational_efficiency={"tradeoff_score": self.tradeoff_score},
            financial_metrics={"collection_rate": financial_state.collection_rate, "total_revenue": financial_state.total_revenue},
            patient_satisfaction=self.tradeoff_score,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

