"""
Stroke Intervention Scheduling Environment
Optimizes stroke intervention timing and sequencing
System: Epic, Cerner, Allscripts
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


class StrokeInterventionSchedulingEnv(HealthcareRLEnvironment):
    """
    Optimizes stroke intervention timing and sequencing
    
    State: Stroke type, time since onset, NIHSS score, patient demographics, facility capabilities
    Action: TPA administration, thrombectomy, monitoring, transfer, discharge, rehab referral
    Reward: Functional outcomes, time to treatment, mortality reduction, cost-effectiveness
    """
    
    ACTIONS = [
        "tpa_administration",
        "thrombectomy",
        "monitoring",
        "transfer",
        "discharge",
        "rehab_referral"
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(20,), dtype=np.float32
        )
        
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        
        self.current_patient = None
        self.time_since_onset = 0.0
        self.nihss_score = 0.0
        self.intervention_history = []
        self.total_cost = 0.0
        self.functional_outcome = 0.0
        
        self.action_costs = {
            "tpa_administration": 5000.0,
            "thrombectomy": 15000.0,
            "monitoring": 200.0,
            "transfer": 2000.0,
            "discharge": 0.0,
            "rehab_referral": 1000.0
        }
    
    def _initialize_state(self) -> np.ndarray:
        """Initialize stroke scenario"""
        self.current_patient = self.patient_generator.generate_patient()
        self.time_since_onset = self.np_random.uniform(0.5, 6.0)  # Hours since stroke
        self.nihss_score = self.np_random.uniform(5.0, 25.0)  # NIHSS score
        self.intervention_history = []
        self.total_cost = 0.0
        self.functional_outcome = 1.0 - (self.nihss_score / 42.0)  # Initial outcome
        
        return self._get_state_features()
    
    def _get_state_features(self) -> np.ndarray:
        """Extract current state features"""
        if self.current_patient is None:
            return np.zeros(20, dtype=np.float32)
        
        p = self.current_patient
        
        state = np.array([
            p.age / 100.0,
            1.0 if p.gender == "M" else 0.0,
            self.time_since_onset / 6.0,
            self.nihss_score / 42.0,
            self.functional_outcome,
            p.risk_score,
            p.vitals.get("bp_systolic", 120) / 200.0,
            p.vitals.get("heart_rate", 72) / 150.0,
            p.vitals.get("glucose", 100) / 200.0,
            len(self.intervention_history) / 10.0,
            self.total_cost / 50000.0,
            1.0 if "tpa" in str(self.intervention_history) else 0.0,
            1.0 if "thrombectomy" in str(self.intervention_history) else 0.0,
            p.readmission_risk,
            p.severity.value / 4.0,
            self.current_patient.length_of_stay / 30.0,
            p.vitals.get("oxygen_saturation", 98) / 100.0,
            (6.0 - self.time_since_onset) / 6.0 if self.time_since_onset < 6.0 else 0.0,
            p.lab_results.get("creatinine", 1.0) / 2.0,
            p.vitals.get("temperature", 98.6) / 105.0
        ], dtype=np.float32)
        
        return state
    
    def _apply_action(self, action: int) -> Dict[str, Any]:
        """Apply stroke intervention"""
        intervention = self.ACTIONS[action]
        self.intervention_history.append(intervention)
        
        transition_info = {
            "intervention": intervention,
            "cost": self.action_costs[intervention]
        }
        
        self.total_cost += self.action_costs[intervention]
        
        # Simulate intervention effect
        if intervention == "tpa_administration":
            # Time-sensitive: better outcomes if < 4.5 hours
            if self.time_since_onset < 4.5:
                improvement = 0.3
            elif self.time_since_onset < 6.0:
                improvement = 0.15
            else:
                improvement = 0.05
            self.nihss_score = max(0, self.nihss_score - improvement * 10)
            self.functional_outcome = min(1.0, self.functional_outcome + improvement)
            self.current_patient.risk_score = max(0, self.current_patient.risk_score - 0.2)
        
        elif intervention == "thrombectomy":
            # Effective up to 24 hours for large vessel occlusion
            if self.time_since_onset < 6.0:
                improvement = 0.4
            elif self.time_since_onset < 24.0:
                improvement = 0.25
            else:
                improvement = 0.1
            self.nihss_score = max(0, self.nihss_score - improvement * 12)
            self.functional_outcome = min(1.0, self.functional_outcome + improvement)
            self.current_patient.risk_score = max(0, self.current_patient.risk_score - 0.25)
        
        elif intervention == "monitoring":
            # No immediate effect, but tracks progress
            self.time_since_onset += 0.5
        
        elif intervention == "transfer":
            # Transfer to comprehensive stroke center
            self.time_since_onset += 1.0
            transition_info["transferred"] = True
        
        elif intervention == "discharge":
            transition_info["discharged"] = True
        
        elif intervention == "rehab_referral":
            # Improves long-term outcomes
            self.functional_outcome = min(1.0, self.functional_outcome + 0.1)
        
        # Time progresses
        self.time_since_onset += 0.5
        
        # Evolve patient state
        self.current_patient = self.patient_generator.evolve_patient(
            self.current_patient, 1.0
        )
        
        return transition_info
    
    def _calculate_reward_components(
        self, state: np.ndarray, action: int, info: Dict[str, Any]
    ) -> Dict[RewardComponent, float]:
        """Calculate reward components"""
        # Clinical score: functional outcome
        clinical_score = self.functional_outcome
        
        # Efficiency score: time to treatment
        time_efficiency = 1.0 - min(1.0, self.time_since_onset / 6.0)
        efficiency_score = time_efficiency * (1.0 - len(self.intervention_history) / 10.0)
        
        # Financial score: cost-effectiveness
        cost_per_outcome = self.total_cost / max(0.01, self.functional_outcome)
        financial_score = 1.0 / (1.0 + cost_per_outcome / 50000.0)
        
        # Patient satisfaction: better outcomes
        patient_satisfaction = self.functional_outcome
        
        # Risk penalty: delayed treatment, poor outcomes
        risk_penalty = 0.0
        if self.time_since_onset > 6.0 and "tpa_administration" not in str(self.intervention_history):
            risk_penalty += 0.4
        if self.functional_outcome < 0.5:
            risk_penalty += 0.3
        
        # Compliance penalty: inappropriate sequencing
        compliance_penalty = 0.0
        if len(self.intervention_history) > 1 and self.intervention_history[-1] == "tpa_administration" and "thrombectomy" in str(self.intervention_history[:-1]):
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
        
        if self.time_since_onset >= 24.0:
            return True
        
        if len(self.intervention_history) >= 8:
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
                "nihss_score": self.nihss_score,
                "functional_outcome": self.functional_outcome,
                "time_to_treatment": self.time_since_onset
            },
            operational_efficiency={
                "interventions_count": len(self.intervention_history),
                "time_to_treatment": self.time_since_onset,
                "treatment_efficiency": (1.0 - self.time_since_onset / 6.0) if self.time_since_onset < 6.0 else 0.0
            },
            financial_metrics={
                "total_cost": self.total_cost,
                "cost_per_outcome": self.total_cost / max(0.01, self.functional_outcome),
                "cost_effectiveness": self.functional_outcome / max(0.01, self.total_cost / 50000.0)
            },
            patient_satisfaction=self.functional_outcome,
            risk_score=p.risk_score + (0.4 if self.time_since_onset > 6.0 and "tpa_administration" not in str(self.intervention_history) else 0.0),
            compliance_score=1.0 - (0.2 if len(self.intervention_history) > 1 and self.intervention_history[-1] == "tpa_administration" and "thrombectomy" in str(self.intervention_history[:-1]) else 0.0),
            timestamp=self.time_step
        )

