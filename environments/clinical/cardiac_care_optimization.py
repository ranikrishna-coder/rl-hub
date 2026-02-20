"""
Cardiac Care Optimization Environment
Optimizes cardiac care pathways and interventions
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


class CardiacCareOptimizationEnv(HealthcareRLEnvironment):
    """
    Optimizes cardiac care pathways
    
    State: Cardiac condition, troponin levels, EKG findings, patient demographics, risk factors
    Action: Cardiac cath, medication, monitoring, surgery, discharge, followup
    Reward: Cardiac outcomes, time to intervention, mortality reduction, cost-effectiveness
    """
    
    ACTIONS = [
        "cardiac_cath",
        "medication",
        "monitoring",
        "surgery",
        "discharge",
        "followup"
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(22,), dtype=np.float32
        )
        
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        
        self.current_patient = None
        self.troponin_level = 0.0
        self.cardiac_function = 0.0
        self.intervention_history = []
        self.total_cost = 0.0
        
        self.action_costs = {
            "cardiac_cath": 8000.0,
            "medication": 200.0,
            "monitoring": 300.0,
            "surgery": 50000.0,
            "discharge": 0.0,
            "followup": 500.0
        }
    
    def _initialize_state(self) -> np.ndarray:
        """Initialize cardiac care scenario"""
        self.current_patient = self.patient_generator.generate_patient()
        self.troponin_level = self.np_random.uniform(0.01, 5.0)
        self.cardiac_function = self.np_random.uniform(0.3, 1.0)
        self.intervention_history = []
        self.total_cost = 0.0
        
        return self._get_state_features()
    
    def _get_state_features(self) -> np.ndarray:
        """Extract current state features"""
        if self.current_patient is None:
            return np.zeros(22, dtype=np.float32)
        
        p = self.current_patient
        
        state = np.array([
            p.age / 100.0,
            1.0 if p.gender == "M" else 0.0,
            self.troponin_level / 5.0,
            self.cardiac_function,
            p.risk_score,
            p.vitals.get("bp_systolic", 120) / 200.0,
            p.vitals.get("heart_rate", 72) / 150.0,
            p.vitals.get("oxygen_saturation", 98) / 100.0,
            len(self.intervention_history) / 10.0,
            self.total_cost / 100000.0,
            1.0 if "cardiac_cath" in str(self.intervention_history) else 0.0,
            1.0 if "surgery" in str(self.intervention_history) else 0.0,
            p.readmission_risk,
            p.severity.value / 4.0,
            self.current_patient.length_of_stay / 30.0,
            p.lab_results.get("creatinine", 1.0) / 2.0,
            p.vitals.get("temperature", 98.6) / 105.0,
            (1.0 - self.cardiac_function) if self.cardiac_function < 0.5 else 0.0,
            p.vitals.get("pain_score", 0) / 10.0,
            self.troponin_level / 5.0 if self.troponin_level > 0.04 else 0.0,
            len([h for h in self.intervention_history if h == "medication"]) / 5.0,
            p.risk_score
        ], dtype=np.float32)
        
        return state
    
    def _apply_action(self, action: int) -> Dict[str, Any]:
        """Apply cardiac care intervention"""
        intervention = self.ACTIONS[action]
        self.intervention_history.append(intervention)
        
        transition_info = {
            "intervention": intervention,
            "cost": self.action_costs[intervention]
        }
        
        self.total_cost += self.action_costs[intervention]
        
        # Simulate intervention effect
        if intervention == "cardiac_cath":
            # Diagnostic and potentially therapeutic
            if self.troponin_level > 0.04:
                self.cardiac_function = min(1.0, self.cardiac_function + 0.2)
                self.troponin_level = max(0.01, self.troponin_level - 0.5)
            self.current_patient.risk_score = max(0, self.current_patient.risk_score - 0.15)
        
        elif intervention == "medication":
            # Cardiac medications
            self.cardiac_function = min(1.0, self.cardiac_function + 0.1)
            self.troponin_level = max(0.01, self.troponin_level - 0.1)
            self.current_patient.vitals["heart_rate"] = max(50, 
                self.current_patient.vitals.get("heart_rate", 72) - 5)
        
        elif intervention == "monitoring":
            # Continuous monitoring
            pass
        
        elif intervention == "surgery":
            # Cardiac surgery
            if self.cardiac_function < 0.5:
                self.cardiac_function = min(1.0, self.cardiac_function + 0.4)
            self.troponin_level = max(0.01, self.troponin_level - 1.0)
            self.current_patient.risk_score = max(0, self.current_patient.risk_score - 0.3)
        
        elif intervention == "discharge":
            transition_info["discharged"] = True
        
        elif intervention == "followup":
            # Long-term care
            self.cardiac_function = min(1.0, self.cardiac_function + 0.05)
        
        # Evolve patient state
        self.current_patient = self.patient_generator.evolve_patient(
            self.current_patient, 1.0
        )
        
        return transition_info
    
    def _calculate_reward_components(
        self, state: np.ndarray, action: int, info: Dict[str, Any]
    ) -> Dict[RewardComponent, float]:
        """Calculate reward components"""
        # Clinical score: cardiac function
        clinical_score = self.cardiac_function
        
        # Efficiency score: appropriate intervention timing
        troponin_normalized = 1.0 - min(1.0, self.troponin_level / 5.0)
        efficiency_score = (troponin_normalized + (1.0 - len(self.intervention_history) / 10.0)) / 2.0
        
        # Financial score: cost-effectiveness
        cost_per_improvement = self.total_cost / max(0.01, self.cardiac_function)
        financial_score = 1.0 / (1.0 + cost_per_improvement / 100000.0)
        
        # Patient satisfaction: better outcomes
        patient_satisfaction = self.cardiac_function
        
        # Risk penalty: delayed intervention, poor outcomes
        risk_penalty = 0.0
        if self.troponin_level > 0.04 and "cardiac_cath" not in str(self.intervention_history):
            risk_penalty += 0.4
        if self.cardiac_function < 0.4:
            risk_penalty += 0.5
        
        # Compliance penalty: inappropriate sequencing
        compliance_penalty = 0.0
        if len(self.intervention_history) > 2 and self.intervention_history[-1] == "surgery" and "cardiac_cath" not in str(self.intervention_history[:-1]):
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
        
        if len(self.intervention_history) > 0 and self.intervention_history[-1] == "discharge":
            return True
        
        if self.cardiac_function >= 0.9:
            return True
        
        if len(self.intervention_history) >= 10:
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
                "cardiac_function": self.cardiac_function,
                "troponin_level": self.troponin_level,
                "vital_stability": 1.0 - abs(p.vitals.get("heart_rate", 72) - 72) / 50.0
            },
            operational_efficiency={
                "interventions_count": len(self.intervention_history),
                "time_to_intervention": len(self.intervention_history),
                "treatment_efficiency": self.cardiac_function / max(1, len(self.intervention_history))
            },
            financial_metrics={
                "total_cost": self.total_cost,
                "cost_per_improvement": self.total_cost / max(0.01, self.cardiac_function),
                "cost_effectiveness": self.cardiac_function / max(0.01, self.total_cost / 100000.0)
            },
            patient_satisfaction=self.cardiac_function,
            risk_score=p.risk_score + (0.4 if self.troponin_level > 0.04 and "cardiac_cath" not in str(self.intervention_history) else 0.0),
            compliance_score=1.0 - (0.2 if len(self.intervention_history) > 2 and self.intervention_history[-1] == "surgery" and "cardiac_cath" not in str(self.intervention_history[:-1]) else 0.0),
            timestamp=self.time_step
        )

