"""Adaptive Trial Design Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class AdaptiveTrialDesignEnv(HealthcareRLEnvironment):
    ADAPTATIONS = ["increase_dose", "decrease_dose", "add_arm", "stop_arm", "extend_trial", "no_change"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ADAPTATIONS))
        self.efficacy_scores = []
        self.safety_scores = []
        self.trial_arms = {"control": 50, "treatment_low": 50, "treatment_high": 50}
    def _initialize_state(self) -> np.ndarray:
        self.efficacy_scores = [0.5] * 3
        self.safety_scores = [0.8] * 3
        self.trial_arms = {"control": 50, "treatment_low": 50, "treatment_high": 50}
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            np.mean(self.efficacy_scores),
            np.mean(self.safety_scores),
            sum(self.trial_arms.values()) / 200.0,
            self.trial_arms["control"] / 100.0,
            self.trial_arms["treatment_low"] / 100.0,
            self.trial_arms["treatment_high"] / 100.0,
            *[0.0] * 10
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        adaptation = self.ADAPTATIONS[action]
        if adaptation == "increase_dose":
            self.efficacy_scores[2] = min(1.0, self.efficacy_scores[2] + 0.1)
            self.safety_scores[2] = max(0, self.safety_scores[2] - 0.05)
        elif adaptation == "decrease_dose":
            self.safety_scores[1] = min(1.0, self.safety_scores[1] + 0.1)
            self.efficacy_scores[1] = max(0, self.efficacy_scores[1] - 0.05)
        return {"adaptation": adaptation}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = np.mean(self.efficacy_scores) * np.mean(self.safety_scores)
        efficiency_score = sum(self.trial_arms.values()) / 200.0
        financial_score = np.mean(self.efficacy_scores)
        risk_penalty = 1.0 - np.mean(self.safety_scores) if np.mean(self.safety_scores) < 0.7 else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: np.mean(self.efficacy_scores),
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 30 or (np.mean(self.efficacy_scores) > 0.8 and np.mean(self.safety_scores) > 0.75)
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"efficacy": np.mean(self.efficacy_scores), "safety": np.mean(self.safety_scores)},
            operational_efficiency={"total_enrollment": sum(self.trial_arms.values())},
            financial_metrics={"trial_value": np.mean(self.efficacy_scores) * 100000},
            patient_satisfaction=np.mean(self.efficacy_scores),
            risk_score=1.0 - np.mean(self.safety_scores),
            compliance_score=1.0,
            timestamp=self.time_step
        )

