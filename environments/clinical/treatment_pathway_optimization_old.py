"""
Treatment Pathway Optimization Environment
Optimizes treatment sequences for patients with multiple conditions
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


class TreatmentPathwayOptimizationEnv(HealthcareRLEnvironment):
    """
    Optimizes treatment pathways for patients with complex conditions
    
    State: Patient demographics, conditions, vitals, lab results, current treatments
    Action: Select next treatment step (medication, procedure, test, discharge)
    Reward: Clinical improvement, efficiency, cost-effectiveness
    """
    
    TREATMENT_OPTIONS = [
        "medication_adjustment",
        "diagnostic_test",
        "specialist_consult",
        "procedure",
        "monitoring",
        "discharge"
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        
        # State space: 20 features
        # [age, gender_encoded, condition_severity, risk_score, vitals(7), labs(5), 
        #  current_treatments(3), pathway_step, days_in_pathway, readmission_risk]
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(20,), dtype=np.float32
        )
        
        # Action space: 6 treatment options
        self.action_space = spaces.Discrete(len(self.TREATMENT_OPTIONS))
        
        # Initialize simulators
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        
        # Patient tracking
        self.current_patient = None
        self.pathway_step = 0
        self.treatment_history = []
        self.total_cost = 0.0
        
        # Treatment costs
        self.treatment_costs = {
            "medication_adjustment": 50.0,
            "diagnostic_test": 200.0,
            "specialist_consult": 300.0,
            "procedure": 1000.0,
            "monitoring": 100.0,
            "discharge": 0.0
        }
    
    def _initialize_state(self) -> np.ndarray:
        """Initialize patient and pathway"""
        self.current_patient = self.patient_generator.generate_patient()
        self.pathway_step = 0
        self.treatment_history = []
        self.total_cost = 0.0
        
        return self._get_state_features()
    
    def _get_state_features(self) -> np.ndarray:
        """Extract current state features"""
        if self.current_patient is None:
            return np.zeros(20, dtype=np.float32)
        
        p = self.current_patient
        
        # Encode gender (M=1, F=0, Other=0.5)
        gender_enc = 1.0 if p.gender == "M" else (0.0 if p.gender == "F" else 0.5)
        
        # Encode severity (mild=0.25, moderate=0.5, severe=0.75, critical=1.0)
        severity_enc = {
            ConditionSeverity.MILD: 0.25,
            ConditionSeverity.MODERATE: 0.5,
            ConditionSeverity.SEVERE: 0.75,
            ConditionSeverity.CRITICAL: 1.0
        }[p.severity]
        
        # Vitals (normalized)
        vitals = [
            p.vitals.get("bp_systolic", 120) / 200.0,
            p.vitals.get("heart_rate", 72) / 150.0,
            p.vitals.get("temperature", 98.6) / 105.0,
            p.vitals.get("respiratory_rate", 16) / 30.0,
            p.vitals.get("oxygen_saturation", 98) / 100.0,
            p.vitals.get("pain_score", 0) / 10.0,
            p.vitals.get("bp_diastolic", 80) / 120.0
        ]
        
        # Lab results (normalized)
        labs = [
            p.lab_results.get("glucose", 100) / 200.0,
            p.lab_results.get("creatinine", 1.0) / 2.0,
            p.lab_results.get("hemoglobin", 14) / 20.0,
            p.lab_results.get("wbc", 7) / 20.0,
            p.lab_results.get("lactate", 1.0) / 5.0
        ]
        
        # Current treatments (one-hot encoded for top 3)
        current_treatments = [0.0, 0.0, 0.0]
        for i, med in enumerate(p.medications[:3]):
            current_treatments[i] = 1.0
        
        state = np.array([
            p.age / 100.0,
            gender_enc,
            severity_enc,
            p.risk_score,
            *vitals,
            *labs,
            *current_treatments,
            self.pathway_step / 10.0,
            self.current_patient.length_of_stay / 30.0,
            p.readmission_risk
        ], dtype=np.float32)
        
        return state
    
    def _apply_action(self, action: int) -> Dict[str, Any]:
        """Apply treatment action"""
        treatment = self.TREATMENT_OPTIONS[action]
        self.treatment_history.append(treatment)
        self.pathway_step += 1
        
        transition_info = {
            "treatment": treatment,
            "pathway_step": self.pathway_step,
            "cost": self.treatment_costs[treatment]
        }
        
        self.total_cost += self.treatment_costs[treatment]
        
        # Simulate treatment effect
        if treatment == "medication_adjustment":
            # Improve vitals
            self.current_patient.vitals["pain_score"] = max(0, self.current_patient.vitals["pain_score"] - 1.0)
            self.current_patient.risk_score = max(0, self.current_patient.risk_score - 0.05)
        
        elif treatment == "diagnostic_test":
            # Update lab results (simulate test revealing information)
            self.current_patient.lab_results["glucose"] += self.np_random.normal(0, 5)
        
        elif treatment == "specialist_consult":
            # Improve condition management
            self.current_patient.risk_score = max(0, self.current_patient.risk_score - 0.1)
        
        elif treatment == "procedure":
            # Significant improvement
            self.current_patient.risk_score = max(0, self.current_patient.risk_score - 0.2)
            self.current_patient.vitals["pain_score"] = max(0, self.current_patient.vitals["pain_score"] - 2.0)
        
        elif treatment == "monitoring":
            # No immediate effect, but tracks progress
            pass
        
        elif treatment == "discharge":
            # Patient ready for discharge
            transition_info["discharged"] = True
        
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
        
        # Clinical score: improvement in risk and vitals
        risk_improvement = max(0, 0.5 - p.risk_score)  # Lower risk is better
        vital_stability = 1.0 - abs(p.vitals.get("oxygen_saturation", 98) - 98) / 20.0
        clinical_score = (risk_improvement + vital_stability) / 2.0
        
        # Efficiency score: pathway length and resource use
        optimal_pathway_length = 5.0
        pathway_efficiency = 1.0 - min(1.0, abs(self.pathway_step - optimal_pathway_length) / 10.0)
        efficiency_score = pathway_efficiency
        
        # Financial score: cost-effectiveness
        cost_per_improvement = self.total_cost / max(0.01, risk_improvement)
        financial_score = 1.0 / (1.0 + cost_per_improvement / 1000.0)
        
        # Patient satisfaction proxy: reduced pain, shorter stay
        pain_reduction = 1.0 - p.vitals.get("pain_score", 0) / 10.0
        stay_length_score = 1.0 - min(1.0, p.length_of_stay / 30.0)
        patient_satisfaction = (pain_reduction + stay_length_score) / 2.0
        
        # Risk penalty: high risk patients
        risk_penalty = p.risk_score if p.risk_score > 0.7 else 0.0
        
        # Compliance penalty: inappropriate treatment sequence
        compliance_penalty = 0.0
        if len(self.treatment_history) > 1:
            # Penalize discharge without proper treatment
            if self.treatment_history[-1] == "discharge" and self.pathway_step < 3:
                compliance_penalty = 0.3
            # Penalize too many procedures
            if self.treatment_history.count("procedure") > 2:
                compliance_penalty += 0.2
        
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
        
        # Done if discharged or pathway too long
        if len(self.treatment_history) > 0 and self.treatment_history[-1] == "discharge":
            return True
        
        if self.pathway_step >= 15:
            return True
        
        # Done if patient critical and no improvement
        if (self.current_patient.severity == ConditionSeverity.CRITICAL and 
            self.current_patient.risk_score > 0.8 and self.pathway_step > 5):
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
                "risk_score": p.risk_score,
                "vital_stability": 1.0 - abs(p.vitals.get("oxygen_saturation", 98) - 98) / 20.0,
                "condition_severity": p.severity.value
            },
            operational_efficiency={
                "pathway_length": self.pathway_step,
                "treatment_efficiency": self.pathway_step / max(1, len(set(self.treatment_history))),
                "time_to_improvement": self.pathway_step
            },
            financial_metrics={
                "total_cost": self.total_cost,
                "cost_per_step": self.total_cost / max(1, self.pathway_step),
                "cost_effectiveness": (1.0 - p.risk_score) / max(0.01, self.total_cost / 1000.0)
            },
            patient_satisfaction=1.0 - p.vitals.get("pain_score", 0) / 10.0,
            risk_score=p.risk_score,
            compliance_score=1.0 - (self.treatment_history.count("discharge") if self.pathway_step < 3 else 0) * 0.3,
            timestamp=self.time_step
        )

