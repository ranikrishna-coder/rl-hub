"""Cross-System Alert Prioritization Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics

class CrossSystemAlertPrioritizationEnv(HealthcareRLEnvironment):
    PRIORITIES = ["critical", "high", "medium", "low", "dismiss"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.PRIORITIES))
        self.alerts = []
        self.processed_alerts = []
        self.alert_fatigue_score = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.alerts = [{"severity": self.np_random.uniform(0, 1), "source": self.np_random.choice(["epic", "cerner", "lab", "pharmacy"]), "urgency": self.np_random.uniform(0, 1)} for _ in range(15)]
        self.processed_alerts = []
        self.alert_fatigue_score = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        return np.array([
            len(self.alerts) / 20.0,
            len(self.processed_alerts) / 15.0,
            self.alert_fatigue_score,
            np.mean([a["severity"] for a in self.alerts[:5]]) if self.alerts else 0.0,
            *[0.0] * 12
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        priority = self.PRIORITIES[action]
        if self.alerts:
            alert = self.alerts.pop(0)
            self.processed_alerts.append({**alert, "priority": priority})
            if priority == "dismiss" and alert["severity"] > 0.7:
                self.alert_fatigue_score += 0.1
        return {"priority": priority}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = 1.0 - self.alert_fatigue_score
        efficiency_score = 1.0 - len(self.alerts) / 20.0
        financial_score = len(self.processed_alerts) / 15.0
        risk_penalty = self.alert_fatigue_score if self.alert_fatigue_score > 0.3 else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - self.alert_fatigue_score,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 30 or len(self.alerts) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"alert_fatigue": self.alert_fatigue_score},
            operational_efficiency={"alerts_processed": len(self.processed_alerts)},
            financial_metrics={"alert_processing_cost": len(self.processed_alerts) * 25},
            patient_satisfaction=1.0 - self.alert_fatigue_score,
            risk_score=self.alert_fatigue_score,
            compliance_score=1.0,
            timestamp=self.time_step
        )

