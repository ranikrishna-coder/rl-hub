"""
Reward Logger
Logs reward calculations and breakdowns for observability
"""

from typing import Dict, Any, Optional, List
import numpy as np
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid


@dataclass
class RewardLogEntry:
    """Single reward log entry"""
    episode_id: str
    step_id: int
    state_id: str
    action: Any
    reward: float
    reward_breakdown: Dict[str, float]
    verifier_name: str
    timestamp: datetime
    metadata: Dict[str, Any]


class RewardLogger:
    """
    Logger for reward calculations
    
    Tracks:
    - Episode ID
    - Step ID
    - State ID
    - Action taken
    - Reward value
    - Reward breakdown (components)
    - Verifier information
    """
    
    def __init__(self, persist_to_db: bool = False, db_connection=None):
        """
        Initialize reward logger
        
        Args:
            persist_to_db: Whether to persist logs to database
            db_connection: Database connection (if persisting)
        """
        self.persist_to_db = persist_to_db
        self.db_connection = db_connection
        self.logs: List[RewardLogEntry] = []
        self.episode_logs: Dict[str, List[RewardLogEntry]] = {}
    
    def log_reward(
        self,
        episode_id: str,
        step_id: int,
        state: np.ndarray,
        action: Any,
        reward: float,
        reward_breakdown: Dict[str, float],
        verifier_name: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a reward calculation
        
        Args:
            episode_id: Unique episode identifier
            step_id: Step number within episode
            state: State vector (for state_id generation)
            action: Action taken
            reward: Total reward value
            reward_breakdown: Dictionary of reward components
            verifier_name: Name of verifier that calculated reward
            metadata: Additional metadata
        """
        # Generate state ID from state hash
        state_id = self._generate_state_id(state)
        
        entry = RewardLogEntry(
            episode_id=episode_id,
            step_id=step_id,
            state_id=state_id,
            action=action,
            reward=reward,
            reward_breakdown=reward_breakdown.copy(),
            verifier_name=verifier_name,
            timestamp=datetime.now(),
            metadata=metadata or {}
        )
        
        # Store in memory
        self.logs.append(entry)
        
        if episode_id not in self.episode_logs:
            self.episode_logs[episode_id] = []
        self.episode_logs[episode_id].append(entry)
        
        # Persist to database if enabled
        if self.persist_to_db and self.db_connection:
            self._persist_to_db(entry)
    
    def get_episode_rewards(self, episode_id: str) -> List[RewardLogEntry]:
        """Get all reward logs for an episode"""
        return self.episode_logs.get(episode_id, [])
    
    def get_reward_breakdown(self, episode_id: str, step_id: int) -> Optional[Dict[str, float]]:
        """Get reward breakdown for specific step"""
        episode_logs = self.get_episode_rewards(episode_id)
        for log in episode_logs:
            if log.step_id == step_id:
                return log.reward_breakdown
        return None
    
    def get_episode_summary(self, episode_id: str) -> Dict[str, Any]:
        """Get summary statistics for an episode"""
        episode_logs = self.get_episode_rewards(episode_id)
        
        if not episode_logs:
            return {}
        
        total_reward = sum(log.reward for log in episode_logs)
        avg_reward = total_reward / len(episode_logs) if episode_logs else 0.0
        
        # Aggregate breakdown components
        breakdown_aggregate = {}
        for log in episode_logs:
            for component, value in log.reward_breakdown.items():
                if component not in breakdown_aggregate:
                    breakdown_aggregate[component] = []
                breakdown_aggregate[component].append(value)
        
        breakdown_summary = {
            component: {
                'total': sum(values),
                'average': sum(values) / len(values) if values else 0.0,
                'min': min(values) if values else 0.0,
                'max': max(values) if values else 0.0
            }
            for component, values in breakdown_aggregate.items()
        }
        
        return {
            'episode_id': episode_id,
            'total_steps': len(episode_logs),
            'total_reward': total_reward,
            'average_reward': avg_reward,
            'reward_breakdown_summary': breakdown_summary,
            'verifiers_used': list(set(log.verifier_name for log in episode_logs))
        }
    
    def _generate_state_id(self, state: np.ndarray) -> str:
        """Generate unique ID for state"""
        # Use hash of state array
        state_hash = hash(state.tobytes() if isinstance(state, np.ndarray) else str(state))
        return f"state_{abs(state_hash)}"
    
    def _persist_to_db(self, entry: RewardLogEntry):
        """Persist log entry to database"""
        # This will be implemented when database schema is ready
        # For now, just a placeholder
        pass
    
    def clear_logs(self):
        """Clear all logs (for testing/debugging)"""
        self.logs = []
        self.episode_logs = {}

