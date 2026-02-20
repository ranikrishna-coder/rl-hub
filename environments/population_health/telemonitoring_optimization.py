"""Telemonitoring Optimization Environment - Optimizes telemonitoring (Health Catalyst, Innovaccer)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class TelemonitoringOptimizationEnv(HealthcareRLEnvironment):
    ACTIONS = ["enable_monitoring", "adjust_frequency", "alert_clinician", "disable_monitoring", "defer", "escalate"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.monitoring_queue = []
        self.active_monitoring = []
        self.monitoring_efficiency = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.monitoring_queue = [{"patient": self.patient_generator.generate_patient(), "risk_level": self.np_random.uniform(0, 1), "monitoring_frequency": 1.0, "days_monitored": 0.0} for _ in range(15)]
        self.active_monitoring = []
        self.monitoring_efficiency = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.monitoring_queue) / 20.0
        state[1] = len(self.active_monitoring) / 20.0
        if self.monitoring_queue:
            state[2] = self.monitoring_queue[0]["risk_level"]
            state[3] = self.monitoring_queue[0]["monitoring_frequency"] / 7.0
        state[4] = self.monitoring_efficiency
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.monitoring_queue:
            patient = self.monitoring_queue.pop(0)
            if action_name == "enable_monitoring":
                self.active_monitoring.append({**patient, "status": "active"})
                self.monitoring_efficiency = min(1.0, self.monitoring_efficiency + 0.1)
            elif action_name == "adjust_frequency":
                patient["monitoring_frequency"] = min(7.0, patient["monitoring_frequency"] + 1.0)
                self.active_monitoring.append({**patient, "status": "active"})
            elif action_name == "alert_clinician":
                self.active_monitoring.append({**patient, "status": "alerted"})
                self.monitoring_efficiency = min(1.0, self.monitoring_efficiency + 0.15)
            elif action_name == "disable_monitoring":
                # Patient no longer needs monitoring
                self.completed_monitoring = getattr(self, "completed_monitoring", [])
                self.completed_monitoring.append({**patient, "status": "completed"})
            elif action_name == "defer":
                self.monitoring_queue.append(patient)
                patient["days_monitored"] += 1.0
        for patient in self.active_monitoring:
            patient["days_monitored"] += 1.0
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = 1.0 - len([p for p in self.monitoring_queue if p["risk_level"] > 0.8]) / 15.0
        efficiency_score = self.monitoring_efficiency
        financial_score = len(self.active_monitoring) / 20.0
        risk_penalty = len([p for p in self.monitoring_queue if p["risk_level"] > 0.9]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.monitoring_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or (len(self.monitoring_queue) == 0 and len(self.active_monitoring) == 0)
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"high_risk_waiting": len([p for p in self.monitoring_queue if p["risk_level"] > 0.8]), "monitoring_efficiency": self.monitoring_efficiency},
            operational_efficiency={"queue_length": len(self.monitoring_queue), "active_monitoring": len(self.active_monitoring)},
            financial_metrics={"active_count": len(self.active_monitoring)},
            patient_satisfaction=1.0 - len(self.monitoring_queue) / 20.0,
            risk_score=len([p for p in self.monitoring_queue if p["risk_level"] > 0.9]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

