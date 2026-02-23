"""
Risk Thresholds
Defines and manages risk thresholds for governance
"""

from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass


@dataclass
class RiskThresholdConfig:
    """Configuration for risk thresholds"""
    max_risk_score: float = 0.8
    critical_risk_threshold: float = 0.7
    warning_risk_threshold: float = 0.5
    min_risk_score: float = 0.0
    
    # Environment-specific thresholds
    environment_thresholds: Dict[str, Dict[str, float]] = None
    
    def __post_init__(self):
        if self.environment_thresholds is None:
            self.environment_thresholds = {}


class RiskThresholds:
    """
    Manages risk thresholds for different environments and scenarios
    
    Provides:
    - Risk level classification
    - Threshold validation
    - Environment-specific thresholds
    """
    
    def __init__(self, config: Optional[RiskThresholdConfig] = None):
        """
        Initialize risk thresholds
        
        Args:
            config: Risk threshold configuration
        """
        self.config = config or RiskThresholdConfig()
    
    def get_risk_level(self, risk_score: float, environment_name: Optional[str] = None) -> str:
        """
        Get risk level for a given risk score
        
        Args:
            risk_score: Risk score value
            environment_name: Optional environment name for specific thresholds
        
        Returns:
            Risk level: 'low', 'medium', 'high', 'critical'
        """
        # Get environment-specific thresholds if available
        thresholds = self._get_thresholds_for_environment(environment_name)
        
        if risk_score >= thresholds['critical']:
            return 'critical'
        elif risk_score >= thresholds['high']:
            return 'high'
        elif risk_score >= thresholds['warning']:
            return 'medium'
        else:
            return 'low'
    
    def is_risk_acceptable(
        self,
        risk_score: float,
        environment_name: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Check if risk score is acceptable
        
        Args:
            risk_score: Risk score value
            environment_name: Optional environment name
        
        Returns:
            Tuple of (is_acceptable, reason)
        """
        thresholds = self._get_thresholds_for_environment(environment_name)
        
        if risk_score > thresholds['max']:
            return False, f"Risk score {risk_score:.2f} exceeds maximum threshold {thresholds['max']}"
        
        return True, ""
    
    def get_threshold_for_level(
        self,
        level: str,
        environment_name: Optional[str] = None
    ) -> float:
        """
        Get threshold value for a risk level
        
        Args:
            level: Risk level ('low', 'medium', 'high', 'critical')
            environment_name: Optional environment name
        
        Returns:
            Threshold value
        """
        thresholds = self._get_thresholds_for_environment(environment_name)
        
        level_map = {
            'low': thresholds['min'],
            'medium': thresholds['warning'],
            'high': thresholds['critical'],
            'critical': thresholds['max']
        }
        
        return level_map.get(level.lower(), thresholds['max'])
    
    def _get_thresholds_for_environment(self, environment_name: Optional[str] = None) -> Dict[str, float]:
        """Get thresholds for specific environment or defaults"""
        if environment_name and environment_name in self.config.environment_thresholds:
            env_thresholds = self.config.environment_thresholds[environment_name]
            return {
                'min': env_thresholds.get('min_risk_score', self.config.min_risk_score),
                'warning': env_thresholds.get('warning_risk_threshold', self.config.warning_risk_threshold),
                'critical': env_thresholds.get('critical_risk_threshold', self.config.critical_risk_threshold),
                'max': env_thresholds.get('max_risk_score', self.config.max_risk_score)
            }
        
        return {
            'min': self.config.min_risk_score,
            'warning': self.config.warning_risk_threshold,
            'critical': self.config.critical_risk_threshold,
            'max': self.config.max_risk_score
        }
    
    def set_environment_threshold(
        self,
        environment_name: str,
        thresholds: Dict[str, float]
    ):
        """Set custom thresholds for an environment"""
        if environment_name not in self.config.environment_thresholds:
            self.config.environment_thresholds[environment_name] = {}
        
        self.config.environment_thresholds[environment_name].update(thresholds)

