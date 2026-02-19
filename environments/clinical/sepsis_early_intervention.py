"""
Sepsis Early Intervention Environment
Detects and intervenes early in sepsis cases
System: Epic, Cerner
"""

import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator, ConditionSeverity, PatientStatus


class SepsisEarlyInterventionEnv(HealthcareRLEnvironment):
    """
    Early detection and intervention for sepsis
    
    State: Vital signs, lab results, SOFA score components, time since admission
    Action: No action, antibiotics, fluids, vasopressors, ICU transfer
    Reward: Early intervention bonus, mortality reduction, cost efficiency
    """
    
    INTERVENTIONS = ["no_action", "antibiotics", "fluids", "vasopressors", "icu_transfer"]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        
        # State: 18 features (vitals, labs, SOFA components, time)
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(18,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(len(self.INTERVENTIONS))
        
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.current_patient = None
        self.sepsis_probability = 0.0
        self.sofa_score = 0.0
        self.interventions_applied = []
        self.time_since_admission = 0.0
        self.mortality_risk = 0.0
    
    def _initialize_state(self) -> np.ndarray:
        """Initialize sepsis scenario"""
        # Generate patient with potential sepsis
        self.current_patient = self.patient_generator.generate_patient(
            condition_type="sepsis",
            severity=self.np_random.choice([
                ConditionSeverity.MODERATE,
                ConditionSeverity.SEVERE,
                ConditionSeverity.CRITICAL
            ], p=[0.3, 0.4, 0.3])
        )
        
        self.sepsis_probability = self.np_random.uniform(0.3, 0.9)
        self.sofa_score = self._calculate_sofa_score()
        self.interventions_applied = []
        self.time_since_admission = 0.0
        self.mortality_risk = self._calculate_mortality_risk()
        
        return self._get_state_features()
    
    def _calculate_sofa_score(self) -> float:
        """Calculate SOFA (Sepsis-related Organ Failure Assessment) score"""
        if self.current_patient is None:
            return 0.0
        
        p = self.current_patient
        score = 0.0
        
        # Respiratory component
        if p.vitals.get("oxygen_saturation", 98) < 90:
            score += 3.0
        elif p.vitals.get("oxygen_saturation", 98) < 95:
            score += 2.0
        
        # Cardiovascular component
        if p.vitals.get("heart_rate", 72) > 120:
            score += 2.0
        if p.vitals.get("bp_systolic", 120) < 90:
            score += 3.0
        
        # Coagulation
        if p.lab_results.get("platelets", 250) < 100:
            score += 2.0
        
        # Liver
        if p.lab_results.get("lactate", 1.0) > 4.0:
            score += 3.0
        
        # Renal
        if p.lab_results.get("creatinine", 1.0) > 2.0:
            score += 2.0
        
        return min(24.0, score)
    
    def _calculate_mortality_risk(self) -> float:
        """Calculate mortality risk based on SOFA and time"""
        base_risk = self.sofa_score / 24.0
        time_penalty = min(0.3, self.time_since_admission / 10.0)  # Delayed intervention
        return min(1.0, base_risk + time_penalty)
    
    def _get_state_features(self) -> np.ndarray:
        """Extract state features"""
        if self.current_patient is None:
            return np.zeros(18, dtype=np.float32)
        
        p = self.current_patient
        
        return np.array([
            p.vitals.get("temperature", 98.6) / 105.0,
            p.vitals.get("heart_rate", 72) / 150.0,
            p.vitals.get("respiratory_rate", 16) / 30.0,
            p.vitals.get("oxygen_saturation", 98) / 100.0,
            p.vitals.get("bp_systolic", 120) / 200.0,
            p.lab_results.get("wbc", 7) / 20.0,
            p.lab_results.get("lactate", 1.0) / 5.0,
            p.lab_results.get("creatinine", 1.0) / 2.0,
            p.lab_results.get("platelets", 250) / 500.0,
            p.lab_results.get("troponin", 0.04) / 1.0,
            self.sepsis_probability,
            self.sofa_score / 24.0,
            self.mortality_risk,
            self.time_since_admission / 24.0,  # Hours since admission
            len(self.interventions_applied) / 5.0,
            1.0 if "antibiotics" in self.interventions_applied else 0.0,
            1.0 if "fluids" in self.interventions_applied else 0.0,
            1.0 if "icu_transfer" in self.interventions_applied else 0.0
        ], dtype=np.float32)
    
    def _apply_action(self, action: int) -> Dict[str, Any]:
        """Apply intervention"""
        intervention = self.INTERVENTIONS[action]
        self.interventions_applied.append(intervention)
        self.time_since_admission += 1.0  # 1 hour per step
        
        transition_info = {"intervention": intervention}
        
        # Simulate intervention effects
        if intervention == "antibiotics":
            self.sepsis_probability = max(0.0, self.sepsis_probability - 0.2)
            if self.current_patient:
                self.current_patient.vitals["temperature"] = max(98.6, 
                    self.current_patient.vitals["temperature"] - 0.5)
        
        elif intervention == "fluids":
            if self.current_patient:
                self.current_patient.vitals["bp_systolic"] = min(140,
                    self.current_patient.vitals["bp_systolic"] + 10)
                self.current_patient.vitals["heart_rate"] = max(60,
                    self.current_patient.vitals["heart_rate"] - 5)
        
        elif intervention == "vasopressors":
            if self.current_patient:
                self.current_patient.vitals["bp_systolic"] = min(150,
                    self.current_patient.vitals["bp_systolic"] + 15)
        
        elif intervention == "icu_transfer":
            if self.current_patient:
                self.current_patient.status = PatientStatus.CRITICAL
        
        # Update scores
        self.sofa_score = self._calculate_sofa_score()
        self.mortality_risk = self._calculate_mortality_risk()
        
        # Evolve patient
        if self.current_patient:
            self.current_patient = self.patient_generator.evolve_patient(
                self.current_patient, 1.0
            )
        
        return transition_info
    
    def _calculate_reward_components(
        self, state: np.ndarray, action: int, info: Dict[str, Any]
    ) -> Dict[RewardComponent, float]:
        """Calculate reward components"""
        intervention = self.INTERVENTIONS[action]
        
        # Clinical score: mortality reduction, SOFA improvement
        mortality_reduction = 1.0 - self.mortality_risk
        sofa_improvement = 1.0 - (self.sofa_score / 24.0)
        clinical_score = (mortality_reduction + sofa_improvement) / 2.0
        
        # Early intervention bonus
        early_bonus = max(0, 1.0 - self.time_since_admission / 6.0) if intervention != "no_action" else 0.0
        
        # Efficiency: appropriate intervention sequence
        efficiency_score = 1.0
        if "antibiotics" not in self.interventions_applied and self.sepsis_probability > 0.5:
            efficiency_score -= 0.3  # Should have given antibiotics
        
        # Financial: cost of interventions
        intervention_costs = {
            "no_action": 0.0,
            "antibiotics": 100.0,
            "fluids": 50.0,
            "vasopressors": 200.0,
            "icu_transfer": 5000.0
        }
        total_cost = sum(intervention_costs.get(i, 0) for i in self.interventions_applied)
        financial_score = 1.0 / (1.0 + total_cost / 10000.0)
        
        # Risk penalty: high mortality risk
        risk_penalty = self.mortality_risk if self.mortality_risk > 0.5 else 0.0
        
        # Compliance: bundle compliance (antibiotics + fluids within 1 hour)
        compliance_penalty = 0.0
        if len(self.interventions_applied) >= 2:
            if "antibiotics" not in self.interventions_applied[:2]:
                compliance_penalty = 0.2
        
        return {
            RewardComponent.CLINICAL: clinical_score + early_bonus * 0.3,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - self.mortality_risk,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    
    def _is_done(self) -> bool:
        """Check if episode done"""
        if self.current_patient is None:
            return True
        
        # Done if patient recovered or died
        if self.mortality_risk < 0.1 or self.mortality_risk > 0.95:
            return True
        
        # Done after 24 hours
        if self.time_since_admission >= 24.0:
            return True
        
        return False
    
    def _get_kpis(self) -> KPIMetrics:
        """Calculate KPIs"""
        return KPIMetrics(
            clinical_outcomes={
                "sofa_score": self.sofa_score,
                "mortality_risk": self.mortality_risk,
                "sepsis_probability": self.sepsis_probability,
                "time_to_antibiotics": self.time_since_admission if "antibiotics" in self.interventions_applied else 999.0
            },
            operational_efficiency={
                "interventions_count": len(self.interventions_applied),
                "bundle_compliance": 1.0 if "antibiotics" in self.interventions_applied and "fluids" in self.interventions_applied else 0.0,
                "time_to_intervention": self.time_since_admission
            },
            financial_metrics={
                "intervention_cost": sum({
                    "antibiotics": 100.0,
                    "fluids": 50.0,
                    "vasopressors": 200.0,
                    "icu_transfer": 5000.0
                }.get(i, 0) for i in self.interventions_applied)
            },
            patient_satisfaction=1.0 - self.mortality_risk,
            risk_score=self.mortality_risk,
            compliance_score=1.0 - (0.2 if "antibiotics" not in self.interventions_applied[:2] else 0.0),
            timestamp=self.time_step
        )

