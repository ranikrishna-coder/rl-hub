"""
Lab Test Prioritization Environment
Optimizes lab test ordering and sequencing
System: Epic, Cerner, Allscripts, Meditech
"""

import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator, ConditionSeverity
from simulator.hospital_simulator import HospitalSimulator


class LabTestPrioritizationEnv(HealthcareRLEnvironment):
    """
    Optimizes lab test ordering and sequencing
    
    State: Patient condition, symptoms, previous labs, test queue, urgency
    Action: Order test (basic panel, comprehensive, specific test, defer, cancel)
    Reward: Diagnostic accuracy, turnaround time, cost-effectiveness, patient outcomes
    """
    
    TEST_ACTIONS = [
        "basic_panel",
        "comprehensive_panel",
        "specific_test",
        "defer_test",
        "cancel_test",
        "urgent_test"
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(19,), dtype=np.float32
        )
        
        self.action_space = spaces.Discrete(len(self.TEST_ACTIONS))
        
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        
        self.current_patient = None
        self.test_queue = []
        self.test_history = []
        self.diagnostic_confidence = 0.0
        self.total_cost = 0.0
        self.wait_time = 0.0
        
        self.test_costs = {
            "basic_panel": 150.0,
            "comprehensive_panel": 400.0,
            "specific_test": 200.0,
            "defer_test": 0.0,
            "cancel_test": 0.0,
            "urgent_test": 300.0
        }
    
    def _initialize_state(self) -> np.ndarray:
        """Initialize patient and lab test scenario"""
        self.current_patient = self.patient_generator.generate_patient()
        self.test_queue = []
        self.test_history = []
        self.diagnostic_confidence = 0.3
        self.total_cost = 0.0
        self.wait_time = 0.0
        
        return self._get_state_features()
    
    def _get_state_features(self) -> np.ndarray:
        """Extract current state features"""
        if self.current_patient is None:
            return np.zeros(19, dtype=np.float32)
        
        p = self.current_patient
        
        state = np.array([
            p.age / 100.0,
            1.0 if p.gender == "M" else 0.0,
            p.risk_score,
            self.diagnostic_confidence,
            len(self.test_queue) / 10.0,
            len(self.test_history) / 10.0,
            self.wait_time / 24.0,
            self.total_cost / 5000.0,
            p.vitals.get("temperature", 98.6) / 105.0,
            p.vitals.get("heart_rate", 72) / 150.0,
            p.lab_results.get("wbc", 7) / 20.0,
            p.lab_results.get("glucose", 100) / 200.0,
            p.lab_results.get("creatinine", 1.0) / 2.0,
            p.severity.value / 4.0,
            p.readmission_risk,
            self.current_patient.length_of_stay / 30.0,
            len([h for h in self.test_history if "urgent" in h]) / 5.0,
            p.vitals.get("oxygen_saturation", 98) / 100.0,
            (1.0 - self.diagnostic_confidence) if self.diagnostic_confidence < 0.8 else 0.0
        ], dtype=np.float32)
        
        return state
    
    def _apply_action(self, action: int) -> Dict[str, Any]:
        """Apply lab test action"""
        test_action = self.TEST_ACTIONS[action]
        self.test_history.append(test_action)
        
        transition_info = {
            "test_action": test_action,
            "cost": self.test_costs[test_action]
        }
        
        self.total_cost += self.test_costs[test_action]
        
        # Simulate test effect
        if test_action == "basic_panel":
            self.diagnostic_confidence = min(1.0, self.diagnostic_confidence + 0.2)
            self.wait_time += 2.0
        
        elif test_action == "comprehensive_panel":
            self.diagnostic_confidence = min(1.0, self.diagnostic_confidence + 0.4)
            self.wait_time += 4.0
        
        elif test_action == "specific_test":
            self.diagnostic_confidence = min(1.0, self.diagnostic_confidence + 0.3)
            self.wait_time += 3.0
        
        elif test_action == "defer_test":
            self.wait_time += 1.0
            # Confidence may decrease if deferring critical tests
            if p.risk_score > 0.7:
                self.diagnostic_confidence = max(0, self.diagnostic_confidence - 0.1)
        
        elif test_action == "cancel_test":
            # No effect
            pass
        
        elif test_action == "urgent_test":
            self.diagnostic_confidence = min(1.0, self.diagnostic_confidence + 0.35)
            self.wait_time += 1.0  # Faster turnaround
        
        # Evolve patient state
        self.current_patient = self.patient_generator.evolve_patient(
            self.current_patient, 1.0
        )
        
        return transition_info
    
    def _calculate_reward_components(
        self, state: np.ndarray, action: int, info: Dict[str, Any]
    ) -> Dict[RewardComponent, float]:
        """Calculate reward components"""
        p = self.current_patient
        
        # Clinical score: diagnostic accuracy
        clinical_score = self.diagnostic_confidence
        
        # Efficiency score: turnaround time and test appropriateness
        turnaround_score = 1.0 - min(1.0, self.wait_time / 24.0)
        test_efficiency = 1.0 - len(self.test_history) / 10.0
        efficiency_score = (turnaround_score + test_efficiency) / 2.0
        
        # Financial score: cost-effectiveness
        cost_per_confidence = self.total_cost / max(0.01, self.diagnostic_confidence)
        financial_score = 1.0 / (1.0 + cost_per_confidence / 2000.0)
        
        # Patient satisfaction: faster diagnosis
        patient_satisfaction = 1.0 - min(1.0, self.wait_time / 24.0)
        
        # Risk penalty: delayed diagnosis
        risk_penalty = 0.0
        if self.wait_time > 12.0 and p.risk_score > 0.7:
            risk_penalty = 0.4
        if self.diagnostic_confidence < 0.5 and len(self.test_history) > 3:
            risk_penalty += 0.3
        
        # Compliance penalty: unnecessary tests
        compliance_penalty = 0.0
        if len(self.test_history) > 5 and self.diagnostic_confidence > 0.9:
            compliance_penalty = 0.2
        
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: patient_satisfaction,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    
    def _is_done(self) -> bool:
        """Check if episode is done"""
        if self.current_patient is None:
            return True
        
        # Done if diagnostic confidence high
        if self.diagnostic_confidence >= 0.9:
            return True
        
        # Done if too many tests
        if len(self.test_history) >= 8:
            return True
        
        # Done if wait time too long
        if self.wait_time >= 48.0:
            return True
        
        return False
    
    def _get_kpis(self) -> KPIMetrics:
        """Calculate KPI metrics"""
        if self.current_patient is None:
            return KPIMetrics(
                clinical_outcomes={},
                operational_efficiency={},
                financial_metrics={},
                patient_satisfaction=0.0,
                risk_score=0.0,
                compliance_score=0.0,
                timestamp=self.time_step
            )
        
        p = self.current_patient
        
        return KPIMetrics(
            clinical_outcomes={
                "diagnostic_confidence": self.diagnostic_confidence,
                "test_accuracy": self.diagnostic_confidence,
                "vital_stability": 1.0 - abs(p.vitals.get("temperature", 98.6) - 98.6) / 10.0
            },
            operational_efficiency={
                "tests_ordered": len(self.test_history),
                "wait_time": self.wait_time,
                "tests_per_confidence": len(self.test_history) / max(0.01, self.diagnostic_confidence)
            },
            financial_metrics={
                "total_cost": self.total_cost,
                "cost_per_confidence": self.total_cost / max(0.01, self.diagnostic_confidence),
                "cost_effectiveness": self.diagnostic_confidence / max(0.01, self.total_cost / 2000.0)
            },
            patient_satisfaction=1.0 - min(1.0, self.wait_time / 24.0),
            risk_score=p.risk_score + (0.4 if self.wait_time > 12.0 and p.risk_score > 0.7 else 0.0),
            compliance_score=1.0 - (0.2 if len(self.test_history) > 5 and self.diagnostic_confidence > 0.9 else 0.0),
            timestamp=self.time_step
        )

