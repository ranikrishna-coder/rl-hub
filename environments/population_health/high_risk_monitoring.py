"""High Risk Monitoring Environment"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class HighRiskMonitoringEnv(HealthcareRLEnvironment):
    MONITORING_ACTIONS = ["daily_check", "weekly_review", "alert_triggered", "escalate", "no_action"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.MONITORING_ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.high_risk_patients = []
        self.monitoring_history = []
        self.alert_count = 0
    def _initialize_state(self) -> np.ndarray:
        self.high_risk_patients = [p for p in self.patient_generator.generate_batch(12) if p.risk_score > 0.6]
        self.monitoring_history = []
        self.alert_count = 0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(16, dtype=np.float32)
        state[0] = len(self.high_risk_patients) / 15.0
        state[1] = self.alert_count / 10.0
        if self.high_risk_patients:
            state[2] = np.mean([p.risk_score for p in self.high_risk_patients])
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.MONITORING_ACTIONS[action]
        self.monitoring_history.append(action_name)
        if action_name == "alert_triggered" and self.high_risk_patients:
            self.alert_count += 1
            patient = self.high_risk_patients[0]
            patient.risk_score = max(0, patient.risk_score - 0.1)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        if not self.high_risk_patients:
            return {k: 0.0 for k in RewardComponent}
        avg_risk = np.mean([p.risk_score for p in self.high_risk_patients])
        clinical_score = 1.0 - avg_risk
        efficiency_score = 1.0 - len(self.monitoring_history) / 20.0 if avg_risk < 0.5 else 0.5
        financial_score = 1.0 / (1.0 + len(self.monitoring_history) * 50 / 3000.0)
        risk_penalty = avg_risk if avg_risk > 0.7 else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - avg_risk,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: 0.0
        }
    def _is_done(self) -> bool:
        return self.time_step >= 25 or (self.high_risk_patients and np.mean([p.risk_score for p in self.high_risk_patients]) < 0.4)
    def _get_kpis(self) -> KPIMetrics:
        avg_risk = np.mean([p.risk_score for p in self.high_risk_patients]) if self.high_risk_patients else 0.0
        return KPIMetrics(
            clinical_outcomes={"avg_risk_score": avg_risk, "alerts_triggered": self.alert_count},
            operational_efficiency={"monitoring_actions": len(self.monitoring_history)},
            financial_metrics={"monitoring_cost": len(self.monitoring_history) * 50},
            patient_satisfaction=1.0 - avg_risk,
            risk_score=avg_risk,
            compliance_score=1.0,
            timestamp=self.time_step
        )

