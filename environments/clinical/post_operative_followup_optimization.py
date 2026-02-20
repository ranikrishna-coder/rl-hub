"""
Post-Operative Follow-up Optimization Environment
Optimizes post-operative follow-up care
System: Epic, Cerner, Meditech
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


class PostOperativeFollowupOptimizationEnv(HealthcareRLEnvironment):
    """
    Optimizes post-operative follow-up care
    
    State: Days post-op, wound status, pain level, complications, patient demographics
    Action: Wound check, pain management, complication screening, discharge, followup, monitoring
    Reward: Recovery outcomes, complication prevention, patient satisfaction, cost-effectiveness
    """
    
    ACTIONS = [
        "wound_check",
        "pain_management",
        "complication_screening",
        "discharge",
        "followup",
        "monitoring"
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32
        )
        
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        
        self.current_patient = None
        self.days_post_op = 0
        self.wound_status = 0.0
        self.complication_risk = 0.0
        self.intervention_history = []
        self.total_cost = 0.0
        
        self.action_costs = {
            "wound_check": 200.0,
            "pain_management": 150.0,
            "complication_screening": 300.0,
            "discharge": 0.0,
            "followup": 250.0,
            "monitoring": 100.0
        }
    
    def _initialize_state(self) -> np.ndarray:
        """Initialize post-operative scenario"""
        self.current_patient = self.patient_generator.generate_patient()
        self.days_post_op = 1
        self.wound_status = 0.7  # Initial healing
        self.complication_risk = self.np_random.uniform(0.2, 0.6)
        self.intervention_history = []
        self.total_cost = 0.0
        
        return self._get_state_features()
    
    def _get_state_features(self) -> np.ndarray:
        """Extract current state features"""
        if self.current_patient is None:
            return np.zeros(17, dtype=np.float32)
        
        p = self.current_patient
        pain_level = p.vitals.get("pain_score", 5.0)
        
        state = np.array([
            p.age / 100.0,
            1.0 if p.gender == "M" else 0.0,
            self.days_post_op / 30.0,
            self.wound_status,
            self.complication_risk,
            pain_level / 10.0,
            p.risk_score,
            len(self.intervention_history) / 10.0,
            self.total_cost / 5000.0,
            len([h for h in self.intervention_history if h == "wound_check"]) / 5.0,
            p.readmission_risk,
            p.severity.value / 4.0,
            self.current_patient.length_of_stay / 30.0,
            p.vitals.get("temperature", 98.6) / 105.0,
            p.vitals.get("heart_rate", 72) / 150.0,
            (1.0 - self.wound_status) if self.wound_status < 0.3 else 0.0,
            p.risk_score
        ], dtype=np.float32)
        
        return state
    
    def _apply_action(self, action: int) -> Dict[str, Any]:
        """Apply post-operative intervention"""
        intervention = self.ACTIONS[action]
        self.intervention_history.append(intervention)
        
        transition_info = {
            "intervention": intervention,
            "cost": self.action_costs[intervention]
        }
        
        self.total_cost += self.action_costs[intervention]
        
        # Simulate intervention effect
        if intervention == "wound_check":
            # Monitor healing
            if self.wound_status < 0.9:
                self.wound_status = min(1.0, self.wound_status + 0.1)
            self.complication_risk = max(0, self.complication_risk - 0.05)
        
        elif intervention == "pain_management":
            # Reduce pain
            self.current_patient.vitals["pain_score"] = max(0, 
                self.current_patient.vitals.get("pain_score", 5.0) - 2.0)
            self.wound_status = min(1.0, self.wound_status + 0.05)
        
        elif intervention == "complication_screening":
            # Early detection
            if self.complication_risk > 0.3:
                self.complication_risk = max(0, self.complication_risk - 0.2)
            self.wound_status = min(1.0, self.wound_status + 0.05)
        
        elif intervention == "discharge":
            transition_info["discharged"] = True
        
        elif intervention == "followup":
            # Long-term care
            self.wound_status = min(1.0, self.wound_status + 0.08)
            self.complication_risk = max(0, self.complication_risk - 0.1)
        
        elif intervention == "monitoring":
            # Track progress
            pass
        
        # Natural healing
        self.days_post_op += 1
        if self.days_post_op > 3:
            self.wound_status = min(1.0, self.wound_status + 0.02)
            self.complication_risk = max(0, self.complication_risk - 0.01)
        
        # Complications may develop
        if self.complication_risk > 0.5 and self.days_post_op > 5:
            self.wound_status = max(0, self.wound_status - 0.1)
            self.current_patient.risk_score = min(1.0, self.current_patient.risk_score + 0.05)
        
        # Evolve patient state
        self.current_patient = self.patient_generator.evolve_patient(
            self.current_patient, 1.0
        )
        
        return transition_info
    
    def _calculate_reward_components(
        self, state: np.ndarray, action: int, info: Dict[str, Any]
    ) -> Dict[RewardComponent, float]:
        """Calculate reward components"""
        # Clinical score: wound healing
        healing_score = self.wound_status
        complication_prevention = 1.0 - self.complication_risk
        clinical_score = (healing_score + complication_prevention) / 2.0
        
        # Efficiency score: recovery speed
        recovery_efficiency = self.wound_status / max(1, self.days_post_op / 7.0)
        efficiency_score = min(1.0, recovery_efficiency)
        
        # Financial score: cost-effectiveness
        cost_per_healing = self.total_cost / max(0.01, self.wound_status)
        financial_score = 1.0 / (1.0 + cost_per_healing / 2000.0)
        
        # Patient satisfaction: pain reduction, faster recovery
        pain_reduction = 1.0 - self.current_patient.vitals.get("pain_score", 5.0) / 10.0
        patient_satisfaction = (healing_score + pain_reduction) / 2.0
        
        # Risk penalty: complications, delayed healing
        risk_penalty = 0.0
        if self.complication_risk > 0.6:
            risk_penalty += 0.4
        if self.wound_status < 0.5 and self.days_post_op > 10:
            risk_penalty += 0.3
        
        # Compliance penalty: inappropriate discharge
        compliance_penalty = 0.0
        if len(self.intervention_history) > 0 and self.intervention_history[-1] == "discharge" and (self.wound_status < 0.7 or self.complication_risk > 0.4):
            compliance_penalty = 0.3
        
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
        
        if len(self.intervention_history) > 0 and self.intervention_history[-1] == "discharge":
            return True
        
        if self.wound_status >= 0.9 and self.complication_risk < 0.2:
            return True
        
        if self.days_post_op >= 30:
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
                "wound_status": self.wound_status,
                "days_post_op": self.days_post_op,
                "complication_risk": self.complication_risk,
                "pain_level": p.vitals.get("pain_score", 5.0)
            },
            operational_efficiency={
                "interventions_count": len(self.intervention_history),
                "wound_checks": len([h for h in self.intervention_history if h == "wound_check"]),
                "recovery_efficiency": self.wound_status / max(1, self.days_post_op / 7.0)
            },
            financial_metrics={
                "total_cost": self.total_cost,
                "cost_per_healing": self.total_cost / max(0.01, self.wound_status),
                "cost_effectiveness": self.wound_status / max(0.01, self.total_cost / 2000.0)
            },
            patient_satisfaction=(self.wound_status + (1.0 - p.vitals.get("pain_score", 5.0) / 10.0)) / 2.0,
            risk_score=p.risk_score + (0.4 if self.complication_risk > 0.6 else 0.0),
            compliance_score=1.0 - (0.3 if len(self.intervention_history) > 0 and self.intervention_history[-1] == "discharge" and (self.wound_status < 0.7 or self.complication_risk > 0.4) else 0.0),
            timestamp=self.time_step
        )

