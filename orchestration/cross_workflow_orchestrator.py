"""
Cross-Workflow Orchestrator
Coordinates multiple environments for system-wide optimization
"""

from typing import Dict, List, Any, Optional
import numpy as np
from dataclasses import dataclass
from enum import Enum


class OrchestrationStrategy(Enum):
    SEQUENTIAL = "sequential"
    PARALLEL = "parallel"
    HIERARCHICAL = "hierarchical"
    COORDINATED = "coordinated"


@dataclass
class WorkflowState:
    """State of a workflow"""
    workflow_id: str
    environment_name: str
    current_state: np.ndarray
    kpis: Dict[str, Any]
    reward: float
    timestamp: float


@dataclass
class OrchestrationAction:
    """Action to take across workflows"""
    workflow_id: str
    action: Any
    priority: float
    expected_impact: Dict[str, float]


class CrossWorkflowOrchestrator:
    """
    Orchestrates multiple RL environments for cross-workflow optimization
    
    Coordinates:
    - Patient journey across multiple environments
    - Resource allocation across workflows
    - System-wide KPI optimization
    - Multi-agent coordination
    """
    
    def __init__(
        self,
        environments: Dict[str, Any],
        strategy: OrchestrationStrategy = OrchestrationStrategy.COORDINATED
    ):
        self.environments = environments
        self.strategy = strategy
        self.workflow_states: Dict[str, WorkflowState] = {}
        self.action_queue: List[OrchestrationAction] = []
        self.coordination_history: List[Dict[str, Any]] = []
    
    def register_workflow(self, workflow_id: str, environment: Any):
        """Register a workflow environment"""
        self.environments[workflow_id] = environment
        state, info = environment.reset()
        self.workflow_states[workflow_id] = WorkflowState(
            workflow_id=workflow_id,
            environment_name=environment.__class__.__name__,
            current_state=state,
            kpis=environment.get_kpis().__dict__,
            reward=0.0,
            timestamp=0.0
        )
    
    def coordinate_step(self) -> Dict[str, Any]:
        """Execute one coordination step across all workflows"""
        coordination_result = {
            "actions_taken": [],
            "total_reward": 0.0,
            "system_kpis": {},
            "workflow_states": {}
        }
        
        if self.strategy == OrchestrationStrategy.COORDINATED:
            # Prioritize actions based on system-wide impact
            prioritized_actions = self._prioritize_actions()
            
            for action in prioritized_actions:
                workflow_id = action.workflow_id
                if workflow_id in self.environments:
                    env = self.environments[workflow_id]
                    state, reward, terminated, truncated, info = env.step(action.action)
                    
                    # Update workflow state
                    self.workflow_states[workflow_id].current_state = state
                    self.workflow_states[workflow_id].kpis = env.get_kpis().__dict__
                    self.workflow_states[workflow_id].reward += reward
                    self.workflow_states[workflow_id].timestamp += 1.0
                    
                    coordination_result["actions_taken"].append({
                        "workflow_id": workflow_id,
                        "action": str(action.action),
                        "reward": reward
                    })
                    coordination_result["total_reward"] += reward
        
        # Calculate system-wide KPIs
        coordination_result["system_kpis"] = self._calculate_system_kpis()
        coordination_result["workflow_states"] = {
            wf_id: {
                "kpis": state.kpis,
                "reward": state.reward
            }
            for wf_id, state in self.workflow_states.items()
        }
        
        self.coordination_history.append(coordination_result)
        return coordination_result
    
    def _prioritize_actions(self) -> List[OrchestrationAction]:
        """Prioritize actions across workflows"""
        actions = []
        
        for workflow_id, env in self.environments.items():
            # Get recommended action (simplified - in production, use trained policy)
            action = env.action_space.sample()
            
            # Calculate expected impact
            expected_impact = self._estimate_action_impact(workflow_id, action)
            
            # Calculate priority
            priority = self._calculate_priority(workflow_id, expected_impact)
            
            actions.append(OrchestrationAction(
                workflow_id=workflow_id,
                action=action,
                priority=priority,
                expected_impact=expected_impact
            ))
        
        # Sort by priority
        actions.sort(key=lambda x: x.priority, reverse=True)
        return actions
    
    def _estimate_action_impact(
        self, workflow_id: str, action: Any
    ) -> Dict[str, float]:
        """Estimate impact of action on system-wide metrics"""
        # Simplified impact estimation
        return {
            "clinical": np.random.uniform(0, 1),
            "efficiency": np.random.uniform(0, 1),
            "financial": np.random.uniform(0, 1)
        }
    
    def _calculate_priority(
        self, workflow_id: str, expected_impact: Dict[str, float]
    ) -> float:
        """Calculate priority for action"""
        # Weighted sum of expected impacts
        weights = {"clinical": 0.4, "efficiency": 0.3, "financial": 0.3}
        priority = sum(
            weights.get(k, 0) * v
            for k, v in expected_impact.items()
        )
        
        # Boost priority for critical workflows
        if "ICU" in workflow_id or "Emergency" in workflow_id:
            priority *= 1.5
        
        return priority
    
    def _calculate_system_kpis(self) -> Dict[str, Any]:
        """Calculate system-wide KPIs"""
        if not self.workflow_states:
            return {}
        
        # Aggregate KPIs across workflows
        total_clinical_score = 0.0
        total_efficiency = 0.0
        total_financial = 0.0
        
        for state in self.workflow_states.values():
            kpis = state.kpis
            total_clinical_score += kpis.get("clinical_outcomes", {}).get("risk_score", 0.0)
            total_efficiency += kpis.get("operational_efficiency", {}).get("efficiency", 0.0)
            total_financial += kpis.get("financial_metrics", {}).get("revenue", 0.0)
        
        count = len(self.workflow_states)
        
        return {
            "avg_clinical_score": total_clinical_score / count if count > 0 else 0.0,
            "avg_efficiency": total_efficiency / count if count > 0 else 0.0,
            "avg_financial": total_financial / count if count > 0 else 0.0,
            "total_workflows": count,
            "system_health": (total_clinical_score + total_efficiency + total_financial) / (count * 3) if count > 0 else 0.0
        }
    
    def optimize_system_wide(self, target_kpis: Dict[str, float]) -> Dict[str, Any]:
        """Optimize system-wide to achieve target KPIs"""
        optimization_result = {
            "target_kpis": target_kpis,
            "current_kpis": self._calculate_system_kpis(),
            "actions_planned": [],
            "expected_improvement": {}
        }
        
        # Plan actions to reach target KPIs
        current_kpis = optimization_result["current_kpis"]
        
        for kpi_name, target_value in target_kpis.items():
            current_value = current_kpis.get(kpi_name, 0.0)
            gap = target_value - current_value
            
            if gap > 0.1:  # Significant gap
                # Find workflows that can improve this KPI
                for workflow_id, state in self.workflow_states.items():
                    if kpi_name in state.kpis:
                        optimization_result["actions_planned"].append({
                            "workflow_id": workflow_id,
                            "kpi": kpi_name,
                            "target_improvement": gap * 0.5
                        })
        
        return optimization_result
    
    def get_coordination_summary(self) -> Dict[str, Any]:
        """Get summary of coordination activities"""
        if not self.coordination_history:
            return {}
        
        return {
            "total_steps": len(self.coordination_history),
            "total_reward": sum(h["total_reward"] for h in self.coordination_history),
            "avg_reward_per_step": np.mean([h["total_reward"] for h in self.coordination_history]),
            "system_kpis": self._calculate_system_kpis(),
            "workflow_count": len(self.workflow_states)
        }

