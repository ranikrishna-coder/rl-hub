"""
Base Verifier Class
Abstract base class for all reward verifiers
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
import numpy as np
from dataclasses import dataclass
from enum import Enum


class RewardComponent(Enum):
    """Components of the reward function"""
    CLINICAL = "clinical"
    EFFICIENCY = "efficiency"
    FINANCIAL = "financial"
    PATIENT_SATISFACTION = "patient_satisfaction"
    RISK_PENALTY = "risk_penalty"
    COMPLIANCE_PENALTY = "compliance_penalty"


@dataclass
class VerifierConfig:
    """Configuration for verifier"""
    weights: Dict[str, float]
    thresholds: Dict[str, float]
    enabled: bool = True
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseVerifier(ABC):
    """
    Base class for all reward verifiers
    
    Verifiers are responsible for:
    1. Evaluating state-action transitions
    2. Decomposing rewards into components
    3. Providing breakdown of reward sources
    """
    
    def __init__(self, config: Optional[VerifierConfig] = None):
        """
        Initialize verifier
        
        Args:
            config: Verifier configuration with weights and thresholds
        """
        self.config = config or VerifierConfig(
            weights={},
            thresholds={}
        )
        self.weights = self.config.weights
        self.thresholds = self.config.thresholds
        self.enabled = self.config.enabled
        self.metadata = self.config.metadata or {}
        
        # Track evaluation history for observability
        self.evaluation_history = []
    
    @abstractmethod
    def evaluate(
        self,
        state: np.ndarray,
        action: Any,
        next_state: np.ndarray,
        info: Optional[Dict[str, Any]] = None
    ) -> Tuple[float, Dict[str, float]]:
        """
        Evaluate state-action transition and return reward with breakdown
        
        Args:
            state: Current state vector
            action: Action taken
            next_state: Resulting state after action
            info: Additional context (patient data, treatment history, etc.)
        
        Returns:
            Tuple of (total_reward, reward_breakdown)
            - total_reward: Scalar reward value
            - reward_breakdown: Dict mapping component names to values
        """
        raise NotImplementedError
    
    def breakdown(self) -> Dict[str, float]:
        """
        Get breakdown of reward components from last evaluation
        
        Returns:
            Dictionary mapping component names to values
        """
        if not self.evaluation_history:
            return {}
        
        return self.evaluation_history[-1].get('breakdown', {})
    
    def get_component_names(self) -> list[str]:
        """
        Get list of reward component names this verifier produces
        
        Returns:
            List of component name strings
        """
        return list(self.weights.keys())
    
    def is_enabled(self) -> bool:
        """Check if verifier is enabled"""
        return self.enabled
    
    def enable(self):
        """Enable verifier"""
        self.enabled = True
    
    def disable(self):
        """Disable verifier"""
        self.enabled = False
    
    def update_config(self, config: VerifierConfig):
        """Update verifier configuration"""
        self.config = config
        self.weights = config.weights
        self.thresholds = config.thresholds
        self.enabled = config.enabled
        self.metadata = config.metadata or {}
    
    def _log_evaluation(
        self,
        state: np.ndarray,
        action: Any,
        next_state: np.ndarray,
        reward: float,
        breakdown: Dict[str, float],
        info: Optional[Dict[str, Any]] = None
    ):
        """Log evaluation for observability"""
        self.evaluation_history.append({
            'state': state.copy() if isinstance(state, np.ndarray) else state,
            'action': action,
            'next_state': next_state.copy() if isinstance(next_state, np.ndarray) else next_state,
            'reward': reward,
            'breakdown': breakdown.copy(),
            'info': info or {}
        })
        
        # Keep only last 1000 evaluations to prevent memory issues
        if len(self.evaluation_history) > 1000:
            self.evaluation_history = self.evaluation_history[-1000:]

