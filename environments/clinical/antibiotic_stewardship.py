"""
Antibiotic Stewardship Environment
Optimizes antibiotic selection and duration to prevent resistance
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


class AntibioticStewardshipEnv(HealthcareRLEnvironment):
    """
    Optimizes antibiotic selection and duration
    
    State: Infection type, patient demographics, lab results, current antibiotics, resistance markers
    Action: Select antibiotic, adjust dose, stop antibiotic, extend course
    Reward: Infection resolution, resistance prevention, cost-effectiveness, safety
    """
    
    ACTIONS = [
        "broad_spectrum_antibiotic",
        "narrow_spectrum_antibiotic",
        "antifungal",
        "adjust_dose",
        "stop_antibiotic",
        "extend_course"
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
        self.infection_severity = 0.0
        self.antibiotic_history = []
        self.days_on_antibiotics = 0
        self.resistance_risk = 0.0
        self.total_cost = 0.0
        
        self.antibiotic_costs = {
            "broad_spectrum_antibiotic": 200.0,
            "narrow_spectrum_antibiotic": 100.0,
            "antifungal": 300.0,
            "adjust_dose": 50.0,
            "stop_antibiotic": 0.0,
            "extend_course": 150.0
        }
    
    def _initialize_state(self) -> np.ndarray:
        """Initialize patient and infection"""
        self.current_patient = self.patient_generator.generate_patient()
        self.infection_severity = self.np_random.uniform(0.5, 1.0)
        self.antibiotic_history = []
        self.days_on_antibiotics = 0
        self.resistance_risk = 0.0
        self.total_cost = 0.0
        
        return self._get_state_features()
    
    def _get_state_features(self) -> np.ndarray:
        """Extract current state features"""
        if self.current_patient is None:
            return np.zeros(20, dtype=np.float32)
        
        p = self.current_patient
        
        state = np.array([
            p.age / 100.0,
            1.0 if p.gender == "M" else 0.0,
            self.infection_severity,
            p.risk_score,
            p.vitals.get("temperature", 98.6) / 105.0,
            p.vitals.get("heart_rate", 72) / 150.0,
            p.lab_results.get("wbc", 7) / 20.0,
            p.lab_results.get("creatinine", 1.0) / 2.0,
            len(self.antibiotic_history) / 10.0,
            self.days_on_antibiotics / 14.0,
            self.resistance_risk,
            self.total_cost / 5000.0,
            1.0 if "broad_spectrum" in str(self.antibiotic_history[-3:]) else 0.0,
            len([h for h in self.antibiotic_history if h == "broad_spectrum_antibiotic"]) / 5.0,
            p.readmission_risk,
            p.severity.value / 4.0,
            self.current_patient.length_of_stay / 30.0,
            (self.infection_severity - 0.3) / 0.7 if self.infection_severity > 0.3 else 0.0,
            p.lab_results.get("hemoglobin", 14) / 20.0,
            p.vitals.get("oxygen_saturation", 98) / 100.0
        ], dtype=np.float32)
        
        return state
    
    def _apply_action(self, action: int) -> Dict[str, Any]:
        """Apply antibiotic stewardship action"""
        intervention = self.ACTIONS[action]
        self.antibiotic_history.append(intervention)
        
        transition_info = {
            "intervention": intervention,
            "cost": self.antibiotic_costs[intervention]
        }
        
        self.total_cost += self.antibiotic_costs[intervention]
        
        # Simulate intervention effect
        if intervention == "broad_spectrum_antibiotic":
            # Effective but increases resistance risk
            self.infection_severity = max(0, self.infection_severity - 0.3)
            self.resistance_risk = min(1.0, self.resistance_risk + 0.15)
            self.days_on_antibiotics += 1
        
        elif intervention == "narrow_spectrum_antibiotic":
            # Less resistance risk, effective if right target
            if self.infection_severity > 0.4:
                self.infection_severity = max(0, self.infection_severity - 0.25)
            else:
                self.infection_severity = max(0, self.infection_severity - 0.35)
            self.resistance_risk = min(1.0, self.resistance_risk + 0.05)
            self.days_on_antibiotics += 1
        
        elif intervention == "antifungal":
            # For fungal infections
            if self.np_random.random() < 0.3:  # 30% chance of fungal infection
                self.infection_severity = max(0, self.infection_severity - 0.4)
            self.days_on_antibiotics += 1
        
        elif intervention == "adjust_dose":
            # Optimize current antibiotic
            self.infection_severity = max(0, self.infection_severity - 0.1)
        
        elif intervention == "stop_antibiotic":
            # Stop if infection resolved
            if self.infection_severity < 0.2:
                transition_info["infection_resolved"] = True
            else:
                # Risk of relapse
                self.infection_severity = min(1.0, self.infection_severity + 0.1)
        
        elif intervention == "extend_course":
            # Extend if needed
            self.days_on_antibiotics += 3
            if self.infection_severity > 0.3:
                self.infection_severity = max(0, self.infection_severity - 0.2)
            else:
                self.resistance_risk = min(1.0, self.resistance_risk + 0.1)
        
        # Evolve patient state
        self.current_patient = self.patient_generator.evolve_patient(
            self.current_patient, 1.0
        )
        
        return transition_info
    
    def _calculate_reward_components(
        self, state: np.ndarray, action: int, info: Dict[str, Any]
    ) -> Dict[RewardComponent, float]:
        """Calculate reward components"""
        # Clinical score: infection resolution
        infection_resolution = 1.0 - self.infection_severity
        vital_stability = 1.0 - abs(self.current_patient.vitals.get("temperature", 98.6) - 98.6) / 10.0
        clinical_score = (infection_resolution + vital_stability) / 2.0
        
        # Efficiency score: appropriate antibiotic use
        narrow_spectrum_ratio = len([h for h in self.antibiotic_history if h == "narrow_spectrum_antibiotic"]) / max(1, len(self.antibiotic_history))
        efficiency_score = narrow_spectrum_ratio * (1.0 - self.resistance_risk)
        
        # Financial score: cost-effectiveness
        cost_per_resolution = self.total_cost / max(0.01, 1.0 - self.infection_severity)
        financial_score = 1.0 / (1.0 + cost_per_resolution / 1000.0)
        
        # Patient satisfaction: infection resolved, shorter course
        course_length_score = 1.0 - min(1.0, self.days_on_antibiotics / 14.0)
        patient_satisfaction = (infection_resolution + course_length_score) / 2.0
        
        # Risk penalty: resistance development, overuse
        risk_penalty = self.resistance_risk
        if self.days_on_antibiotics > 14:
            risk_penalty += 0.2
        if len([h for h in self.antibiotic_history if h == "broad_spectrum_antibiotic"]) > 3:
            risk_penalty += 0.3
        
        # Compliance penalty: inappropriate use
        compliance_penalty = 0.0
        if self.infection_severity < 0.2 and len(self.antibiotic_history) > 0 and self.antibiotic_history[-1] != "stop_antibiotic":
            compliance_penalty = 0.2
        if self.days_on_antibiotics > 14 and self.infection_severity < 0.1:
            compliance_penalty += 0.3
        
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
        
        # Done if infection resolved
        if self.infection_severity < 0.1:
            return True
        
        # Done if too many days on antibiotics
        if self.days_on_antibiotics >= 21:
            return True
        
        # Done if resistance risk too high
        if self.resistance_risk > 0.8:
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
                "infection_severity": self.infection_severity,
                "infection_resolution": 1.0 - self.infection_severity,
                "vital_stability": 1.0 - abs(p.vitals.get("temperature", 98.6) - 98.6) / 10.0
            },
            operational_efficiency={
                "days_on_antibiotics": self.days_on_antibiotics,
                "narrow_spectrum_ratio": len([h for h in self.antibiotic_history if h == "narrow_spectrum_antibiotic"]) / max(1, len(self.antibiotic_history)),
                "interventions_count": len(self.antibiotic_history)
            },
            financial_metrics={
                "total_cost": self.total_cost,
                "cost_per_resolution": self.total_cost / max(0.01, 1.0 - self.infection_severity),
                "cost_effectiveness": (1.0 - self.infection_severity) / max(0.01, self.total_cost / 1000.0)
            },
            patient_satisfaction=1.0 - self.infection_severity,
            risk_score=p.risk_score + self.resistance_risk,
            compliance_score=1.0 - (0.2 if self.infection_severity < 0.2 and len(self.antibiotic_history) > 0 and self.antibiotic_history[-1] != "stop_antibiotic" else 0.0),
            timestamp=self.time_step
        )

