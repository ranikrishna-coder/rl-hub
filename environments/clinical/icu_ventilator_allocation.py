"""
ICU Ventilator Allocation Environment
Optimizes ventilator allocation for critical patients
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


class ICUVentilatorAllocationEnv(HealthcareRLEnvironment):
    """
    Optimizes ventilator allocation for critical patients
    
    State: Patient acuity, ventilator availability, respiratory status, waiting queue
    Action: Allocate ventilator, wean, extubate, defer, transfer
    Reward: Patient outcomes, resource utilization, mortality reduction
    """
    
    ACTIONS = [
        "allocate_ventilator",
        "wean_ventilator",
        "extubate",
        "defer_allocation",
        "transfer_patient",
        "monitor"
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        config = config or {}
        
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(21,), dtype=np.float32
        )
        
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.hospital_simulator = HospitalSimulator(seed=self.np_random.integers(0, 10000))
        self.simulator = self.hospital_simulator
        
        self.ventilator_capacity = config.get("ventilator_capacity", 10)
        self.available_ventilators = self.ventilator_capacity
        self.ventilated_patients = []
        self.waiting_queue = []
        self.current_patient = None
        self.total_cost = 0.0
        
        self.action_costs = {
            "allocate_ventilator": 500.0,
            "wean_ventilator": 200.0,
            "extubate": 100.0,
            "defer_allocation": 0.0,
            "transfer_patient": 1000.0,
            "monitor": 50.0
        }
    
    def _initialize_state(self) -> np.ndarray:
        """Initialize ICU ventilator scenario"""
        self.available_ventilators = self.ventilator_capacity
        self.ventilated_patients = []
        self.waiting_queue = [self.patient_generator.generate_patient() for _ in range(3)]
        self.current_patient = self.waiting_queue[0] if self.waiting_queue else None
        self.total_cost = 0.0
        
        return self._get_state_features()
    
    def _get_state_features(self) -> np.ndarray:
        """Extract current state features"""
        if self.current_patient is None:
            return np.zeros(21, dtype=np.float32)
        
        p = self.current_patient
        
        state = np.array([
            self.available_ventilators / self.ventilator_capacity,
            len(self.ventilated_patients) / self.ventilator_capacity,
            len(self.waiting_queue) / 10.0,
            p.risk_score,
            p.vitals.get("respiratory_rate", 16) / 40.0,
            p.vitals.get("oxygen_saturation", 98) / 100.0,
            p.vitals.get("bp_systolic", 120) / 200.0,
            p.vitals.get("heart_rate", 72) / 150.0,
            p.severity.value / 4.0,
            p.age / 100.0,
            1.0 if p.gender == "M" else 0.0,
            p.lab_results.get("lactate", 1.0) / 5.0,
            p.lab_results.get("creatinine", 1.0) / 2.0,
            self.total_cost / 10000.0,
            p.readmission_risk,
            self.current_patient.length_of_stay / 30.0,
            (100.0 - p.vitals.get("oxygen_saturation", 98)) / 100.0,
            p.vitals.get("temperature", 98.6) / 105.0,
            len([vp for vp in self.ventilated_patients if vp.risk_score > 0.7]) / 5.0,
            self.hospital_simulator.get_state().occupancy_rate,
            p.vitals.get("pain_score", 0) / 10.0
        ], dtype=np.float32)
        
        return state
    
    def _apply_action(self, action: int) -> Dict[str, Any]:
        """Apply ventilator allocation action"""
        action_name = self.ACTIONS[action]
        transition_info = {"action": action_name, "cost": self.action_costs[action_name]}
        
        self.total_cost += self.action_costs[action_name]
        
        if action_name == "allocate_ventilator" and self.available_ventilators > 0 and self.current_patient:
            self.available_ventilators -= 1
            self.ventilated_patients.append(self.current_patient)
            if self.current_patient in self.waiting_queue:
                self.waiting_queue.remove(self.current_patient)
            # Improve respiratory status
            self.current_patient.vitals["oxygen_saturation"] = min(100, 
                self.current_patient.vitals.get("oxygen_saturation", 85) + 5)
            self.current_patient.risk_score = max(0, self.current_patient.risk_score - 0.1)
        
        elif action_name == "wean_ventilator" and self.ventilated_patients:
            # Gradually reduce support
            patient = self.ventilated_patients[0]
            patient.vitals["oxygen_saturation"] = max(90, 
                patient.vitals.get("oxygen_saturation", 95) - 2)
            if patient.vitals.get("oxygen_saturation", 95) >= 95:
                self.ventilated_patients.remove(patient)
                self.available_ventilators += 1
        
        elif action_name == "extubate" and self.ventilated_patients:
            patient = self.ventilated_patients[0]
            if patient.vitals.get("oxygen_saturation", 90) >= 92:
                self.ventilated_patients.remove(patient)
                self.available_ventilators += 1
                transition_info["extubated"] = True
        
        elif action_name == "defer_allocation":
            # Patient waits, condition may worsen
            if self.current_patient:
                self.current_patient.vitals["oxygen_saturation"] = max(70,
                    self.current_patient.vitals.get("oxygen_saturation", 85) - 2)
                self.current_patient.risk_score = min(1.0, self.current_patient.risk_score + 0.05)
        
        elif action_name == "transfer_patient" and self.current_patient:
            if self.current_patient in self.waiting_queue:
                self.waiting_queue.remove(self.current_patient)
            transition_info["transferred"] = True
        
        # Update patient states
        for patient in self.ventilated_patients:
            patient = self.patient_generator.evolve_patient(patient, 1.0)
        
        if self.waiting_queue:
            self.current_patient = self.waiting_queue[0]
        else:
            self.current_patient = None
        
        return transition_info
    
    def _calculate_reward_components(
        self, state: np.ndarray, action: int, info: Dict[str, Any]
    ) -> Dict[RewardComponent, float]:
        """Calculate reward components"""
        if self.current_patient is None:
            return {
                RewardComponent.CLINICAL: 0.0,
                RewardComponent.EFFICIENCY: 0.0,
                RewardComponent.FINANCIAL: 0.0,
                RewardComponent.PATIENT_SATISFACTION: 0.0,
                RewardComponent.RISK_PENALTY: 0.0,
                RewardComponent.COMPLIANCE_PENALTY: 0.0
            }
        
        p = self.current_patient
        
        # Clinical score: patient outcomes
        oxygen_score = p.vitals.get("oxygen_saturation", 85) / 100.0
        risk_reduction = 1.0 - p.risk_score
        clinical_score = (oxygen_score + risk_reduction) / 2.0
        
        # Efficiency score: resource utilization
        utilization = (self.ventilator_capacity - self.available_ventilators) / self.ventilator_capacity
        queue_length_penalty = len(self.waiting_queue) / 10.0
        efficiency_score = utilization * (1.0 - queue_length_penalty)
        
        # Financial score: cost-effectiveness
        cost_per_patient = self.total_cost / max(1, len(self.ventilated_patients) + len(self.waiting_queue))
        financial_score = 1.0 / (1.0 + cost_per_patient / 1000.0)
        
        # Patient satisfaction: reduced wait time
        patient_satisfaction = 1.0 - min(1.0, len(self.waiting_queue) / 10.0)
        
        # Risk penalty: delayed care, poor outcomes
        risk_penalty = 0.0
        if len(self.waiting_queue) > 3:
            risk_penalty += 0.3
        if p.vitals.get("oxygen_saturation", 85) < 85:
            risk_penalty += 0.5
        
        # Compliance penalty: inappropriate allocation
        compliance_penalty = 0.0
        if self.available_ventilators > 0 and p.vitals.get("oxygen_saturation", 85) < 88 and \
           info.get("action") != "allocate_ventilator":
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
        return self.time_step >= 100 or (len(self.waiting_queue) == 0 and len(self.ventilated_patients) == 0)
    
    def _get_kpis(self) -> KPIMetrics:
        """Calculate KPI metrics"""
        if not self.ventilated_patients and not self.waiting_queue:
            return KPIMetrics(
                clinical_outcomes={},
                operational_efficiency={},
                financial_metrics={},
                patient_satisfaction=0.0,
                risk_score=0.0,
                compliance_score=0.0,
                timestamp=self.time_step
            )
        
        avg_oxygen = np.mean([p.vitals.get("oxygen_saturation", 85) for p in self.ventilated_patients + self.waiting_queue]) if (self.ventilated_patients or self.waiting_queue) else 0.0
        
        return KPIMetrics(
            clinical_outcomes={
                "ventilator_utilization": (self.ventilator_capacity - self.available_ventilators) / self.ventilator_capacity,
                "avg_oxygen_saturation": avg_oxygen,
                "mortality_risk": np.mean([p.risk_score for p in self.ventilated_patients + self.waiting_queue]) if (self.ventilated_patients or self.waiting_queue) else 0.0
            },
            operational_efficiency={
                "queue_length": len(self.waiting_queue),
                "ventilated_count": len(self.ventilated_patients),
                "utilization_rate": (self.ventilator_capacity - self.available_ventilators) / self.ventilator_capacity
            },
            financial_metrics={
                "total_cost": self.total_cost,
                "cost_per_patient": self.total_cost / max(1, len(self.ventilated_patients) + len(self.waiting_queue)),
                "cost_effectiveness": len(self.ventilated_patients) / max(0.01, self.total_cost / 1000.0)
            },
            patient_satisfaction=1.0 - min(1.0, len(self.waiting_queue) / 10.0),
            risk_score=np.mean([p.risk_score for p in self.waiting_queue]) if self.waiting_queue else 0.0,
            compliance_score=1.0 - (0.3 if self.available_ventilators > 0 and self.waiting_queue and 
                                     self.waiting_queue[0].vitals.get("oxygen_saturation", 85) < 88 else 0.0),
            timestamp=self.time_step
        )

