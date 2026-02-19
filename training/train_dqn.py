"""
DQN Training Script Example
Uses stable-baselines3 for DQN training
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stable_baselines3 import DQN
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
from environments.clinical.sepsis_early_intervention import SepsisEarlyInterventionEnv


def train_dqn(
    environment_name: str = "SepsisEarlyIntervention",
    total_timesteps: int = 100000,
    learning_rate: float = 1e-4,
    buffer_size: int = 100000,
    learning_starts: int = 1000,
    batch_size: int = 32,
    tau: float = 1.0,
    gamma: float = 0.99,
    train_freq: int = 4,
    gradient_steps: int = 1,
    target_update_interval: int = 1000,
    exploration_fraction: float = 0.1,
    exploration_initial_eps: float = 1.0,
    exploration_final_eps: float = 0.05,
    max_grad_norm: float = 10.0,
    tensorboard_log: str = "./logs/dqn/",
    save_path: str = "./models/dqn/"
):
    """
    Train DQN agent on RL environment
    
    Args:
        environment_name: Name of environment to train on
        total_timesteps: Total training timesteps
        learning_rate: Learning rate
        buffer_size: Replay buffer size
        learning_starts: Steps before learning starts
        batch_size: Batch size
        tau: Soft update coefficient
        gamma: Discount factor
        train_freq: Training frequency
        gradient_steps: Gradient steps per update
        target_update_interval: Target network update interval
        exploration_fraction: Exploration fraction
        exploration_initial_eps: Initial exploration epsilon
        exploration_final_eps: Final exploration epsilon
        max_grad_norm: Maximum gradient norm
        tensorboard_log: TensorBoard log directory
        save_path: Model save path
    """
    
    # Create environment
    env = SepsisEarlyInterventionEnv()
    
    # Create vectorized environment
    vec_env = make_vec_env(lambda: SepsisEarlyInterventionEnv(), n_envs=1)
    
    # Create evaluation environment
    eval_env = SepsisEarlyInterventionEnv()
    
    # Create DQN model
    model = DQN(
        "MlpPolicy",
        vec_env,
        learning_rate=learning_rate,
        buffer_size=buffer_size,
        learning_starts=learning_starts,
        batch_size=batch_size,
        tau=tau,
        gamma=gamma,
        train_freq=train_freq,
        gradient_steps=gradient_steps,
        target_update_interval=target_update_interval,
        exploration_fraction=exploration_fraction,
        exploration_initial_eps=exploration_initial_eps,
        exploration_final_eps=exploration_final_eps,
        max_grad_norm=max_grad_norm,
        tensorboard_log=tensorboard_log,
        verbose=1
    )
    
    # Create callbacks
    eval_callback = EvalCallback(
        eval_env,
        best_model_save_path=save_path,
        log_path=save_path,
        eval_freq=5000,
        deterministic=True,
        render=False
    )
    
    checkpoint_callback = CheckpointCallback(
        save_freq=10000,
        save_path=save_path,
        name_prefix="dqn_model"
    )
    
    # Train model
    print(f"Starting DQN training on {environment_name}")
    print(f"Total timesteps: {total_timesteps}")
    
    model.learn(
        total_timesteps=total_timesteps,
        callback=[eval_callback, checkpoint_callback],
        progress_bar=True
    )
    
    # Save final model
    final_model_path = os.path.join(save_path, "dqn_final_model")
    model.save(final_model_path)
    print(f"Training complete. Model saved to {final_model_path}")
    
    # Evaluate model
    print("\nEvaluating trained model...")
    obs = eval_env.reset()[0]
    total_reward = 0.0
    episode_count = 0
    
    for _ in range(10):  # Evaluate for 10 episodes
        done = False
        episode_reward = 0.0
        
        while not done:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = eval_env.step(action)
            episode_reward += reward
            done = terminated or truncated
        
        total_reward += episode_reward
        episode_count += 1
        obs = eval_env.reset()[0]
    
    avg_reward = total_reward / episode_count
    print(f"Average reward over {episode_count} episodes: {avg_reward:.2f}")
    
    return model


if __name__ == "__main__":
    # Example usage
    model = train_dqn(
        environment_name="SepsisEarlyIntervention",
        total_timesteps=100000,
        learning_rate=1e-4
    )

