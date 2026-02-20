"""
Mental Health Intervention Sequencing Environment
Optimizes mental health intervention sequencing
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


class MentalHealthInterventionSequencingEnv(HealthcareRLEnvironment):
    """
    Optimizes mental health intervention sequencing
    
    State: Mental health assessment, severity, patient demographics, risk factors, medication history
    Action: Medication, therapy, crisis intervention, monitoring, discharge, referral
    Reward: Symptom improvement, safety, patient engagement, cost-effectiveness
    """
    
    ACTIONS = [
        "medication",
        "therapy",
        "crisis_intervention",
        "monitoring",
        "discharge",
        "referral"
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(19,), dtype=np.float32
        )
        
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        
        self.current_patient = None
        self.symptom_severity = 0.0
        self.safety_risk = 0.0
        self.intervention_history = []
        self.total_cost = 0.0
        self.engagement_score = 0.5
        
        self.action_costs = {
            "medication": 200.0,
            "therapy": 300.0,
            "crisis_intervention": 500.0,
            "monitoring": 150.0,
            "discharge": 0.0,
            "referral": 400.0
        }
    
    def _initialize_state(self) -> np.ndarray:
        """Initialize mental health scenario"""
        self.current_patient = self.patient_generator.generate_patient()
        self.symptom_severity = self.np_random.uniform(0.4, 1.0)
        self.safety_risk = self.np_random.uniform(0.1, 0.8)
        self.intervention_history = []
        self.total_cost = 0.0
        self.engagement_score = 0.5
        
        return self._get_state_features()
    
    def _get_state_features(self) -> np.ndarray:
        """Extract current state features"""
        if self.current_patient is None:
            return np.zeros(19, dtype=np.float32)
        
        p = self.current_patient
        
        state = np.array([
            p.age / 100.0,
            1.0 if p.gender == "M" else 0.0,
            self.symptom_severity,
            self.safety_risk,
            self.engagement_score,
            p.risk_score,
            len(self.intervention_history) / 10.0,
            self.total_cost / 5000.0,
            len([h for h in self.intervention_history if h == "medication"]) / 5.0,
            len([h for h in self.intervention_history if h == "therapy"]) / 5.0,
            p.readmission_risk,
            p.severity.value / 4.0,
            self.current_patient.length_of_stay / 30.0,
            p.vitals.get("heart_rate", 72) / 150.0,
            p.vitals.get("bp_systolic", 120) / 200.0,
            (1.0 - self.symptom_severity) if self.symptom_severity < 0.5 else 0.0,
            self.safety_risk,
            p.risk_score,
            self.engagement_score
        ], dtype=np.float32)
        
        return state
    
    def _apply_action(self, action: int) -> Dict[str, Any]:
        """Apply mental health intervention"""
        intervention = self.ACTIONS[action]
        self.intervention_history.append(intervention)
        
        transition_info = {
            "intervention": intervention,
            "cost": self.action_costs[intervention]
        }
        
        self.total_cost += self.action_costs[intervention]
        
        # Simulate intervention effect
        if intervention == "medication":
            # Reduces symptoms
            self.symptom_severity = max(0, self.symptom_severity - 0.2)
            self.safety_risk = max(0, self.safety_risk - 0.15)
            self.engagement_score = min(1.0, self.engagement_score + 0.1)
        
        elif intervention == "therapy":
            # Long-term improvement
            self.symptom_severity = max(0, self.symptom_severity - 0.15)
            self.engagement_score = min(1.0, self.engagement_score + 0.2)
        
        elif intervention == "crisis_intervention":
            # Immediate safety
            self.safety_risk = max(0, self.safety_risk - 0.4)
            self.symptom_severity = max(0, self.symptom_severity - 0.1)
        
        elif intervention == "monitoring":
            # Track progress
            pass
        
        elif intervention == "discharge":
            transition_info["discharged"] = True
        
        elif intervention == "referral":
            # Specialized care
            self.symptom_severity = max(0, self.symptom_severity - 0.1)
            self.engagement_score = min(1.0, self.engagement_score + 0.15)
        
        # Symptoms may worsen without intervention
        if len(self.intervention_history) > 0 and self.intervention_history[-1] == "monitoring":
            self.symptom_severity = min(1.0, self.symptom_severity + 0.05)
        
        # Evolve patient state
        self.current_patient = self.patient_generator.evolve_patient(
            self.current_patient, 1.0
        )
        
        return transition_info
    
    def _calculate_reward_components(
        self, state: np.ndarray, action: int, info: Dict[str, Any]
    ) -> Dict[RewardComponent, float]:
        """Calculate reward components"""
        # Clinical score: symptom improvement
        symptom_improvement = 1.0 - self.symptom_severity
        safety_score = 1.0 - self.safety_risk
        clinical_score = (symptom_improvement + safety_score) / 2.0
        
        # Efficiency score: intervention effectiveness
        efficiency_score = symptom_improvement * (1.0 - len(self.intervention_history) / 10.0)
        
        # Financial score: cost-effectiveness
        cost_per_improvement = self.total_cost / max(0.01, symptom_improvement)
        financial_score = 1.0 / (1.0 + cost_per_improvement / 2000.0)
        
        # Patient satisfaction: engagement and improvement
        patient_satisfaction = self.engagement_score * symptom_improvement
        
        # Risk penalty: high safety risk, poor outcomes
        risk_penalty = 0.0
        if self.safety_risk > 0.6:
            risk_penalty += 0.5
        if self.symptom_severity > 0.8:
            risk_penalty += 0.3
        
        # Compliance penalty: inappropriate sequencing
        compliance_penalty = 0.0
        if len(self.intervention_history) > 3 and self.symptom_severity < 0.3 and self.intervention_history[-1] != "discharge":
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
        
        if self.symptom_severity < 0.3 and self.safety_risk < 0.3:
            return True
        
        if len(self.intervention_history) >= 12:
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
        symptom_improvement = 1.0 - self.symptom_severity
        
        return KPIMetrics(
            clinical_outcomes={
                "symptom_severity": self.symptom_severity,
                "symptom_improvement": symptom_improvement,
                "safety_risk": self.safety_risk,
                "engagement_score": self.engagement_score
            },
            operational_efficiency={
                "interventions_count": len(self.intervention_history),
                "therapy_sessions": len([h for h in self.intervention_history if h == "therapy"]),
                "treatment_efficiency": symptom_improvement / max(1, len(self.intervention_history))
            },
            financial_metrics={
                "total_cost": self.total_cost,
                "cost_per_improvement": self.total_cost / max(0.01, symptom_improvement),
                "cost_effectiveness": symptom_improvement / max(0.01, self.total_cost / 2000.0)
            },
            patient_satisfaction=self.engagement_score * symptom_improvement,
            risk_score=p.risk_score + (0.5 if self.safety_risk > 0.6 else 0.0),
            compliance_score=1.0 - (0.2 if len(self.intervention_history) > 3 and self.symptom_severity < 0.3 and self.intervention_history[-1] != "discharge" else 0.0),
            timestamp=self.time_step
        )

