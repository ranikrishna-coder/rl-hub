"""
Ensemble Verifier
Combines multiple verifiers into a single reward signal
"""

from typing import Dict, Any, Optional, Tuple, List
import numpy as np
from .base_verifier import BaseVerifier, VerifierConfig


class EnsembleVerifier(BaseVerifier):
    """
    Ensemble verifier that combines multiple verifiers
    
    Combines rewards from:
    - Clinical verifier
    - Operational verifier
    - Financial verifier
    - Compliance verifier (penalties)
    """
    
    def __init__(
        self,
        verifiers: List[BaseVerifier],
        config: Optional[VerifierConfig] = None
    ):
        """
        Initialize ensemble verifier
        
        Args:
            verifiers: List of verifier instances to combine
            config: Optional configuration for ensemble weights
        """
        if config is None:
            # Default: equal weights for all verifiers
            verifier_weights = {f'verifier_{i}': 1.0 / len(verifiers) for i in range(len(verifiers))}
            config = VerifierConfig(
                weights=verifier_weights,
                thresholds={}
            )
        
        super().__init__(config)
        self.verifiers = verifiers
        
        # Validate all verifiers are enabled
        self.verifiers = [v for v in self.verifiers if v.is_enabled()]
    
    def evaluate(
        self,
        state: np.ndarray,
        action: Any,
        next_state: np.ndarray,
        info: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, Dict[str, float]]:
        """
        Evaluate using all verifiers and combine results
        
        Args:
            state: Current state
            action: Action taken
            next_state: Resulting state
            info: Additional context
        
        Returns:
            Tuple of (total_reward, combined_breakdown)
        """
        if not self.enabled or not self.verifiers:
            return 0.0, {}
        
        info = info or {}
        total_reward = 0.0
        combined_breakdown = {}
        
        # Evaluate each verifier
        for i, verifier in enumerate(self.verifiers):
            if not verifier.is_enabled():
                continue
            
            verifier_reward, verifier_breakdown = verifier.evaluate(
                state, action, next_state, info
            )
            
            # Get weight for this verifier
            verifier_weight = self.weights.get(f'verifier_{i}', 1.0 / len(self.verifiers))
            
            # Add weighted reward
            weighted_reward = verifier_reward * verifier_weight
            total_reward += weighted_reward
            
            # Add breakdown with verifier prefix
            verifier_name = verifier.__class__.__name__
            for component, value in verifier_breakdown.items():
                breakdown_key = f"{verifier_name}_{component}"
                combined_breakdown[breakdown_key] = value
                # Also add weighted component
                combined_breakdown[f"{breakdown_key}_weighted"] = value * verifier_weight
        
        # Add total reward to breakdown
        combined_breakdown['total_reward'] = total_reward
        combined_breakdown['num_verifiers'] = len(self.verifiers)
        
        # Log evaluation
        self._log_evaluation(state, action, next_state, total_reward, combined_breakdown, info)
        
        return total_reward, combined_breakdown
    
    def add_verifier(self, verifier: BaseVerifier):
        """Add a verifier to the ensemble"""
        if verifier not in self.verifiers:
            self.verifiers.append(verifier)
            # Update weights to maintain equal weighting
            num_verifiers = len(self.verifiers)
            self.weights = {f'verifier_{i}': 1.0 / num_verifiers for i in range(num_verifiers)}
    
    def remove_verifier(self, verifier: BaseVerifier):
        """Remove a verifier from the ensemble"""
        if verifier in self.verifiers:
            self.verifiers.remove(verifier)
            # Update weights
            num_verifiers = len(self.verifiers)
            if num_verifiers > 0:
                self.weights = {f'verifier_{i}': 1.0 / num_verifiers for i in range(num_verifiers)}
    
    def get_verifier_names(self) -> List[str]:
        """Get names of all verifiers in ensemble"""
        return [v.__class__.__name__ for v in self.verifiers]

