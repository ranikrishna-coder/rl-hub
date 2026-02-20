"""Adverse Event Prediction Environment - Predicts adverse events (Veeva, IQVIA)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class AdverseEventPredictionEnv(HealthcareRLEnvironment):
    ACTIONS = ["predict_low_risk", "predict_moderate_risk", "predict_high_risk", "monitor_closely", "intervene", "defer"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.prediction_queue = []
        self.predicted_events = []
        self.prediction_accuracy = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.prediction_queue = [{"patient": self.patient_generator.generate_patient(), "adverse_event_risk": self.np_random.uniform(0, 1), "prediction_confidence": self.np_random.uniform(0.5, 1.0), "baseline_risk": self.np_random.uniform(0.1, 0.5)} for _ in range(15)]
        self.predicted_events = []
        self.prediction_accuracy = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.prediction_queue) / 20.0
        state[1] = len(self.predicted_events) / 20.0
        if self.prediction_queue:
            state[2] = self.prediction_queue[0]["adverse_event_risk"]
            state[3] = self.prediction_queue[0]["prediction_confidence"]
            state[4] = self.prediction_queue[0]["baseline_risk"]
        state[5] = self.prediction_accuracy
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.prediction_queue:
            patient = self.prediction_queue.pop(0)
            if action_name == "predict_low_risk":
                actual_risk = patient["baseline_risk"] * self.np_random.uniform(0.8, 1.2)
                accuracy = 1.0 - abs(patient["adverse_event_risk"] - actual_risk) if patient["adverse_event_risk"] < 0.3 else 0.5
                self.predicted_events.append({**patient, "prediction": "low", "accuracy": accuracy})
                self.prediction_accuracy = min(1.0, self.prediction_accuracy + accuracy / 10.0)
            elif action_name == "predict_moderate_risk":
                actual_risk = patient["baseline_risk"] * self.np_random.uniform(0.9, 1.1)
                accuracy = 1.0 - abs(patient["adverse_event_risk"] - actual_risk) if 0.3 <= patient["adverse_event_risk"] <= 0.7 else 0.5
                self.predicted_events.append({**patient, "prediction": "moderate", "accuracy": accuracy})
                self.prediction_accuracy = min(1.0, self.prediction_accuracy + accuracy / 8.0)
            elif action_name == "predict_high_risk":
                actual_risk = patient["baseline_risk"] * self.np_random.uniform(1.0, 1.5)
                accuracy = 1.0 - abs(patient["adverse_event_risk"] - actual_risk) if patient["adverse_event_risk"] > 0.7 else 0.5
                self.predicted_events.append({**patient, "prediction": "high", "accuracy": accuracy})
                self.prediction_accuracy = min(1.0, self.prediction_accuracy + accuracy / 7.0)
            elif action_name == "monitor_closely":
                self.predicted_events.append({**patient, "prediction": "monitored"})
                self.prediction_accuracy = min(1.0, self.prediction_accuracy + 0.05)
            elif action_name == "intervene":
                patient["adverse_event_risk"] = max(0, patient["adverse_event_risk"] - 0.2)
                self.predicted_events.append({**patient, "prediction": "intervened"})
                self.prediction_accuracy = min(1.0, self.prediction_accuracy + 0.1)
            elif action_name == "defer":
                self.prediction_queue.append(patient)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.prediction_accuracy
        efficiency_score = len(self.predicted_events) / 20.0
        financial_score = len(self.predicted_events) / 20.0
        risk_penalty = len([p for p in self.prediction_queue if p["adverse_event_risk"] > 0.8]) * 0.3
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.prediction_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.prediction_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"prediction_accuracy": self.prediction_accuracy, "high_risk_waiting": len([p for p in self.prediction_queue if p["adverse_event_risk"] > 0.8])},
            operational_efficiency={"queue_length": len(self.prediction_queue), "events_predicted": len(self.predicted_events)},
            financial_metrics={"predicted_count": len(self.predicted_events)},
            patient_satisfaction=1.0 - len(self.prediction_queue) / 20.0,
            risk_score=len([p for p in self.prediction_queue if p["adverse_event_risk"] > 0.8]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

