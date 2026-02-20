"""Radiologist Task Assignment Environment - Assigns radiology tasks (Philips, GE)"""
import numpy as np
from gymnasium import spaces
from typing import Dict, Any, Optional
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from base_environment import HealthcareRLEnvironment, RewardComponent, KPIMetrics
from simulator.patient_generator import PatientGenerator

class RadiologistTaskAssignmentEnv(HealthcareRLEnvironment):
    ACTIONS = ["assign_senior", "assign_junior", "assign_ai_review", "batch_assign", "defer", "prioritize"]
    def __init__(self, config: Optional[Dict[str, Any]] = None, **kwargs):
        super().__init__(config, **kwargs)
        self.observation_space = spaces.Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.patient_generator = PatientGenerator(seed=self.np_random.integers(0, 10000))
        self.task_queue = []
        self.assigned_tasks = []
        self.radiologist_workload = {"senior": 0.0, "junior": 0.0, "ai": 0.0}
    def _initialize_state(self) -> np.ndarray:
        self.task_queue = [{"patient": self.patient_generator.generate_patient(), "complexity": self.np_random.uniform(0, 1), "urgency": self.np_random.uniform(0, 1), "wait_time": 0.0} for _ in range(15)]
        self.assigned_tasks = []
        self.radiologist_workload = {"senior": 0.0, "junior": 0.0, "ai": 0.0}
        return self._get_state_features()
    def _get_state_features(self) -> np.ndarray:
        state = np.zeros(17, dtype=np.float32)
        state[0] = len(self.task_queue) / 20.0
        state[1] = len(self.assigned_tasks) / 20.0
        if self.task_queue:
            state[2] = self.task_queue[0]["complexity"]
            state[3] = self.task_queue[0]["urgency"]
            state[4] = self.task_queue[0]["wait_time"] / 7.0
        state[5] = self.radiologist_workload["senior"]
        state[6] = self.radiologist_workload["junior"]
        state[7] = self.radiologist_workload["ai"]
        state[8] = np.mean([t["urgency"] for t in self.task_queue[:5]]) if self.task_queue else 0.0
        return state
    def _apply_action(self, action: int) -> Dict[str, Any]:
        action_name = self.ACTIONS[action]
        if self.task_queue:
            task = self.task_queue.pop(0)
            if action_name == "assign_senior":
                self.assigned_tasks.append({**task, "assignee": "senior"})
                self.radiologist_workload["senior"] = min(1.0, self.radiologist_workload["senior"] + 0.1)
            elif action_name == "assign_junior":
                self.assigned_tasks.append({**task, "assignee": "junior"})
                self.radiologist_workload["junior"] = min(1.0, self.radiologist_workload["junior"] + 0.1)
            elif action_name == "assign_ai_review":
                self.assigned_tasks.append({**task, "assignee": "ai"})
                self.radiologist_workload["ai"] = min(1.0, self.radiologist_workload["ai"] + 0.1)
            elif action_name == "batch_assign":
                similar_tasks = [t for t in self.task_queue if abs(t["complexity"] - task["complexity"]) < 0.2][:2]
                for t in similar_tasks:
                    self.assigned_tasks.append({**t, "assignee": "junior"})
                    if t in self.task_queue:
                        self.task_queue.remove(t)
                    self.radiologist_workload["junior"] = min(1.0, self.radiologist_workload["junior"] + 0.1)
            elif action_name == "defer":
                self.task_queue.append(task)
                task["wait_time"] += 1.0
        for task in self.task_queue:
            task["wait_time"] += 0.5
        return {"action": action_name}
    def _calculate_reward_components(self, state: np.ndarray, action: int, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        clinical_score = 1.0 - len([t for t in self.task_queue if t["urgency"] > 0.8]) / 15.0
        efficiency_score = np.mean(list(self.radiologist_workload.values()))
        financial_score = len(self.assigned_tasks) / 20.0
        risk_penalty = len([t for t in self.task_queue if t["urgency"] > 0.9 and t["wait_time"] > 2.0]) * 0.2
        compliance_penalty = 0.2 if self.task_queue and self.task_queue[0]["complexity"] > 0.8 and self.ACTIONS[action] == "assign_junior" else 0.0
        return {
            RewardComponent.CLINICAL: clinical_score,
            RewardComponent.EFFICIENCY: efficiency_score,
            RewardComponent.FINANCIAL: financial_score,
            RewardComponent.PATIENT_SATISFACTION: 1.0 - len(self.task_queue) / 20.0,
            RewardComponent.RISK_PENALTY: risk_penalty,
            RewardComponent.COMPLIANCE_PENALTY: compliance_penalty
        }
    def _is_done(self) -> bool:
        return self.time_step >= 40 or len(self.task_queue) == 0
    def _get_kpis(self) -> KPIMetrics:
        return KPIMetrics(
            clinical_outcomes={"urgent_tasks_waiting": len([t for t in self.task_queue if t["urgency"] > 0.8])},
            operational_efficiency={"queue_length": len(self.task_queue), "workload_balance": 1.0 - np.std(list(self.radiologist_workload.values()))},
            financial_metrics={"tasks_assigned": len(self.assigned_tasks)},
            patient_satisfaction=1.0 - len(self.task_queue) / 20.0,
            risk_score=len([t for t in self.task_queue if t["urgency"] > 0.9 and t["wait_time"] > 2.0]) / 15.0,
            compliance_score=1.0 - (0.2 if self.task_queue and self.task_queue[0]["complexity"] > 0.8 else 0.0),
            timestamp=self.time_step
        )

