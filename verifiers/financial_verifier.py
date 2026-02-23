"""
Financial Verifier
Evaluates financial metrics and cost-effectiveness
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
from .base_verifier import BaseVerifier, VerifierConfig


class FinancialVerifier(BaseVerifier):
    """
    Verifier for financial outcomes
    
    Evaluates:
    - Cost-effectiveness
    - Total cost management
    - Cost per improvement
    - Revenue optimization
    """
    
    def __init__(self, config: Optional[VerifierConfig] = None):
        """Initialize financial verifier"""
        if config is None:
            config = VerifierConfig(
                weights={
                    'cost_effectiveness': 0.5,
                    'cost_management': 0.3,
                    'revenue_optimization': 0.2
                },
                thresholds={
                    'max_cost_per_step': 500.0,
                    'target_cost_effectiveness': 0.7,
                    'cost_improvement_ratio': 1000.0
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
        Evaluate financial outcomes
        
        Args:
            state: Current state
            action: Action taken
            next_state: Resulting state
            info: Context with total_cost, treatment_costs, etc.
        
        Returns:
            Tuple of (financial_reward, breakdown_dict)
        """
        if not self.enabled:
            return 0.0, {}
        
        info = info or {}
        total_cost = info.get('total_cost', 0.0)
        treatment_cost = info.get('cost', 0.0)
        pathway_step = info.get('pathway_step', 1)
        
        breakdown = {}
        
        # Cost-effectiveness: improvement per dollar spent
        cost_effectiveness = self._calculate_cost_effectiveness(
            state, next_state, total_cost, info
        )
        breakdown['cost_effectiveness'] = cost_effectiveness
        effectiveness_score = self.weights.get('cost_effectiveness', 0.5) * cost_effectiveness
        
        # Cost management: keeping costs reasonable
        cost_management = self._calculate_cost_management(
            total_cost, pathway_step, treatment_cost, info
        )
        breakdown['cost_management'] = cost_management
        management_score = self.weights.get('cost_management', 0.3) * cost_management
        
        # Revenue optimization (if applicable)
        revenue_optimization = self._calculate_revenue_optimization(
            action, treatment_cost, info
        )
        breakdown['revenue_optimization'] = revenue_optimization
        revenue_score = self.weights.get('revenue_optimization', 0.2) * revenue_optimization
        
        # Total financial reward
        total_reward = effectiveness_score + management_score + revenue_score
        
        # Log evaluation
        self._log_evaluation(state, action, next_state, total_reward, breakdown, info)
        
        return total_reward, breakdown
    
    def _calculate_cost_effectiveness(
        self,
        state: np.ndarray,
        next_state: np.ndarray,
        total_cost: float,
        info: Dict[str, Any]
    ) -> float:
        """Calculate cost-effectiveness ratio"""
        if len(state) < 4 or len(next_state) < 4:
            return 0.5
        
        # Improvement = risk reduction
        prev_risk = state[3]
        curr_risk = next_state[3]
        improvement = max(0.01, prev_risk - curr_risk)
        
        if total_cost <= 0:
            return 1.0 if improvement > 0 else 0.5
        
        # Cost per improvement
        cost_per_improvement = total_cost / improvement
        cost_ratio = self.thresholds.get('cost_improvement_ratio', 1000.0)
        
        # Better cost-effectiveness = lower cost per improvement
        effectiveness = 1.0 / (1.0 + cost_per_improvement / cost_ratio)
        
        return max(0.0, min(1.0, effectiveness))
    
    def _calculate_cost_management(
        self,
        total_cost: float,
        pathway_step: int,
        treatment_cost: float,
        info: Dict[str, Any]
    ) -> float:
        """Calculate cost management score"""
        if pathway_step == 0:
            return 1.0
        
        # Average cost per step
        avg_cost_per_step = total_cost / pathway_step
        max_cost = self.thresholds.get('max_cost_per_step', 500.0)
        
        # Lower average cost = better management
        management = 1.0 / (1.0 + avg_cost_per_step / max_cost)
        
        return max(0.0, min(1.0, management))
    
    def _calculate_revenue_optimization(
        self,
        action: Any,
        treatment_cost: float,
        info: Dict[str, Any]
    ) -> float:
        """Calculate revenue optimization score"""
        # For TreatmentPathwayOptimization, revenue is correlated with appropriate treatment selection
        # Higher-value treatments (procedures, specialist consults) generate more revenue
        # but should be used appropriately
        
        treatment_revenue_map = {
            "medication_adjustment": 0.3,
            "diagnostic_test": 0.5,
            "specialist_consult": 0.7,
            "procedure": 0.9,
            "monitoring": 0.2,
            "discharge": 0.0
        }
        
        revenue_score = treatment_revenue_map.get(str(action), 0.5)
        
        # Normalize to 0-1 range
        return revenue_score

