"""
Base RL Environment
Implements Gymnasium-compatible interface with healthcare-specific features
"""

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from typing import Dict, Any, Tuple, Optional
from abc import ABC, abstractmethod
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
class RewardWeights:
    """Configurable weights for reward components"""
    clinical: float = 0.3
    efficiency: float = 0.2
    financial: float = 0.2
    patient_satisfaction: float = 0.1
    risk_penalty: float = 0.1
    compliance_penalty: float = 0.1


@dataclass
class KPIMetrics:
    """Structured KPI metrics"""
    clinical_outcomes: Dict[str, float]
    operational_efficiency: Dict[str, float]
    financial_metrics: Dict[str, float]
    patient_satisfaction: float
    risk_score: float
    compliance_score: float
    timestamp: float


class HealthcareRLEnvironment(gym.Env):
    """
    Base class for all RL Hub Environments
    
    All environments inherit from this class and implement:
    - State space definition
    - Action space definition
    - State transition logic
    - Reward calculation
    - KPI tracking
    """
    
    metadata = {"render_modes": ["human", "rgb_array"]}
    
    def __init__(
        self,
        config: Optional[Dict[str, Any]] = None,
        reward_weights: Optional[RewardWeights] = None,
        max_steps: int = 1000,
        seed: Optional[int] = None
    ):
        super().__init__()
        
        self.config = config or {}
        self.reward_weights = reward_weights or RewardWeights()
        self.max_steps = max_steps
        self.time_step = 0
        self.current_state = None
        self.simulator = None
        
        # Initialize spaces (to be overridden by subclasses)
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf, shape=(1,), dtype=np.float32
        )
        self.action_space = spaces.Discrete(1)
        
        # KPI tracking
        self.kpi_history: list[KPIMetrics] = []
        self.episode_rewards: list[float] = []
        
        # Set random seed
        if seed is not None:
            self.np_random = np.random.default_rng(seed)
        else:
            self.np_random = np.random.default_rng()
    
    @abstractmethod
    def _initialize_state(self) -> np.ndarray:
        """Initialize the initial state vector"""
        pass
    
    @abstractmethod
    def _get_state_features(self) -> np.ndarray:
        """Extract current state features"""
        pass
    
    @abstractmethod
    def _apply_action(self, action: Any) -> Dict[str, Any]:
        """Apply action and return transition info"""
        pass
    
    @abstractmethod
    def _calculate_reward_components(self, state: np.ndarray, action: Any, info: Dict[str, Any]) -> Dict[RewardComponent, float]:
        """Calculate individual reward components"""
        pass
    
    @abstractmethod
    def _is_done(self) -> bool:
        """Check if episode is done"""
        pass
    
    @abstractmethod
    def _get_kpis(self) -> KPIMetrics:
        """Calculate current KPI metrics"""
        pass
    
    def reset(
        self,
        seed: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """Reset environment to initial state"""
        super().reset(seed=seed)
        
        if seed is not None:
            self.np_random = np.random.default_rng(seed)
        
        self.time_step = 0
        self.current_state = self._initialize_state()
        self.kpi_history = []
        self.episode_rewards = []
        
        # Reset simulator if exists
        if self.simulator:
            self.simulator.reset()
        
        info = {
            "time_step": self.time_step,
            "kpis": self._get_kpis().__dict__
        }
        
        return self._get_state_features(), info
    
    def step(
        self, action: Any
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """Execute one step in the environment"""
        self.time_step += 1
        
        # Apply action and get transition info
        transition_info = self._apply_action(action)
        
        # Update state
        self.current_state = self._get_state_features()
        
        # Calculate reward components
        reward_components = self._calculate_reward_components(
            self.current_state, action, transition_info
        )
        
        # Compute weighted reward
        reward = (
            self.reward_weights.clinical * reward_components.get(RewardComponent.CLINICAL, 0.0) +
            self.reward_weights.efficiency * reward_components.get(RewardComponent.EFFICIENCY, 0.0) +
            self.reward_weights.financial * reward_components.get(RewardComponent.FINANCIAL, 0.0) +
            self.reward_weights.patient_satisfaction * reward_components.get(RewardComponent.PATIENT_SATISFACTION, 0.0) -
            self.reward_weights.risk_penalty * reward_components.get(RewardComponent.RISK_PENALTY, 0.0) -
            self.reward_weights.compliance_penalty * reward_components.get(RewardComponent.COMPLIANCE_PENALTY, 0.0)
        )
        
        self.episode_rewards.append(reward)
        
        # Check termination
        terminated = self._is_done()
        truncated = self.time_step >= self.max_steps
        
        # Get KPIs
        kpis = self._get_kpis()
        self.kpi_history.append(kpis)
        
        info = {
            "time_step": self.time_step,
            "reward_components": {k.value: v for k, v in reward_components.items()},
            "kpis": kpis.__dict__,
            "transition_info": transition_info
        }
        
        return self.current_state, reward, terminated, truncated, info
    
    def calculate_reward(
        self, state: np.ndarray, action: Any, info: Dict[str, Any]
    ) -> float:
        """Calculate reward for given state-action pair"""
        reward_components = self._calculate_reward_components(state, action, info)
        return (
            self.reward_weights.clinical * reward_components.get(RewardComponent.CLINICAL, 0.0) +
            self.reward_weights.efficiency * reward_components.get(RewardComponent.EFFICIENCY, 0.0) +
            self.reward_weights.financial * reward_components.get(RewardComponent.FINANCIAL, 0.0) +
            self.reward_weights.patient_satisfaction * reward_components.get(RewardComponent.PATIENT_SATISFACTION, 0.0) -
            self.reward_weights.risk_penalty * reward_components.get(RewardComponent.RISK_PENALTY, 0.0) -
            self.reward_weights.compliance_penalty * reward_components.get(RewardComponent.COMPLIANCE_PENALTY, 0.0)
        )
    
    def get_kpis(self) -> KPIMetrics:
        """Get current KPI metrics"""
        return self._get_kpis()
    
    def get_episode_summary(self) -> Dict[str, Any]:
        """Get summary statistics for current episode"""
        if not self.kpi_history:
            return {}
        
        return {
            "total_reward": sum(self.episode_rewards),
            "mean_reward": np.mean(self.episode_rewards) if self.episode_rewards else 0.0,
            "episode_length": self.time_step,
            "final_kpis": self.kpi_history[-1].__dict__ if self.kpi_history else {},
            "kpi_trends": {
                "clinical_outcomes": [k.clinical_outcomes for k in self.kpi_history],
                "efficiency": [k.operational_efficiency for k in self.kpi_history],
                "financial": [k.financial_metrics for k in self.kpi_history]
            }
        }
    
    def render(self, mode: str = "human"):
        """Render environment state"""
        if mode == "human":
            print(f"Time Step: {self.time_step}")
            print(f"State: {self.current_state}")
            if self.kpi_history:
                print(f"KPIs: {self.kpi_history[-1].__dict__}")
        elif mode == "rgb_array":
            # Return RGB array for visualization
            return np.zeros((480, 640, 3), dtype=np.uint8)
    
    def close(self):
        """Clean up resources"""
        if self.simulator:
            self.simulator.close()

