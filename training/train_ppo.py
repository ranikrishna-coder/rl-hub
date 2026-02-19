"""
PPO Training Script Example
Uses stable-baselines3 for PPO training
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import EvalCallback, CheckpointCallback
from environments.clinical.treatment_pathway_optimization import TreatmentPathwayOptimizationEnv


def train_ppo(
    environment_name: str = "TreatmentPathwayOptimization",
    total_timesteps: int = 100000,
    learning_rate: float = 3e-4,
    n_steps: int = 2048,
    batch_size: int = 64,
    n_epochs: int = 10,
    gamma: float = 0.99,
    gae_lambda: float = 0.95,
    clip_range: float = 0.2,
    ent_coef: float = 0.01,
    vf_coef: float = 0.5,
    max_grad_norm: float = 0.5,
    tensorboard_log: str = "./logs/ppo/",
    save_path: str = "./models/ppo/"
):
    """
    Train PPO agent on RL environment
    
    Args:
        environment_name: Name of environment to train on
        total_timesteps: Total training timesteps
        learning_rate: Learning rate
        n_steps: Number of steps per update
        batch_size: Batch size
        n_epochs: Number of epochs per update
        gamma: Discount factor
        gae_lambda: GAE lambda parameter
        clip_range: PPO clip range
        ent_coef: Entropy coefficient
        vf_coef: Value function coefficient
        max_grad_norm: Maximum gradient norm
        tensorboard_log: TensorBoard log directory
        save_path: Model save path
    """
    
    # Create environment
    env = TreatmentPathwayOptimizationEnv()
    
    # Create vectorized environment (for parallel training)
    vec_env = make_vec_env(lambda: TreatmentPathwayOptimizationEnv(), n_envs=4)
    
    # Create evaluation environment
    eval_env = TreatmentPathwayOptimizationEnv()
    
    # Create PPO model
    model = PPO(
        "MlpPolicy",
        vec_env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        batch_size=batch_size,
        n_epochs=n_epochs,
        gamma=gamma,
        gae_lambda=gae_lambda,
        clip_range=clip_range,
        ent_coef=ent_coef,
        vf_coef=vf_coef,
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
        name_prefix="ppo_model"
    )
    
    # Train model
    print(f"Starting PPO training on {environment_name}")
    print(f"Total timesteps: {total_timesteps}")
    
    model.learn(
        total_timesteps=total_timesteps,
        callback=[eval_callback, checkpoint_callback],
        progress_bar=True
    )
    
    # Save final model
    final_model_path = os.path.join(save_path, "ppo_final_model")
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
    model = train_ppo(
        environment_name="TreatmentPathwayOptimization",
        total_timesteps=100000,
        learning_rate=3e-4
    )

