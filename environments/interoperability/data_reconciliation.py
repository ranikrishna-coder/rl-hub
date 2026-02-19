"""Data Reconciliation Environment - Reconciles data across systems (InterSystems, Orion)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class DataReconciliationEnv(HealthcareRLEnvironment):
    ACTIONS = ["merge", "keep_primary", "keep_secondary", "flag_conflict", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.data_conflicts = []
        self.reconciled_records = 0
        self.data_quality_score = 0.7
    def _initialize_state(self) -> np.ndarray:
        self.data_conflicts = [{"confidence_primary": self.np_random.uniform(0.5, 1.0), "confidence_secondary": self.np_random.uniform(0.5, 1.0), "conflict_type": self.np_random.choice(["duplicate", "mismatch", "missing"])} for _ in range(12)]
        self.reconciled_records = 0
        self.data_quality_score = 0.7
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            len(self.data_conflicts) / 20.0,
            self.reconciled_records / 15.0,
            self.data_quality_score,
            np.mean([c["confidence_primary"] for c in self.data_conflicts[:5]]) if self.data_conflicts else 0.0,
            *[0.0] * 12
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.data_conflicts and action_name != "no_action":
            conflict = self.data_conflicts.pop(0)
            if action_name == "merge":
                self.data_quality_score = min(1.0, self.data_quality_score + 0.05)
            self.reconciled_records += 1
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.data_quality_score
        efficiency_score = 1.0 - len(self.data_conflicts) / 20.0
        financial_score = self.data_quality_score * 0.9
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.data_quality_score,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 25 or len(self.data_conflicts) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"data_quality": self.data_quality_score},
            operational_efficiency={"records_reconciled": self.reconciled_records},
            financial_metrics={"reconciliation_cost": self.reconciled_records * 50},
            patient_satisfaction=self.data_quality_score,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

