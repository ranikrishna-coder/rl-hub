"""
Clinical Verifier
Evaluates clinical outcomes and patient safety metrics
"""

from typing import Dict, Any, Optional, Tuple
import numpy as np
from .base_verifier import BaseVerifier, VerifierConfig, RewardComponent


class ClinicalVerifier(BaseVerifier):
    """
    Verifier for clinical outcomes and patient safety
    
    Evaluates:
    - Risk score improvements
    - Vital sign stability
    - Condition severity changes
    - Mortality risk reduction
    """
    
    def __init__(self, config: Optional[VerifierConfig] = None):
        """Initialize clinical verifier with default weights"""
        if config is None:
            config = VerifierConfig(
                weights={
                    'risk_improvement': 0.4,
                    'vital_stability': 0.3,
                    'severity_reduction': 0.2,
                    'mortality_reduction': 0.1
                },
                thresholds={
                    'min_risk_improvement': 0.01,
                    'max_risk_score': 0.8,
                    'critical_vital_threshold': 0.7
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
        Evaluate clinical outcomes
        
        Args:
            state: Current state (includes patient risk_score, vitals, severity)
            action: Treatment action taken
            next_state: Resulting state after treatment
            info: Additional context with patient object, treatment history
        
        Returns:
            Tuple of (clinical_reward, breakdown_dict)
        """
        if not self.enabled:
            return 0.0, {}
        
        info = info or {}
        patient = info.get('patient')
        previous_risk = info.get('previous_risk_score', state[3] if len(state) > 3 else 0.5)
        current_risk = next_state[3] if len(next_state) > 3 else previous_risk
        
        breakdown = {}
        
        # Risk improvement component
        risk_improvement = max(0, previous_risk - current_risk)
        breakdown['risk_improvement'] = risk_improvement
        risk_score = self.weights.get('risk_improvement', 0.4) * risk_improvement
        
        # Vital stability component
        vital_stability = self._calculate_vital_stability(next_state, patient, info)
        breakdown['vital_stability'] = vital_stability
        vital_score = self.weights.get('vital_stability', 0.3) * vital_stability
        
        # Severity reduction component
        severity_reduction = self._calculate_severity_reduction(state, next_state, patient, info)
        breakdown['severity_reduction'] = severity_reduction
        severity_score = self.weights.get('severity_reduction', 0.2) * severity_reduction
        
        # Mortality risk reduction (if applicable)
        mortality_reduction = self._calculate_mortality_reduction(state, next_state, patient, info)
        breakdown['mortality_reduction'] = mortality_reduction
        mortality_score = self.weights.get('mortality_reduction', 0.1) * mortality_reduction
        
        # Total clinical reward
        total_reward = risk_score + vital_score + severity_score + mortality_score
        
        # Log evaluation
        self._log_evaluation(state, action, next_state, total_reward, breakdown, info)
        
        return total_reward, breakdown
    
    def _calculate_vital_stability(
        self,
        state: np.ndarray,
        patient: Any,
        info: Dict[str, Any]
    ) -> float:
        """Calculate vital sign stability score"""
        if patient is None:
            # Extract from state if patient object not available
            # Assuming vitals are at indices 4-10 (based on TreatmentPathwayOptimization)
            if len(state) > 10:
                # Normalize vitals back to original scale for calculation
                oxygen_sat = state[8] * 100.0  # oxygen_saturation normalized
                # Stability: how close to normal (98% for O2 sat)
                stability = 1.0 - abs(oxygen_sat - 98) / 20.0
                return max(0.0, min(1.0, stability))
            return 0.5
        
        # Use patient object if available
        vitals = getattr(patient, 'vitals', {})
        oxygen_sat = vitals.get('oxygen_saturation', 98)
        stability = 1.0 - abs(oxygen_sat - 98) / 20.0
        return max(0.0, min(1.0, stability))
    
    def _calculate_severity_reduction(
        self,
        state: np.ndarray,
        next_state: np.ndarray,
        patient: Any,
        info: Dict[str, Any]
    ) -> float:
        """Calculate condition severity reduction"""
        if patient is None:
            # Extract severity from state (index 2 in TreatmentPathwayOptimization)
            if len(state) > 2 and len(next_state) > 2:
                prev_severity = state[2]
                curr_severity = next_state[2]
                reduction = max(0, prev_severity - curr_severity)
                return reduction
            return 0.0
        
        # Use patient object if available
        prev_severity = getattr(patient, 'previous_severity', None)
        curr_severity = getattr(patient, 'severity', None)
        
        if prev_severity is None or curr_severity is None:
            return 0.0
        
        # Map severity enum to numeric (mild=0.25, moderate=0.5, severe=0.75, critical=1.0)
        severity_map = {
            'MILD': 0.25,
            'MODERATE': 0.5,
            'SEVERE': 0.75,
            'CRITICAL': 1.0
        }
        
        prev_val = severity_map.get(str(prev_severity).upper(), 0.5)
        curr_val = severity_map.get(str(curr_severity).upper(), 0.5)
        
        reduction = max(0, prev_val - curr_val)
        return reduction
    
    def _calculate_mortality_reduction(
        self,
        state: np.ndarray,
        next_state: np.ndarray,
        patient: Any,
        info: Dict[str, Any]
    ) -> float:
        """Calculate mortality risk reduction"""
        # For TreatmentPathwayOptimization, mortality risk is correlated with risk_score
        # Higher risk_score = higher mortality risk
        if len(state) > 3 and len(next_state) > 3:
            prev_risk = state[3]
            curr_risk = next_state[3]
            reduction = max(0, prev_risk - curr_risk)
            return reduction
        
        return 0.0

