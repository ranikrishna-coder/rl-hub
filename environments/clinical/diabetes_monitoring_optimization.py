"""
Diabetes Monitoring Optimization Environment
Optimizes diabetes monitoring and management
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


class DiabetesMonitoringOptimizationEnv(HealthcareRLEnvironment):
    """
    Optimizes diabetes monitoring and management
    
    State: Glucose levels, HbA1c, patient demographics, medication history, complications
    Action: Insulin adjustment, glucose check, diet counseling, exercise plan, monitoring, discharge
    Reward: Glucose control, complication prevention, patient adherence, cost-effectiveness
    """
    
    ACTIONS = [
        "insulin_adjustment",
        "glucose_check",
        "diet_counseling",
        "exercise_plan",
        "monitoring",
        "discharge"
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(18,), dtype=np.float32
        )
        
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        
        self.current_patient = None
        self.glucose_level = 0.0
        self.hba1c = 0.0
        self.intervention_history = []
        self.total_cost = 0.0
        self.complication_risk = 0.0
        
        self.action_costs = {
            "insulin_adjustment": 150.0,
            "glucose_check": 50.0,
            "diet_counseling": 200.0,
            "exercise_plan": 150.0,
            "monitoring": 100.0,
            "discharge": 0.0
        }
    
    def _initialize_state(self) -> np.ndarray:
        """Initialize diabetes scenario"""
        self.current_patient = self.patient_generator.generate_patient()
        self.glucose_level = self.np_random.uniform(80.0, 300.0)
        self.hba1c = self.np_random.uniform(5.0, 12.0)
        self.intervention_history = []
        self.total_cost = 0.0
        self.complication_risk = max(0.0, (self.hba1c - 7.0) / 5.0)
        
        return self._get_state_features()
    
    def _get_state_features(self) -> np.ndarray:
        """Extract current state features"""
        if self.current_patient is None:
            return np.zeros(18, dtype=np.float32)
        
        p = self.current_patient
        
        # Normalize glucose (target: 70-140)
        glucose_normalized = 1.0 - abs(self.glucose_level - 100.0) / 200.0
        
        state = np.array([
            p.age / 100.0,
            1.0 if p.gender == "M" else 0.0,
            self.glucose_level / 300.0,
            self.hba1c / 12.0,
            glucose_normalized,
            self.complication_risk,
            p.risk_score,
            len(self.intervention_history) / 10.0,
            self.total_cost / 5000.0,
            len([h for h in self.intervention_history if h == "insulin_adjustment"]) / 5.0,
            p.readmission_risk,
            p.severity.value / 4.0,
            self.current_patient.length_of_stay / 30.0,
            p.lab_results.get("creatinine", 1.0) / 2.0,
            p.vitals.get("bp_systolic", 120) / 200.0,
            p.vitals.get("heart_rate", 72) / 150.0,
            (self.hba1c - 7.0) / 5.0 if self.hba1c > 7.0 else 0.0,
            p.risk_score
        ], dtype=np.float32)
        
        return state
    
    def _apply_action(self, action: int) -> Dict[str, Any]:
        """Apply diabetes management action"""
        intervention = self.ACTIONS[action]
        self.intervention_history.append(intervention)
        
        transition_info = {
            "intervention": intervention,
            "cost": self.action_costs[intervention]
        }
        
        self.total_cost += self.action_costs[intervention]
        
        # Simulate intervention effect
        if intervention == "insulin_adjustment":
            # Adjust glucose toward target
            if self.glucose_level > 140:
                self.glucose_level = max(70, self.glucose_level - 30)
            elif self.glucose_level < 70:
                self.glucose_level = min(140, self.glucose_level + 20)
            self.hba1c = max(5.0, self.hba1c - 0.2)
            self.complication_risk = max(0.0, self.complication_risk - 0.1)
        
        elif intervention == "glucose_check":
            # Monitor only
            pass
        
        elif intervention == "diet_counseling":
            # Long-term glucose control
            self.glucose_level = max(70, min(300, self.glucose_level - 10))
            self.hba1c = max(5.0, self.hba1c - 0.1)
            self.complication_risk = max(0.0, self.complication_risk - 0.05)
        
        elif intervention == "exercise_plan":
            # Improves insulin sensitivity
            self.glucose_level = max(70, min(300, self.glucose_level - 15))
            self.hba1c = max(5.0, self.hba1c - 0.15)
            self.complication_risk = max(0.0, self.complication_risk - 0.08)
        
        elif intervention == "monitoring":
            # Track progress
            pass
        
        elif intervention == "discharge":
            transition_info["discharged"] = True
        
        # Update complication risk based on HbA1c
        self.complication_risk = max(0.0, (self.hba1c - 7.0) / 5.0)
        
        # Evolve patient state
        self.current_patient = self.patient_generator.evolve_patient(
            self.current_patient, 1.0
        )
        
        return transition_info
    
    def _calculate_reward_components(
        self, state: np.ndarray, action: int, info: Dict[str, Any]
    ) -> Dict[RewardComponent, float]:
        """Calculate reward components"""
        # Clinical score: glucose control
        glucose_control = 1.0 - abs(self.glucose_level - 100.0) / 200.0
        hba1c_control = 1.0 - max(0, (self.hba1c - 7.0) / 5.0)
        clinical_score = (glucose_control + hba1c_control) / 2.0
        
        # Efficiency score: intervention effectiveness
        glucose_improvement = abs(self.glucose_level - 100.0) / 200.0
        efficiency_score = 1.0 - min(1.0, len(self.intervention_history) / 10.0) * (1.0 - glucose_improvement)
        
        # Financial score: cost-effectiveness
        cost_per_control = self.total_cost / max(0.01, glucose_control)
        financial_score = 1.0 / (1.0 + cost_per_control / 2000.0)
        
        # Patient satisfaction: better control, fewer complications
        patient_satisfaction = glucose_control * (1.0 - self.complication_risk)
        
        # Risk penalty: poor glucose control, complications
        risk_penalty = 0.0
        if self.glucose_level > 250 or self.glucose_level < 60:
            risk_penalty += 0.4
        if self.complication_risk > 0.5:
            risk_penalty += 0.3
        
        # Compliance penalty: inappropriate interventions
        compliance_penalty = 0.0
        if len(self.intervention_history) > 5 and glucose_control > 0.9:
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
        
        if 70 <= self.glucose_level <= 140 and self.hba1c <= 7.5:
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
        glucose_control = 1.0 - abs(self.glucose_level - 100.0) / 200.0
        
        return KPIMetrics(
            clinical_outcomes={
                "glucose_level": self.glucose_level,
                "hba1c": self.hba1c,
                "glucose_control": glucose_control,
                "complication_risk": self.complication_risk
            },
            operational_efficiency={
                "interventions_count": len(self.intervention_history),
                "glucose_checks": len([h for h in self.intervention_history if h == "glucose_check"]),
                "control_efficiency": glucose_control / max(1, len(self.intervention_history))
            },
            financial_metrics={
                "total_cost": self.total_cost,
                "cost_per_control": self.total_cost / max(0.01, glucose_control),
                "cost_effectiveness": glucose_control / max(0.01, self.total_cost / 2000.0)
            },
            patient_satisfaction=glucose_control * (1.0 - self.complication_risk),
            risk_score=p.risk_score + (0.4 if self.glucose_level > 250 or self.glucose_level < 60 else 0.0),
            compliance_score=1.0 - (0.2 if len(self.intervention_history) > 5 and glucose_control > 0.9 else 0.0),
            timestamp=self.time_step
        )

