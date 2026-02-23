"""
Operational Verifier
Evaluates operational efficiency metrics
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
from .base_verifier import BaseVerifier, VerifierConfig


class OperationalVerifier(BaseVerifier):
    """
    Verifier for operational efficiency
    
    Evaluates:
    - Pathway length efficiency
    - Resource utilization
    - Treatment sequence optimization
    - Time to improvement
    """
    
    def __init__(self, config: Optional[VerifierConfig] = None):
        """Initialize operational verifier"""
        if config is None:
            config = VerifierConfig(
                weights={
                    'pathway_efficiency': 0.4,
                    'resource_utilization': 0.3,
                    'treatment_sequence': 0.2,
                    'time_to_improvement': 0.1
                },
                thresholds={
                    'optimal_pathway_length': 5.0,
                    'max_pathway_length': 15.0,
                    'min_resource_efficiency': 0.5
                }
            )
        super().__init__(config)
    
    def evaluate(
        self,
        state: np.ndarray,
        action: Any,
        next_state: np.ndarray,
        info: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, Dict[str, float]]:
        """
        Evaluate operational efficiency
        
        Args:
            state: Current state
            action: Action taken
            next_state: Resulting state
            info: Context with pathway_step, treatment_history, etc.
        
        Returns:
            Tuple of (operational_reward, breakdown_dict)
        """
        if not self.enabled:
            return 0.0, {}
        
        info = info or {}
        pathway_step = info.get('pathway_step', 0)
        treatment_history = info.get('treatment_history', [])
        optimal_length = self.thresholds.get('optimal_pathway_length', 5.0)
        
        breakdown = {}
        
        # Pathway efficiency: how close to optimal length
        pathway_efficiency = self._calculate_pathway_efficiency(
            pathway_step, optimal_length, info
        )
        breakdown['pathway_efficiency'] = pathway_efficiency
        pathway_score = self.weights.get('pathway_efficiency', 0.4) * pathway_efficiency
        
        # Resource utilization: diversity of treatments used
        resource_utilization = self._calculate_resource_utilization(
            treatment_history, info
        )
        breakdown['resource_utilization'] = resource_utilization
        resource_score = self.weights.get('resource_utilization', 0.3) * resource_utilization
        
        # Treatment sequence: appropriate ordering
        treatment_sequence = self._calculate_treatment_sequence(
            treatment_history, action, info
        )
        breakdown['treatment_sequence'] = treatment_sequence
        sequence_score = self.weights.get('treatment_sequence', 0.2) * treatment_sequence
        
        # Time to improvement: how quickly patient improves
        time_to_improvement = self._calculate_time_to_improvement(
            state, next_state, pathway_step, info
        )
        breakdown['time_to_improvement'] = time_to_improvement
        time_score = self.weights.get('time_to_improvement', 0.1) * time_to_improvement
        
        # Total operational reward
        total_reward = pathway_score + resource_score + sequence_score + time_score
        
        # Log evaluation
        self._log_evaluation(state, action, next_state, total_reward, breakdown, info)
        
        return total_reward, breakdown
    
    def _calculate_pathway_efficiency(
        self,
        pathway_step: int,
        optimal_length: float,
        info: Dict[str, Any]
    ) -> float:
        """Calculate pathway length efficiency"""
        max_length = self.thresholds.get('max_pathway_length', 15.0)
        
        # Efficiency decreases as we deviate from optimal
        deviation = abs(pathway_step - optimal_length)
        efficiency = 1.0 - min(1.0, deviation / max_length)
        
        return max(0.0, efficiency)
    
    def _calculate_resource_utilization(
        self,
        treatment_history: list,
        info: Dict[str, Any]
    ) -> float:
        """Calculate resource utilization diversity"""
        if not treatment_history:
            return 0.5
        
        # More diverse treatments = better utilization
        unique_treatments = len(set(treatment_history))
        total_treatments = len(treatment_history)
        
        if total_treatments == 0:
            return 0.5
        
        diversity = unique_treatments / max(1, total_treatments)
        return diversity
    
    def _calculate_treatment_sequence(
        self,
        treatment_history: list,
        action: Any,
        info: Dict[str, Any]
    ) -> float:
        """Calculate treatment sequence appropriateness"""
        if len(treatment_history) < 2:
            return 1.0  # First treatment is always appropriate
        
        # Penalize premature discharge
        if action == "discharge" and len(treatment_history) < 3:
            return 0.3
        
        # Reward logical sequence (e.g., diagnostic before procedure)
        score = 1.0
        
        # Check for appropriate sequencing patterns
        if "diagnostic_test" in treatment_history and "procedure" in treatment_history:
            test_idx = treatment_history.index("diagnostic_test")
            proc_idx = treatment_history.index("procedure")
            if proc_idx < test_idx:
                score -= 0.2  # Procedure before diagnostic test
        
        return max(0.0, min(1.0, score))
    
    def _calculate_time_to_improvement(
        self,
        state: np.ndarray,
        next_state: np.ndarray,
        pathway_step: int,
        info: Dict[str, Any]
    ) -> float:
        """Calculate time to improvement score"""
        if len(state) < 4 or len(next_state) < 4:
            return 0.5
        
        # Improvement = risk reduction
        prev_risk = state[3]
        curr_risk = next_state[3]
        improvement = prev_risk - curr_risk
        
        if improvement <= 0:
            return 0.0
        
        # Faster improvement = better score
        # Normalize by pathway step (earlier improvement is better)
        time_score = improvement * (1.0 - min(1.0, pathway_step / 10.0))
        
        return max(0.0, min(1.0, time_score))

