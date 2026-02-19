"""Scan Parameter Optimization Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class ScanParameterOptimizationEnv(HealthcareRLEnvironment):
    PARAMETERS = ["low_dose", "standard", "high_quality", "contrast", "no_contrast"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(15,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.PARAMETERS))
        self.image_quality = 0.5
        self.radiation_dose = 0.5
        self.scans_performed = 0
    def _initialize_state(self) -> np.ndarray:
        self.image_quality = 0.5
        self.radiation_dose = 0.5
        self.scans_performed = 0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            self.image_quality, self.radiation_dose, self.scans_performed / 20.0,
            *[0.0] * 12
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        param = self.PARAMETERS[action]
        if param == "low_dose":
            self.radiation_dose = max(0, self.radiation_dose - 0.2)
            self.image_quality = max(0, self.image_quality - 0.1)
        elif param == "high_quality":
            self.image_quality = min(1.0, self.image_quality + 0.2)
            self.radiation_dose = min(1.0, self.radiation_dose + 0.1)
        elif param == "standard":
            self.image_quality = 0.7
            self.radiation_dose = 0.5
        self.scans_performed += 1
        return {"parameter": param}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.image_quality
        efficiency_score = 1.0 - self.radiation_dose
        financial_score = self.scans_performed / 20.0
        risk_penalty = self.radiation_dose if self.radiation_dose > 0.8 else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.image_quality,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 25 or self.scans_performed >= 20
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"image_quality": self.image_quality},
            operational_efficiency={"scans_performed": self.scans_performed},
            financial_metrics={"scan_revenue": self.scans_performed * 800},
            patient_satisfaction=self.image_quality,
            risk_score=self.radiation_dose,
            compliance_score=1.0,
            timestamp=self.time_step
        )

