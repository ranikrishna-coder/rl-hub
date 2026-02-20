"""AI-Assisted Diagnostics Environment - AI-assisted imaging diagnostics (Philips, GE)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class AIAssistedDiagnosticsEnv(HealthcareRLEnvironment):
    ACTIONS = ["ai_review", "radiologist_review", "ai_plus_radiologist", "defer", "auto_diagnose", "flag_for_review"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(18,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.diagnostic_queue = []
        self.completed_diagnostics = []
        self.ai_accuracy = 0.85
        self.radiologist_accuracy = 0.95
    def _initialize_state(self) -> np.ndarray:
        self.diagnostic_queue = [{"patient": self.patient_generator.generate_patient(), "complexity": self.np_random.uniform(0, 1), "ai_confidence": self.np_random.uniform(0.5, 1.0), "wait_time": 0.0} for _ in range(15)]
        self.completed_diagnostics = []
        self.ai_accuracy = 0.85
        self.radiologist_accuracy = 0.95
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(18, dtype=np.float32)
        state[0] = len(self.diagnostic_queue) / 20.0
        state[1] = len(self.completed_diagnostics) / 20.0
        if self.diagnostic_queue:
            state[2] = self.diagnostic_queue[0]["complexity"]
            state[3] = self.diagnostic_queue[0]["ai_confidence"]
            state[4] = self.diagnostic_queue[0]["wait_time"] / 7.0
        state[5] = self.ai_accuracy
        state[6] = self.radiologist_accuracy
        state[7] = np.mean([d["ai_confidence"] for d in self.diagnostic_queue[:5]]) if self.diagnostic_queue else 0.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.diagnostic_queue:
            diagnostic = self.diagnostic_queue.pop(0)
            if action_name == "ai_review":
                accuracy = self.ai_accuracy
                self.completed_diagnostics.append({**diagnostic, "method": "ai", "accuracy": accuracy})
            elif action_name == "radiologist_review":
                accuracy = self.radiologist_accuracy
                self.completed_diagnostics.append({**diagnostic, "method": "radiologist", "accuracy": accuracy})
            elif action_name == "ai_plus_radiologist":
                accuracy = min(1.0, (self.ai_accuracy + self.radiologist_accuracy) / 2.0 + 0.05)
                self.completed_diagnostics.append({**diagnostic, "method": "combined", "accuracy": accuracy})
            elif action_name == "auto_diagnose":
                accuracy = self.ai_accuracy if diagnostic["ai_confidence"] > 0.9 else self.ai_accuracy - 0.1
                self.completed_diagnostics.append({**diagnostic, "method": "auto", "accuracy": accuracy})
            elif action_name == "defer":
                self.diagnostic_queue.append(diagnostic)
                diagnostic["wait_time"] += 1.0
            elif action_name == "flag_for_review":
                self.completed_diagnostics.append({**diagnostic, "method": "flagged", "accuracy": self.radiologist_accuracy})
        for diagnostic in self.diagnostic_queue:
            diagnostic["wait_time"] += 0.5
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        avg_accuracy = np.mean([d.get("accuracy", 0.8) for d in self.completed_diagnostics]) if self.completed_diagnostics else 0.8
        clinical_score = avg_accuracy
        efficiency_score = len(self.completed_diagnostics) / 20.0
        financial_score = len(self.completed_diagnostics) / 20.0
        risk_penalty = len([d for d in self.diagnostic_queue if d["complexity"] > 0.8 and d["wait_time"] > 2.0]) * 0.2
        compliance_penalty = 0.2 if self.diagnostic_queue and self.diagnostic_queue[0]["complexity"] > 0.8 and self.ACTIONS[action] == "auto_diagnose" else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.diagnostic_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 40 or len(self.diagnostic_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        avg_accuracy = np.mean([d.get("accuracy", 0.8) for d in self.completed_diagnostics]) if self.completed_diagnostics else 0.8
        return KPIMetrics(
            clinical_outcomes={"diagnostic_accuracy": avg_accuracy, "complex_cases_waiting": len([d for d in self.diagnostic_queue if d["complexity"] > 0.8])},
            operational_efficiency={"queue_length": len(self.diagnostic_queue), "diagnostics_completed": len(self.completed_diagnostics)},
            financial_metrics={"completed_count": len(self.completed_diagnostics)},
            patient_satisfaction=1.0 - len(self.diagnostic_queue) / 20.0,
            risk_score=len([d for d in self.diagnostic_queue if d["complexity"] > 0.8 and d["wait_time"] > 2.0]) / 15.0,
            compliance_score=1.0 - (0.2 if self.diagnostic_queue and self.diagnostic_queue[0]["complexity"] > 0.8 else 0.0),
            timestamp=self.time_step
        )

