"""
Pain Management Optimization Environment
Optimizes pain management strategies for patients
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


class PainManagementOptimizationEnv(HealthcareRLEnvironment):
    """
    Optimizes pain management strategies for patients
    
    State: Pain score, patient demographics, pain type, current medications, vitals
    Action: Select pain management intervention (medication, procedure, therapy, monitoring)
    Reward: Pain reduction, patient satisfaction, cost-effectiveness, safety
    """
    
    INTERVENTIONS = [
        "opioid_medication",
        "non_opioid_medication",
        "nerve_block",
        "physical_therapy",
        "monitoring",
        "discharge"
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(18,), dtype=np.float32
        )
        
        self.action_space = spaces.Discrete(len(self.INTERVENTIONS))
        
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        
        self.current_patient = None
        self.pain_history = []
        self.intervention_history = []
        self.total_cost = 0.0
        self.opioid_usage = 0
        
        self.intervention_costs = {
            "opioid_medication": 100.0,
            "non_opioid_medication": 50.0,
            "nerve_block": 500.0,
            "physical_therapy": 200.0,
            "monitoring": 50.0,
            "discharge": 0.0
        }
    
    def _initialize_state(self) -> np.ndarray:
        """Initialize patient and pain management episode"""
        self.current_patient = self.patient_generator.generate_patient()
        self.pain_history = [self.current_patient.vitals.get("pain_score", 5.0)]
        self.intervention_history = []
        self.total_cost = 0.0
        self.opioid_usage = 0
        
        return self._get_state_features()
    
    def _get_state_features(self) -> np.ndarray:
        """Extract current state features"""
        if self.current_patient is None:
            return np.zeros(18, dtype=np.float32)
        
        p = self.current_patient
        current_pain = p.vitals.get("pain_score", 5.0)
        
        state = np.array([
            p.age / 100.0,
            1.0 if p.gender == "M" else 0.0,
            current_pain / 10.0,
            p.risk_score,
            p.vitals.get("bp_systolic", 120) / 200.0,
            p.vitals.get("heart_rate", 72) / 150.0,
            p.vitals.get("respiratory_rate", 16) / 30.0,
            p.vitals.get("oxygen_saturation", 98) / 100.0,
            len(self.intervention_history) / 10.0,
            self.opioid_usage / 5.0,
            self.total_cost / 5000.0,
            (current_pain - self.pain_history[0]) / 10.0 if len(self.pain_history) > 0 else 0.0,
            p.lab_results.get("creatinine", 1.0) / 2.0,
            p.lab_results.get("hemoglobin", 14) / 20.0,
            1.0 if "opioid" in str(self.intervention_history[-1:]) else 0.0,
            len([h for h in self.intervention_history if h == "opioid_medication"]) / 5.0,
            self.current_patient.length_of_stay / 30.0,
            p.readmission_risk,
            p.severity.value / 4.0
        ], dtype=np.float32)
        
        return state
    
    def _apply_action(self, action: int) -> Dict[str, Any]:
        """Apply pain management intervention"""
        intervention = self.INTERVENTIONS[action]
        self.intervention_history.append(intervention)
        
        transition_info = {
            "intervention": intervention,
            "cost": self.intervention_costs[intervention]
        }
        
        self.total_cost += self.intervention_costs[intervention]
        
        # Simulate intervention effect
        current_pain = self.current_patient.vitals.get("pain_score", 5.0)
        
        if intervention == "opioid_medication":
            pain_reduction = min(3.0, current_pain * 0.4)
            self.current_patient.vitals["pain_score"] = max(0, current_pain - pain_reduction)
            self.opioid_usage += 1
            # Risk of respiratory depression
            if self.opioid_usage > 3:
                self.current_patient.vitals["respiratory_rate"] = max(8, 
                    self.current_patient.vitals.get("respiratory_rate", 16) - 2)
        
        elif intervention == "non_opioid_medication":
            pain_reduction = min(2.0, current_pain * 0.3)
            self.current_patient.vitals["pain_score"] = max(0, current_pain - pain_reduction)
        
        elif intervention == "nerve_block":
            pain_reduction = min(5.0, current_pain * 0.6)
            self.current_patient.vitals["pain_score"] = max(0, current_pain - pain_reduction)
        
        elif intervention == "physical_therapy":
            pain_reduction = min(1.5, current_pain * 0.2)
            self.current_patient.vitals["pain_score"] = max(0, current_pain - pain_reduction)
            self.current_patient.risk_score = max(0, self.current_patient.risk_score - 0.05)
        
        elif intervention == "monitoring":
            # No immediate effect
            pass
        
        elif intervention == "discharge":
            transition_info["discharged"] = True
        
        self.pain_history.append(self.current_patient.vitals.get("pain_score", 0.0))
        
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
        current_pain = p.vitals.get("pain_score", 5.0)
        initial_pain = self.pain_history[0] if len(self.pain_history) > 0 else current_pain
        
        # Clinical score: pain reduction
        pain_reduction = (initial_pain - current_pain) / max(0.1, initial_pain)
        vital_stability = 1.0 - abs(p.vitals.get("respiratory_rate", 16) - 16) / 20.0
        clinical_score = (pain_reduction + vital_stability) / 2.0
        
        # Efficiency score: intervention effectiveness
        interventions_per_pain_reduction = len(self.intervention_history) / max(0.1, initial_pain - current_pain)
        efficiency_score = 1.0 / (1.0 + interventions_per_pain_reduction / 5.0)
        
        # Financial score: cost-effectiveness
        cost_per_pain_reduction = self.total_cost / max(0.1, initial_pain - current_pain)
        financial_score = 1.0 / (1.0 + cost_per_pain_reduction / 500.0)
        
        # Patient satisfaction: pain reduction
        patient_satisfaction = 1.0 - current_pain / 10.0
        
        # Risk penalty: opioid overuse, respiratory depression
        risk_penalty = 0.0
        if self.opioid_usage > 3:
            risk_penalty += 0.3
        if p.vitals.get("respiratory_rate", 16) < 12:
            risk_penalty += 0.5
        
        # Compliance penalty: inappropriate interventions
        compliance_penalty = 0.0
        if current_pain < 2.0 and self.intervention_history[-1:] == ["opioid_medication"]:
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
        
        current_pain = self.current_patient.vitals.get("pain_score", 5.0)
        
        # Done if pain controlled and discharged
        if len(self.intervention_history) > 0 and self.intervention_history[-1] == "discharge":
            return True
        
        # Done if pain well controlled (< 3) for multiple steps
        if current_pain < 3.0 and len(self.intervention_history) >= 3:
            return True
        
        # Done if too many interventions
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
        current_pain = p.vitals.get("pain_score", 5.0)
        initial_pain = self.pain_history[0] if len(self.pain_history) > 0 else current_pain
        
        return KPIMetrics(
            clinical_outcomes={
                "pain_score": current_pain,
                "pain_reduction": initial_pain - current_pain,
                "vital_stability": 1.0 - abs(p.vitals.get("respiratory_rate", 16) - 16) / 20.0
            },
            operational_efficiency={
                "interventions_count": len(self.intervention_history),
                "interventions_per_pain_reduction": len(self.intervention_history) / max(0.1, initial_pain - current_pain),
                "time_to_pain_control": len(self.intervention_history)
            },
            financial_metrics={
                "total_cost": self.total_cost,
                "cost_per_pain_reduction": self.total_cost / max(0.1, initial_pain - current_pain),
                "cost_effectiveness": (initial_pain - current_pain) / max(0.01, self.total_cost / 1000.0)
            },
            patient_satisfaction=1.0 - current_pain / 10.0,
            risk_score=p.risk_score + (0.3 if self.opioid_usage > 3 else 0.0),
            compliance_score=1.0 - (0.2 if current_pain < 2.0 and self.intervention_history[-1:] == ["opioid_medication"] else 0.0),
            timestamp=self.time_step
        )

