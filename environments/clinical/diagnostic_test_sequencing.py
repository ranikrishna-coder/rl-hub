"""Diagnostic Test Sequencing Environment - Optimizes test ordering for diagnosis"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class DiagnosticTestSequencingEnv(HealthcareRLEnvironment):
    TESTS = ["blood_test", "imaging", "biopsy", "ecg", "endoscopy", "no_more_tests"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(16,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.TESTS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.current_patient = None
        self.tests_ordered = []
        self.diagnosis_confidence = 0.0
        self.total_test_cost = 0.0
    def _initialize_state(self) -> np.ndarray:
        self.current_patient = self.patient_generator.generate_patient()
        self.tests_ordered = []
        self.diagnosis_confidence = 0.0
        self.total_test_cost = 0.0
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        if not self.current_patient:
            return np.zeros(16, dtype=np.float32)
        p = self.current_patient
        test_costs = {"blood_test": 100, "imaging": 500, "biopsy": 2000, "ecg": 150, "endoscopy": 3000}
        return np.array([
            p.age / 100.0, p.risk_score, len(p.conditions) / 5.0,
            p.vitals.get("temperature", 98.6) / 105.0,
            p.vitals.get("heart_rate", 72) / 150.0,
            p.lab_results.get("wbc", 7) / 20.0,
            p.lab_results.get("glucose", 100) / 200.0,
            len(self.tests_ordered) / 10.0,
            self.diagnosis_confidence,
            self.total_test_cost / 10000.0,
            1.0 if "blood_test" in self.tests_ordered else 0.0,
            1.0 if "imaging" in self.tests_ordered else 0.0,
            1.0 if "biopsy" in self.tests_ordered else 0.0,
            1.0 if "ecg" in self.tests_ordered else 0.0,
            1.0 if "endoscopy" in self.tests_ordered else 0.0,
            len(set(self.tests_ordered)) / 5.0
        ], dtype=np.float32)
    def _apply_action(self, action: int) -> Dict[str, Any]:
        test = self.TESTS[action]
        if test != "no_more_tests":
            self.tests_ordered.append(test)
            test_costs = {"blood_test": 100, "imaging": 500, "biopsy": 2000, "ecg": 150, "endoscopy": 3000}
            self.total_test_cost += test_costs.get(test, 0)
            self.diagnosis_confidence = min(1.0, self.diagnosis_confidence + 0.15)
        return {"test": test, "confidence": self.diagnosis_confidence}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = self.diagnosis_confidence
        efficiency_score = 1.0 - len(self.tests_ordered) / 10.0 if self.diagnosis_confidence > 0.8 else 0.5
        financial_score = 1.0 / (1.0 + self.total_test_cost / 5000.0)
        risk_penalty = 0.0 if self.diagnosis_confidence > 0.7 else 0.3
        compliance_penalty = 0.0 if len(self.tests_ordered) <= 5 else 0.2
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: self.diagnosis_confidence,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.TESTS[self.action_space.sample()] == "no_more_tests" if hasattr(self, 'action_space') else len(self.tests_ordered) >= 5 or self.diagnosis_confidence >= 0.9
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"diagnosis_confidence": self.diagnosis_confidence},
            operational_efficiency={"tests_ordered": len(self.tests_ordered), "time_to_diagnosis": len(self.tests_ordered)},
            financial_metrics={"test_cost": self.total_test_cost},
            patient_satisfaction=self.diagnosis_confidence,
            risk_score=1.0 - self.diagnosis_confidence,
            compliance_score=1.0 - (0.2 if len(self.tests_ordered) > 5 else 0.0),
            timestamp=self.time_step
        )

