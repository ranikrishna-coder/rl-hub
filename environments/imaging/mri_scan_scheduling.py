"""
MRI Scan Scheduling Environment
Optimizes MRI scan scheduling and resource allocation
System: Philips, GE
"""

import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator


class MRIScanSchedulingEnv(HealthcareRLEnvironment):
    """
    Optimizes MRI scan scheduling
    
    State: Scan queue, urgency, patient demographics, scanner availability, appointment slots
    Action: Schedule immediate, schedule routine, reschedule, cancel, prioritize
    Reward: Wait time reduction, scanner utilization, patient satisfaction, cost-effectiveness
    """
    
    ACTIONS = [
        "schedule_immediate",
        "schedule_routine",
        "reschedule",
        "cancel",
        "prioritize",
        "batch_schedule"
    ]
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        config = config or {}
        
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(18,), dtype=np.float32
        )
        
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        
        self.scanner_capacity = config.get("scanner_capacity", 8)  # Slots per day
        self.scan_queue = []
        self.scheduled_scans = []
        self.scanner_utilization = 0.0
        self.total_wait_time = 0.0
        self.total_revenue = 0.0
        
        self.scan_costs = {
            "schedule_immediate": 1500.0,
            "schedule_routine": 1200.0,
            "reschedule": 100.0,
            "cancel": 0.0,
            "prioritize": 1500.0,
            "batch_schedule": 1000.0
        }
    
    def _initialize_state(self) -> np.ndarray:
        """Initialize MRI scheduling scenario"""
        self.scan_queue = [
            {
                "patient": self.patient_generator.generate_patient(),
                "urgency": self.np_random.uniform(0.3, 1.0),
                "scan_type": self.np_random.choice(["brain", "spine", "joint", "abdomen"]),
                "wait_time": 0.0
            }
            for _ in range(12)
        ]
        self.scheduled_scans = []
        self.scanner_utilization = 0.0
        self.total_wait_time = 0.0
        self.total_revenue = 0.0
        
        return self._get_state_features()
    
    def _get_state_features(self) -> np.ndarray:
        """Extract current state features"""
        state = np.zeros(18, dtype=np.float32)
        
        if self.scan_queue:
            state[0] = len(self.scan_queue) / 20.0
            state[1] = np.mean([s["urgency"] for s in self.scan_queue[:5]]) if self.scan_queue else 0.0
            state[2] = np.mean([s["wait_time"] for s in self.scan_queue]) / 7.0 if self.scan_queue else 0.0
            state[3] = self.scan_queue[0]["urgency"] if self.scan_queue else 0.0
            state[4] = self.scan_queue[0]["wait_time"] / 7.0 if self.scan_queue else 0.0
        
        state[5] = len(self.scheduled_scans) / self.scanner_capacity
        state[6] = self.scanner_utilization
        state[7] = self.total_wait_time / 100.0
        state[8] = self.total_revenue / 20000.0
        state[9] = (self.scanner_capacity - len(self.scheduled_scans)) / self.scanner_capacity
        state[10] = len([s for s in self.scan_queue if s["urgency"] > 0.7]) / 10.0
        state[11] = len([s for s in self.scheduled_scans]) / self.scanner_capacity
        
        return state
    
    def _apply_action(self, action: int) -> Dict[str, Any]:
        """Apply scheduling action"""
        action_name = self.ACTIONS[action]
        transition_info = {"action": action_name}
        
        if not self.scan_queue:
            return transition_info
        
        current_scan = self.scan_queue[0]
        
        if action_name == "schedule_immediate" and len(self.scheduled_scans) < self.scanner_capacity:
            self.scheduled_scans.append(current_scan)
            self.scan_queue.pop(0)
            self.scanner_utilization = len(self.scheduled_scans) / self.scanner_capacity
            self.total_revenue += self.scan_costs["schedule_immediate"]
            transition_info["scheduled"] = True
        
        elif action_name == "schedule_routine" and len(self.scheduled_scans) < self.scanner_capacity:
            self.scheduled_scans.append(current_scan)
            self.scan_queue.pop(0)
            self.scanner_utilization = len(self.scheduled_scans) / self.scanner_capacity
            self.total_revenue += self.scan_costs["schedule_routine"]
            transition_info["scheduled"] = True
        
        elif action_name == "reschedule":
            # Move to end of queue
            self.scan_queue.append(self.scan_queue.pop(0))
            current_scan["wait_time"] += 1.0
            self.total_wait_time += 1.0
        
        elif action_name == "cancel":
            self.scan_queue.pop(0)
            transition_info["cancelled"] = True
        
        elif action_name == "prioritize":
            # Move urgent scans to front
            urgent_scans = [s for s in self.scan_queue if s["urgency"] > 0.7]
            if urgent_scans and current_scan["urgency"] < 0.7:
                self.scan_queue.remove(current_scan)
                self.scan_queue.insert(0, current_scan)
        
        elif action_name == "batch_schedule" and len(self.scheduled_scans) < self.scanner_capacity - 1:
            # Schedule multiple similar scans
            similar_scans = [s for s in self.scan_queue if s["scan_type"] == current_scan["scan_type"]][:2]
            for scan in similar_scans:
                if len(self.scheduled_scans) < self.scanner_capacity:
                    self.scheduled_scans.append(scan)
                    if scan in self.scan_queue:
                        self.scan_queue.remove(scan)
                    self.total_revenue += self.scan_costs["batch_schedule"]
            self.scanner_utilization = len(self.scheduled_scans) / self.scanner_capacity
        
        # Update wait times
        for scan in self.scan_queue:
            scan["wait_time"] += 0.5
            self.total_wait_time += 0.5
        
        return transition_info
    
    def _calculate_reward_components(
        self, state: np.ndarray, action: int, info: Dict[str, Any]
    ) -> Dict[RewardComponent, float]:
        """Calculate reward components"""
        # Clinical score: urgent scans scheduled
        urgent_scheduled = len([s for s in self.scheduled_scans if s.get("urgency", 0) > 0.7])
        clinical_score = urgent_scheduled / max(1, len([s for s in self.scan_queue + self.scheduled_scans if s.get("urgency", 0) > 0.7]))
        
        # Efficiency score: scanner utilization and wait time
        utilization_score = self.scanner_utilization
        wait_time_penalty = min(1.0, np.mean([s["wait_time"] for s in self.scan_queue]) / 7.0) if self.scan_queue else 0.0
        efficiency_score = utilization_score * (1.0 - wait_time_penalty)
        
        # Financial score: revenue and utilization
        revenue_score = self.total_revenue / 20000.0
        financial_score = (revenue_score + utilization_score) / 2.0
        
        # Patient satisfaction: reduced wait time
        avg_wait = np.mean([s["wait_time"] for s in self.scan_queue]) if self.scan_queue else 0.0
        patient_satisfaction = 1.0 - min(1.0, avg_wait / 7.0)
        
        # Risk penalty: long wait times for urgent scans
        risk_penalty = 0.0
        urgent_waiting = [s for s in self.scan_queue if s.get("urgency", 0) > 0.7 and s["wait_time"] > 2.0]
        if urgent_waiting:
            risk_penalty = len(urgent_waiting) / 10.0
        
        # Compliance penalty: poor scheduling
        compliance_penalty = 0.0
        if self.scanner_utilization < 0.5 and len(self.scan_queue) > 5:
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
        return self.time_step >= 50 or (len(self.scan_queue) == 0 and len(self.scheduled_scans) == 0)
    
    def _get_kpis(self) -> KPIMetrics:
        """Calculate KPI metrics"""
        avg_wait = np.mean([s["wait_time"] for s in self.scan_queue]) if self.scan_queue else 0.0
        
        return KPIMetrics(
            clinical_outcomes={
                "urgent_scans_scheduled": len([s for s in self.scheduled_scans if s.get("urgency", 0) > 0.7]),
                "avg_wait_time": avg_wait,
                "scanner_utilization": self.scanner_utilization
            },
            operational_efficiency={
                "queue_length": len(self.scan_queue),
                "scheduled_count": len(self.scheduled_scans),
                "utilization_rate": self.scanner_utilization
            },
            financial_metrics={
                "total_revenue": self.total_revenue,
                "revenue_per_scan": self.total_revenue / max(1, len(self.scheduled_scans)),
                "cost_effectiveness": self.scanner_utilization * (self.total_revenue / 20000.0)
            },
            patient_satisfaction=1.0 - min(1.0, avg_wait / 7.0),
            risk_score=len([s for s in self.scan_queue if s.get("urgency", 0) > 0.7 and s["wait_time"] > 2.0]) / 10.0,
            compliance_score=1.0 - (0.2 if self.scanner_utilization < 0.5 and len(self.scan_queue) > 5 else 0.0),
            timestamp=self.time_step
        )

