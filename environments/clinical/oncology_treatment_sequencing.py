"""
Oncology Treatment Sequencing Environment
Optimizes cancer treatment sequences and timing
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


class OncologyTreatmentSequencingEnv(HealthcareRLEnvironment):
    """
    Optimizes cancer treatment sequences
    
    State: Cancer type, stage, patient demographics, biomarkers, treatment history, side effects
    Action: Select treatment (chemotherapy, radiation, immunotherapy, surgery, monitoring)
    Reward: Tumor response, survival, quality of life, cost-effectiveness
    """
    
    TREATMENTS = [
        "chemotherapy",
        "radiation_therapy",
        "immunotherapy",
        "surgery",
        "targeted_therapy",
        "monitoring"
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(22,), dtype=np.float32
        )
        
        self.action_space = spaces.Discrete(len(self.TREATMENTS))
        
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        
        self.current_patient = None
        self.tumor_size = 0.0
        self.treatment_cycle = 0
        self.treatment_history = []
        self.side_effects = 0.0
        self.total_cost = 0.0
        
        self.treatment_costs = {
            "chemotherapy": 5000.0,
            "radiation_therapy": 3000.0,
            "immunotherapy": 8000.0,
            "surgery": 15000.0,
            "targeted_therapy": 6000.0,
            "monitoring": 500.0
        }
    
    def _initialize_state(self) -> np.ndarray:
        """Initialize patient and cancer"""
        self.current_patient = self.patient_generator.generate_patient()
        self.tumor_size = self.np_random.uniform(0.5, 1.0)
        self.treatment_cycle = 0
        self.treatment_history = []
        self.side_effects = 0.0
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
            self.tumor_size,
            p.risk_score,
            self.treatment_cycle / 10.0,
            self.side_effects,
            p.vitals.get("hemoglobin", 14) / 20.0,
            p.vitals.get("wbc", 7) / 20.0,
            p.vitals.get("heart_rate", 72) / 150.0,
            len(self.treatment_history) / 10.0,
            self.total_cost / 50000.0,
            len([h for h in self.treatment_history if h == "chemotherapy"]) / 5.0,
            len([h for h in self.treatment_history if h == "immunotherapy"]) / 5.0,
            p.readmission_risk,
            p.severity.value / 4.0,
            self.current_patient.length_of_stay / 90.0,
            p.lab_results.get("creatinine", 1.0) / 2.0,
            p.vitals.get("oxygen_saturation", 98) / 100.0,
            (1.0 - self.tumor_size) if self.tumor_size < 1.0 else 0.0,
            self.side_effects / 10.0,
            p.vitals.get("pain_score", 0) / 10.0,
            p.risk_score
        ], dtype=np.float32)
        
        return state
    
    def _apply_action(self, action: int) -> Dict[str, Any]:
        """Apply oncology treatment"""
        treatment = self.TREATMENTS[action]
        self.treatment_history.append(treatment)
        self.treatment_cycle += 1
        
        transition_info = {
            "treatment": treatment,
            "cycle": self.treatment_cycle,
            "cost": self.treatment_costs[treatment]
        }
        
        self.total_cost += self.treatment_costs[treatment]
        
        # Simulate treatment effect
        if treatment == "chemotherapy":
            # Reduces tumor but increases side effects
            tumor_reduction = min(0.3, self.tumor_size * 0.4)
            self.tumor_size = max(0, self.tumor_size - tumor_reduction)
            self.side_effects = min(10.0, self.side_effects + 2.0)
            self.current_patient.vitals["wbc"] = max(2.0, self.current_patient.vitals.get("wbc", 7) - 1.5)
        
        elif treatment == "radiation_therapy":
            # Localized reduction
            tumor_reduction = min(0.25, self.tumor_size * 0.35)
            self.tumor_size = max(0, self.tumor_size - tumor_reduction)
            self.side_effects = min(10.0, self.side_effects + 1.5)
        
        elif treatment == "immunotherapy":
            # Potent but expensive
            tumor_reduction = min(0.35, self.tumor_size * 0.45)
            self.tumor_size = max(0, self.tumor_size - tumor_reduction)
            self.side_effects = min(10.0, self.side_effects + 1.0)
        
        elif treatment == "surgery":
            # Major reduction but high cost
            if self.tumor_size > 0.3:
                self.tumor_size = max(0, self.tumor_size - 0.5)
            self.side_effects = min(10.0, self.side_effects + 3.0)
        
        elif treatment == "targeted_therapy":
            # Precision treatment
            tumor_reduction = min(0.3, self.tumor_size * 0.4)
            self.tumor_size = max(0, self.tumor_size - tumor_reduction)
            self.side_effects = min(10.0, self.side_effects + 0.8)
        
        elif treatment == "monitoring":
            # Tumor may grow if untreated
            if len(self.treatment_history) > 0:
                self.tumor_size = min(1.0, self.tumor_size + 0.05)
            self.side_effects = max(0, self.side_effects - 0.5)
        
        # Evolve patient state
        self.current_patient = self.patient_generator.evolve_patient(
            self.current_patient, 1.0
        )
        
        return transition_info
    
    def _calculate_reward_components(
        self, state: np.ndarray, action: int, info: Dict[str, Any]
    ) -> Dict[RewardComponent, float]:
        """Calculate reward components"""
        # Clinical score: tumor response
        tumor_response = 1.0 - self.tumor_size
        side_effect_penalty = self.side_effects / 10.0
        clinical_score = tumor_response * (1.0 - side_effect_penalty * 0.3)
        
        # Efficiency score: treatment sequencing
        treatment_diversity = len(set(self.treatment_history)) / max(1, len(self.treatment_history))
        efficiency_score = treatment_diversity * (1.0 - self.treatment_cycle / 15.0)
        
        # Financial score: cost-effectiveness
        cost_per_response = self.total_cost / max(0.01, 1.0 - self.tumor_size)
        financial_score = 1.0 / (1.0 + cost_per_response / 50000.0)
        
        # Patient satisfaction: quality of life
        quality_of_life = (1.0 - self.tumor_size) * (1.0 - self.side_effects / 10.0)
        patient_satisfaction = quality_of_life
        
        # Risk penalty: high side effects, tumor growth
        risk_penalty = 0.0
        if self.side_effects > 7.0:
            risk_penalty += 0.3
        if self.tumor_size > 0.8:
            risk_penalty += 0.5
        
        # Compliance penalty: inappropriate sequencing
        compliance_penalty = 0.0
        if len(self.treatment_history) > 2 and self.treatment_history[-1] == "surgery" and "surgery" in self.treatment_history[:-1]:
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
        
        # Done if tumor resolved
        if self.tumor_size < 0.1:
            return True
        
        # Done if too many cycles
        if self.treatment_cycle >= 12:
            return True
        
        # Done if side effects too severe
        if self.side_effects > 9.0:
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
                "tumor_size": self.tumor_size,
                "tumor_response": 1.0 - self.tumor_size,
                "side_effects": self.side_effects
            },
            operational_efficiency={
                "treatment_cycles": self.treatment_cycle,
                "treatment_diversity": len(set(self.treatment_history)) / max(1, len(self.treatment_history)),
                "cycles_per_response": self.treatment_cycle / max(0.01, 1.0 - self.tumor_size)
            },
            financial_metrics={
                "total_cost": self.total_cost,
                "cost_per_response": self.total_cost / max(0.01, 1.0 - self.tumor_size),
                "cost_effectiveness": (1.0 - self.tumor_size) / max(0.01, self.total_cost / 50000.0)
            },
            patient_satisfaction=(1.0 - self.tumor_size) * (1.0 - self.side_effects / 10.0),
            risk_score=p.risk_score + (0.3 if self.side_effects > 7.0 else 0.0) + (0.5 if self.tumor_size > 0.8 else 0.0),
            compliance_score=1.0 - (0.2 if len(self.treatment_history) > 2 and self.treatment_history[-1] == "surgery" and "surgery" in self.treatment_history[:-1] else 0.0),
            timestamp=self.time_step
        )

