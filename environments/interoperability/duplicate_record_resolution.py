"""Duplicate Record Resolution Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class DuplicateRecordResolutionEnv(HealthcareRLEnvironment):
    ACTIONS = ["merge", "keep_both", "delete_duplicate", "flag_review", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.duplicate_records = []
        self.resolved_count = 0
        self.data_integrity_score = 0.8
    def _initialize_state(self) -> np.ndarray:
        self.duplicate_records = [{"match_confidence": self.np_random.uniform(0.6, 1.0), "source_systems": 2} for _ in range(10)]
        self.resolved_count = 0
        self.data_integrity_score = 0.8
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            len(self.duplicate_records) / 15.0,
            self.resolved_count / 10.0,
            self.data_integrity_score,
            np.mean([d["match_confidence"] for d in self.duplicate_records[:5]]) if self.duplicate_records else 0.0,
            *[0.0] * 11
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.duplicate_records and action_name != "no_action":
            record = self.duplicate_records.pop(0)
            if action_name == "merge":
                self.data_integrity_score = min(1.0, self.data_integrity_score + 0.05)
            self.resolved_count += 1
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.data_integrity_score
        efficiency_score = 1.0 - len(self.duplicate_records) / 15.0
        financial_score = self.data_integrity_score * 0.9
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.data_integrity_score,
            RewardComponent.RISK_PENALTY: 0.0,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 20 or len(self.duplicate_records) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"data_integrity": self.data_integrity_score},
            operational_efficiency={"records_resolved": self.resolved_count},
            financial_metrics={"resolution_cost": self.resolved_count * 30},
            patient_satisfaction=self.data_integrity_score,
            risk_score=0.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

