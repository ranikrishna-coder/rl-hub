"""Revenue Forecast Simulation Environment - Simulates revenue forecasts (Change Healthcare)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class RevenueForecastSimulationEnv(HealthcareRLEnvironment):
    ACTIONS = ["forecast_optimistic", "forecast_realistic", "forecast_conservative", "adjust_forecast", "defer", "update_model"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(18,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.forecast_queue = []
        self.completed_forecasts = []
        self.forecast_accuracy = 0.0
        self.actual_revenue = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.forecast_queue = [{"patient": self.patient_generator.generate_patient(), "projected_revenue": self.np_random.uniform(1000, 50000), "forecast_confidence": self.np_random.uniform(0.5, 1.0), "time_horizon": self.np_random.uniform(1, 12)} for _ in range(15)]
        self.completed_forecasts = []
        self.forecast_accuracy = 0.0
        self.actual_revenue = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(18, dtype=np.float32)
        state[0] = len(self.forecast_queue) / 20.0
        state[1] = len(self.completed_forecasts) / 20.0
        if self.forecast_queue:
            state[2] = self.forecast_queue[0]["projected_revenue"] / 50000.0
            state[3] = self.forecast_queue[0]["forecast_confidence"]
            state[4] = self.forecast_queue[0]["time_horizon"] / 12.0
        state[5] = self.forecast_accuracy
        state[6] = self.actual_revenue / 500000.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.forecast_queue:
            forecast = self.forecast_queue.pop(0)
            if action_name == "forecast_optimistic":
                actual = forecast["projected_revenue"] * self.np_random.uniform(0.9, 1.1)
                accuracy = 1.0 - abs(forecast["projected_revenue"] - actual) / forecast["projected_revenue"]
                self.actual_revenue += actual
                self.completed_forecasts.append({**forecast, "type": "optimistic", "actual": actual, "accuracy": accuracy})
                self.forecast_accuracy = min(1.0, self.forecast_accuracy + accuracy / 10.0)
            elif action_name == "forecast_realistic":
                actual = forecast["projected_revenue"] * self.np_random.uniform(0.95, 1.05)
                accuracy = 1.0 - abs(forecast["projected_revenue"] - actual) / forecast["projected_revenue"]
                self.actual_revenue += actual
                self.completed_forecasts.append({**forecast, "type": "realistic", "actual": actual, "accuracy": accuracy})
                self.forecast_accuracy = min(1.0, self.forecast_accuracy + accuracy / 8.0)
            elif action_name == "forecast_conservative":
                actual = forecast["projected_revenue"] * self.np_random.uniform(0.85, 1.0)
                accuracy = 1.0 - abs(forecast["projected_revenue"] - actual) / forecast["projected_revenue"]
                self.actual_revenue += actual
                self.completed_forecasts.append({**forecast, "type": "conservative", "actual": actual, "accuracy": accuracy})
                self.forecast_accuracy = min(1.0, self.forecast_accuracy + accuracy / 10.0)
            elif action_name == "adjust_forecast":
                forecast["projected_revenue"] *= self.np_random.uniform(0.9, 1.1)
                forecast["forecast_confidence"] = min(1.0, forecast["forecast_confidence"] + 0.1)
                self.forecast_queue.insert(0, forecast)
            elif action_name == "update_model":
                forecast["forecast_confidence"] = min(1.0, forecast["forecast_confidence"] + 0.15)
                self.forecast_queue.insert(0, forecast)
            elif action_name == "defer":
                self.forecast_queue.append(forecast)
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.forecast_accuracy
        efficiency_score = len(self.completed_forecasts) / 20.0
        financial_score = self.actual_revenue / 500000.0
        risk_penalty = len([f for f in self.forecast_queue if f["forecast_confidence"] < 0.5]) * 0.2
        compliance_penalty = 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.forecast_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 50 or len(self.forecast_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"forecast_accuracy": self.forecast_accuracy, "low_confidence_waiting": len([f for f in self.forecast_queue if f["forecast_confidence"] < 0.5])},
            operational_efficiency={"queue_length": len(self.forecast_queue), "forecasts_completed": len(self.completed_forecasts)},
            financial_metrics={"actual_revenue": self.actual_revenue, "forecast_accuracy": self.forecast_accuracy},
            patient_satisfaction=1.0 - len(self.forecast_queue) / 20.0,
            risk_score=len([f for f in self.forecast_queue if f["forecast_confidence"] < 0.5]) / 15.0,
            compliance_score=1.0,
            timestamp=self.time_step
        )

