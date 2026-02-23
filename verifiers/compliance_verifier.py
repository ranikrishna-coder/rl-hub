"""
Compliance Verifier
Evaluates compliance with clinical guidelines and safety rules
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
from .base_verifier import BaseVerifier, VerifierConfig


class ComplianceVerifier(BaseVerifier):
    """
    Verifier for compliance and safety
    
    Evaluates:
    - Clinical guideline compliance
    - Safety rule adherence
    - Appropriate treatment sequencing
    - Risk threshold violations
    """
    
    def __init__(self, config: Optional[VerifierConfig] = None):
        """Initialize compliance verifier"""
        if config is None:
            config = VerifierConfig(
                weights={
                    'guideline_compliance': 0.4,
                    'safety_adherence': 0.3,
                    'treatment_appropriateness': 0.2,
                    'risk_management': 0.1
                },
                thresholds={
                    'min_pathway_steps_before_discharge': 3,
                    'max_procedures_per_episode': 2,
                    'max_risk_score': 0.8,
                    'critical_risk_threshold': 0.7
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
        Evaluate compliance (returns penalty, so negative values)
        
        Args:
            state: Current state
            action: Action taken
            next_state: Resulting state
            info: Context with treatment_history, pathway_step, etc.
        
        Returns:
            Tuple of (compliance_penalty, breakdown_dict)
            Note: This returns penalties (negative values), which are subtracted from reward
        """
        if not self.enabled:
            return 0.0, {}
        
        info = info or {}
        treatment_history = info.get('treatment_history', [])
        pathway_step = info.get('pathway_step', 0)
        
        breakdown = {}
        
        # Guideline compliance: appropriate treatment sequences
        guideline_penalty = self._calculate_guideline_compliance(
            treatment_history, action, pathway_step, info
        )
        breakdown['guideline_compliance'] = guideline_penalty
        guideline_score = self.weights.get('guideline_compliance', 0.4) * guideline_penalty
        
        # Safety adherence: avoiding unsafe actions
        safety_penalty = self._calculate_safety_adherence(
            state, action, next_state, info
        )
        breakdown['safety_adherence'] = safety_penalty
        safety_score = self.weights.get('safety_adherence', 0.3) * safety_penalty
        
        # Treatment appropriateness: right treatment for condition
        treatment_penalty = self._calculate_treatment_appropriateness(
            state, action, info
        )
        breakdown['treatment_appropriateness'] = treatment_penalty
        treatment_score = self.weights.get('treatment_appropriateness', 0.2) * treatment_penalty
        
        # Risk management: managing high-risk situations
        risk_penalty = self._calculate_risk_management(
            state, next_state, info
        )
        breakdown['risk_management'] = risk_penalty
        risk_score = self.weights.get('risk_management', 0.1) * risk_penalty
        
        # Total compliance penalty (negative values)
        total_penalty = -(guideline_score + safety_score + treatment_score + risk_score)
        
        # Log evaluation
        self._log_evaluation(state, action, next_state, total_penalty, breakdown, info)
        
        return total_penalty, breakdown
    
    def _calculate_guideline_compliance(
        self,
        treatment_history: list,
        action: Any,
        pathway_step: int,
        info: Dict[str, Any]
    ) -> float:
        """Calculate guideline compliance penalty"""
        penalty = 0.0
        
        # Penalize premature discharge
        min_steps = self.thresholds.get('min_pathway_steps_before_discharge', 3)
        if action == "discharge" and pathway_step < min_steps:
            penalty += 0.3
        
        # Penalize too many procedures
        max_procedures = self.thresholds.get('max_procedures_per_episode', 2)
        procedure_count = treatment_history.count("procedure")
        if procedure_count > max_procedures:
            penalty += 0.2
        
        return min(1.0, penalty)
    
    def _calculate_safety_adherence(
        self,
        state: np.ndarray,
        action: Any,
        next_state: np.ndarray,
        info: Dict[str, Any]
    ) -> float:
        """Calculate safety adherence penalty"""
        penalty = 0.0
        
        # Check for unsafe actions on critical patients
        if len(state) > 2:
            severity = state[2]  # Condition severity
            if severity > 0.75:  # Critical condition
                # Penalize non-urgent actions on critical patients
                if action in ["monitoring", "discharge"]:
                    penalty += 0.2
        
        return min(1.0, penalty)
    
    def _calculate_treatment_appropriateness(
        self,
        state: np.ndarray,
        action: Any,
        info: Dict[str, Any]
    ) -> float:
        """Calculate treatment appropriateness penalty"""
        penalty = 0.0
        
        # Check if treatment matches patient condition
        # This is a simplified check - can be expanded
        treatment_history = info.get('treatment_history', [])
        
        # Penalize repeated same treatment without improvement
        if len(treatment_history) >= 2:
            if treatment_history[-1] == treatment_history[-2] == action:
                # Same treatment 3 times in a row might indicate ineffectiveness
                penalty += 0.1
        
        return min(1.0, penalty)
    
    def _calculate_risk_management(
        self,
        state: np.ndarray,
        next_state: np.ndarray,
        info: Dict[str, Any]
    ) -> float:
        """Calculate risk management penalty"""
        if len(state) < 4 or len(next_state) < 4:
            return 0.0
        
        penalty = 0.0
        max_risk = self.thresholds.get('max_risk_score', 0.8)
        critical_risk = self.thresholds.get('critical_risk_threshold', 0.7)
        
        current_risk = next_state[3]
        
        # Penalize if risk exceeds threshold
        if current_risk > max_risk:
            penalty += 0.5
        elif current_risk > critical_risk:
            penalty += 0.2
        
        return min(1.0, penalty)

