"""
FastAPI Backend for RL Hub
Provides endpoints for training, monitoring, and KPI retrieval
"""

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import uvicorn
import json
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from environments import HealthcareRLEnvironment
from portal.environment_registry import get_environment_class, list_all_environments

# Import verifier architecture
from verifiers.verifier_registry import VerifierRegistry, get_verifier
from verifiers.base_verifier import VerifierConfig

# Import observability
from observability.reward_logger import RewardLogger
from observability.action_trace_logger import ActionTraceLogger
from observability.episode_metrics import EpisodeMetricsTracker
from observability.audit_logger import AuditLogger

# Import governance
from governance.safety_guardrails import SafetyGuardrails, SafetyConfig
from governance.risk_thresholds import RiskThresholds, RiskThresholdConfig
from governance.compliance_rules import ComplianceRules

app = FastAPI(title="RL Hub API", version="1.0.0")

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

# CORS middleware
# Allow GitHub Pages and common deployment URLs
# Note: FastAPI CORS doesn't support wildcards, so we allow all origins
# In production, you may want to restrict this to specific domains
allowed_origins = [
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1:8000",
    "https://ranikrishna-coder.github.io",
    "https://rl-hub-api.onrender.com",
]
# Add environment variable for additional origins
if os.getenv("CORS_ORIGINS"):
    allowed_origins.extend(os.getenv("CORS_ORIGINS").split(","))

# For GitHub Pages, we need to allow all origins since we can't predict the exact URL
# In production, you can restrict this by setting CORS_ORIGINS environment variable
cors_origins = os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins if cors_origins != ["*"] else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Training jobs storage (in production, use database)
training_jobs: Dict[str, Dict[str, Any]] = {}

# Observability storage (in production, use database)
reward_loggers: Dict[str, RewardLogger] = {}
action_trace_loggers: Dict[str, ActionTraceLogger] = {}
episode_metrics_trackers: Dict[str, EpisodeMetricsTracker] = {}
audit_loggers: Dict[str, AuditLogger] = {}

# Governance storage
governance_configs: Dict[str, Dict[str, Any]] = {}


class TrainingRequest(BaseModel):
    environment_name: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    algorithm: str = "PPO"
    num_episodes: int = 100
    max_steps: int = 1000
    dataset_url: Optional[str] = None
    verifier_config: Optional[Dict[str, Any]] = None  # Verifier configuration


class TrainingResponse(BaseModel):
    job_id: str
    status: str
    environment_name: str
    message: str


@app.get("/")
async def root():
    """Root endpoint - serves the catalog UI"""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {
        "message": "RL Hub API",
        "version": "1.0.0",
        "endpoints": {
            "catalog": "/ (this page)",
            "simulation_console": "/test-console",
            "environments": "/environments",
            "train": "/train/{environment_name}",
            "kpis": "/kpis/{environment_name}",
            "training_status": "/training/{job_id}",
            "validate": "/validate/{environment_name}",
            "validate_all": "/validate-all",
            "download_model": "/models/{algorithm}/{model_filename}"
        }
    }


@app.get("/config.js")
async def get_config():
    """Serve config.js with API URL"""
    # Get the API URL from environment or use current request host
    api_url = os.getenv("API_URL", "https://rl-hub-api.onrender.com")
    
    # If API_URL is not set, try to construct from request
    # This will be handled by the JavaScript auto-detection
    
    config_content = f"""// API Configuration
// This can be overridden by setting window.API_BASE before loading app.js
window.API_BASE = window.API_BASE || '{api_url}';
console.log('🚀 RL Hub - API Base URL:', window.API_BASE);
"""
    from fastapi.responses import Response
    return Response(content=config_content, media_type="application/javascript")


@app.get("/test-console")
async def test_console(env: Optional[str] = None):
    """Simulation console for any RL environment"""
    static_dir = os.path.join(os.path.dirname(__file__), "static")
    # Use generic simulation console for all environments
    console_path = os.path.join(static_dir, "simulation-console.html")
    if not os.path.exists(console_path):
        # Fallback to old console if new one doesn't exist
        console_path = os.path.join(static_dir, "test-console.html")
    if os.path.exists(console_path):
        return FileResponse(console_path)
    raise HTTPException(status_code=404, detail="Simulation console not found")


@app.get("/environments")
async def list_environments():
    """List all available environments with enhanced metadata"""
    environments = list_all_environments()
    
    # Enhance each environment with actions, state features, and action type
    enhanced_environments = []
    for env_data in environments:
        env_name = env_data["name"]
        enhanced_env = env_data.copy()
        
        try:
            # Get the environment class
            env_class = get_environment_class(env_name)
            if env_class:
                # Extract actions from ACTIONS attribute (some environments use different names)
                actions = []
                if hasattr(env_class, 'ACTIONS'):
                    actions = env_class.ACTIONS
                elif hasattr(env_class, 'PRIORITIES'):  # Some environments use PRIORITIES
                    actions = env_class.PRIORITIES
                elif hasattr(env_class, 'INTERVENTIONS'):  # Some use INTERVENTIONS
                    actions = env_class.INTERVENTIONS
                elif hasattr(env_class, 'STRATA'):  # Some use STRATA
                    actions = env_class.STRATA
                
                if actions:
                    enhanced_env["actions"] = actions
                    enhanced_env["actionSpace"] = len(actions)
                else:
                    # Try to get from action_space if available
                    if hasattr(env_class, 'action_space'):
                        action_space = env_class.action_space
                        if hasattr(action_space, 'n'):
                            enhanced_env["actionSpace"] = action_space.n
                            enhanced_env["actions"] = [f"action_{i}" for i in range(action_space.n)]
                        else:
                            enhanced_env["actions"] = []
                            enhanced_env["actionSpace"] = "N/A"
                    else:
                        enhanced_env["actions"] = []
                        enhanced_env["actionSpace"] = "N/A"
                
                # Extract state features count from observation_space
                if hasattr(env_class, 'observation_space'):
                    obs_space = env_class.observation_space
                    if hasattr(obs_space, 'shape'):
                        enhanced_env["stateFeatures"] = obs_space.shape[0] if len(obs_space.shape) > 0 else "N/A"
                    else:
                        enhanced_env["stateFeatures"] = "N/A"
                else:
                    enhanced_env["stateFeatures"] = "N/A"
                
                # Determine action type from action_space
                if hasattr(env_class, 'action_space'):
                    action_space = env_class.action_space
                    if hasattr(action_space, '__class__'):
                        action_type_name = action_space.__class__.__name__
                        if 'Discrete' in action_type_name:
                            enhanced_env["actionType"] = "Discrete"
                        elif 'Box' in action_type_name:
                            enhanced_env["actionType"] = "Continuous"
                        elif 'MultiDiscrete' in action_type_name:
                            enhanced_env["actionType"] = "Multi-Discrete"
                        else:
                            enhanced_env["actionType"] = "Discrete"  # Default
                    else:
                        enhanced_env["actionType"] = "Discrete"
                else:
                    enhanced_env["actionType"] = "Discrete"
            else:
                # Fallback if class can't be loaded
                enhanced_env["actions"] = []
                enhanced_env["actionSpace"] = "N/A"
                enhanced_env["stateFeatures"] = "N/A"
                enhanced_env["actionType"] = "Discrete"
        except Exception as e:
            # If there's an error loading the class, use defaults
            enhanced_env["actions"] = []
            enhanced_env["actionSpace"] = "N/A"
            enhanced_env["stateFeatures"] = "N/A"
            enhanced_env["actionType"] = "Discrete"
        
        enhanced_environments.append(enhanced_env)
    
    return {
        "count": len(enhanced_environments),
        "environments": enhanced_environments
    }


@app.post("/train/{environment_name}", response_model=TrainingResponse)
async def start_training(
    environment_name: str,
    request: TrainingRequest,
    background_tasks: BackgroundTasks
):
    """Start training for a specific environment"""
    try:
        # Use environment_name from path (more reliable than body)
        final_env_name = environment_name
        
        # Get environment class
        env_class = get_environment_class(final_env_name)
        if env_class is None:
            # Try to get more details about why it failed
            from portal.environment_registry import ENVIRONMENT_REGISTRY
            if final_env_name not in ENVIRONMENT_REGISTRY:
                available = list(ENVIRONMENT_REGISTRY.keys())[:10]
                raise HTTPException(
                    status_code=404, 
                    detail=f"Environment '{final_env_name}' not found in registry. Available: {', '.join(available)}..."
                )
            else:
                class_path = ENVIRONMENT_REGISTRY[final_env_name].get("class_path", "unknown")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to load environment class for '{final_env_name}'. Class path: {class_path}. Check that the environment file exists and the class name is correct."
                )
        
        # Create job ID
        import uuid
        job_id = str(uuid.uuid4())
        
        # Create models directory if it doesn't exist
        models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", request.algorithm.lower())
        os.makedirs(models_dir, exist_ok=True)
        
        # Model path
        model_filename = f"{final_env_name}_{job_id}.zip"
        model_path = os.path.join(models_dir, model_filename)
        
        # Store job info
        training_jobs[job_id] = {
            "job_id": job_id,
            "environment_name": final_env_name,
            "status": "running",
            "algorithm": request.algorithm,
            "num_episodes": request.num_episodes,
            "progress": 0,
            "results": None,
            "model_path": model_path,
            "model_url": f"/models/{request.algorithm.lower()}/{model_filename}",
            "dataset_url": request.dataset_url
        }
        
        # Start training in background
        background_tasks.add_task(
            run_training,
            job_id,
            env_class,
            final_env_name,
            request.config,
            request.algorithm,
            request.num_episodes,
            request.max_steps,
            request.dataset_url,
            model_path,
            request.verifier_config  # Pass verifier config
        )
        
        return TrainingResponse(
            job_id=job_id,
            status="running",
            environment_name=final_env_name,
            message=f"Training started for {final_env_name}"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_detail = f"{str(e)}\n{traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


def run_training(
    job_id: str,
    env_class: type,
    environment_name: str,
    config: Optional[Dict[str, Any]],
    algorithm: str,
    num_episodes: int,
    max_steps: int,
    dataset_url: Optional[str],
    model_path: str,
    verifier_config: Optional[Dict[str, Any]] = None
):
    """Run training in background"""
    try:
        # Download dataset if URL provided
        if dataset_url:
            try:
                import urllib.request
                import tempfile
                dataset_path = os.path.join(tempfile.gettempdir(), f"dataset_{job_id}.csv")
                urllib.request.urlretrieve(dataset_url, dataset_path)
                training_jobs[job_id]["dataset_path"] = dataset_path
            except Exception as e:
                training_jobs[job_id]["dataset_error"] = f"Failed to download dataset: {str(e)}"
                # Continue without dataset - will use synthetic data
        
        # Validate environment class
        if env_class is None:
            raise ValueError(f"Environment class for {environment_name} is None - check registry")
        
        # Create verifier if config provided
        verifier = None
        if verifier_config:
            try:
                verifier_type = verifier_config.get("type", "ensemble")
                if verifier_type == "ensemble" or verifier_type is None:
                    verifier = VerifierRegistry.create_default_ensemble(
                        configs=verifier_config.get("verifiers", {})
                    )
                else:
                    verifier_config_obj = VerifierConfig(
                        weights=verifier_config.get("weights", {}),
                        thresholds=verifier_config.get("thresholds", {}),
                        enabled=verifier_config.get("enabled", True),
                        metadata=verifier_config.get("metadata", {})
                    )
                    verifier = VerifierRegistry.create_verifier(verifier_type, verifier_config_obj)
            except Exception as e:
                print(f"Warning: Failed to create verifier: {e}, using default")
                verifier = None
        
        # Create environment with error handling
        try:
            # Check if constructor accepts verifier parameter
            import inspect
            sig = inspect.signature(env_class.__init__)
            has_verifier_param = 'verifier' in sig.parameters
            
            # Try with config, max_steps, and verifier
            if verifier is not None and has_verifier_param:
                if config is not None:
                    env = env_class(config=config, max_steps=max_steps, verifier=verifier)
                else:
                    env = env_class(max_steps=max_steps, verifier=verifier)
            elif config is not None:
                try:
                    env = env_class(config=config, max_steps=max_steps)
                except TypeError:
                    env = env_class(config=config)
            else:
                try:
                    env = env_class(max_steps=max_steps)
                except TypeError:
                    env = env_class()
        except Exception as e:
            raise ValueError(f"Failed to instantiate environment {environment_name}: {str(e)}")
        
        # Validate environment has required methods
        if not hasattr(env, 'reset') or not hasattr(env, 'step') or not hasattr(env, 'action_space'):
            raise ValueError(f"Environment {environment_name} does not have required Gymnasium interface")
        
        # Simple training loop (in production, use stable-baselines3 or similar)
        total_rewards = []
        consecutive_errors = 0
        # Allow up to 20% of episodes to fail (min 10, max 50); also stop on 10+ consecutive failures
        max_total_errors = min(50, max(10, int(0.20 * num_episodes)))
        for episode in range(num_episodes):
            try:
                # Reset environment
                reset_result = env.reset()
                if isinstance(reset_result, tuple):
                    state, info = reset_result
                else:
                    state = reset_result
                    info = {}
                
                episode_reward = 0.0
                episode_steps = 0
                
                for step in range(max_steps):
                    # Sample action from action space
                    try:
                        action = env.action_space.sample()
                    except Exception as e:
                        raise ValueError(f"Failed to sample action from action space: {str(e)}")
                    
                    # Take step
                    try:
                        step_result = env.step(action)
                        if len(step_result) == 5:
                            state, reward, terminated, truncated, info = step_result
                        elif len(step_result) == 4:
                            # Older Gym API
                            state, reward, done, info = step_result
                            terminated = done
                            truncated = False
                        else:
                            raise ValueError(f"Unexpected step result format: {len(step_result)} values")
                    except Exception as e:
                        raise ValueError(f"Environment step failed: {str(e)}")
                    
                    episode_reward += float(reward)
                    episode_steps += 1
                    
                    if terminated or truncated:
                        break
                
                total_rewards.append(episode_reward)
                consecutive_errors = 0  # Reset on successful episode
                training_jobs[job_id]["progress"] = int((episode + 1) / num_episodes * 100)
                
                # Update progress every 10 episodes or at the end
                if (episode + 1) % 10 == 0 or (episode + 1) == num_episodes:
                    training_jobs[job_id]["current_episode"] = episode + 1
                    training_jobs[job_id]["avg_reward_so_far"] = sum(total_rewards) / len(total_rewards) if total_rewards else 0.0
                    
            except Exception as episode_error:
                # Log episode error but continue training
                consecutive_errors += 1
                error_msg = str(episode_error)
                print(f"Error in episode {episode + 1} for {environment_name}: {error_msg}")
                training_jobs[job_id]["episode_errors"] = training_jobs[job_id].get("episode_errors", [])
                training_jobs[job_id]["episode_errors"].append({
                    "episode": episode + 1,
                    "error": error_msg
                })
                # Use zero reward for failed episode
                total_rewards.append(0.0)
                training_jobs[job_id]["progress"] = int((episode + 1) / num_episodes * 100)
                
                # Stop on too many consecutive errors (sustained failure) or if total errors exceed cap
                if consecutive_errors > 10:
                    raise ValueError(f"Too many consecutive episode errors ({consecutive_errors}). Last error: {error_msg}")
                if len(training_jobs[job_id]["episode_errors"]) > max_total_errors:
                    raise ValueError(f"Too many total episode errors (>{max_total_errors}). Last error: {error_msg}")
        
        # Calculate final statistics
        if len(total_rewards) > 0:
            mean_reward = sum(total_rewards) / len(total_rewards)
            max_reward = max(total_rewards)
            min_reward = min(total_rewards)
        else:
            mean_reward = 0.0
            max_reward = 0.0
            min_reward = 0.0
        
        # Save model metadata
        model_metadata = {
            "job_id": job_id,
            "environment_name": environment_name,
            "algorithm": algorithm,
            "num_episodes": num_episodes,
            "mean_reward": mean_reward,
            "max_reward": max_reward,
            "min_reward": min_reward,
            "total_episodes_completed": len(total_rewards),
            "training_completed": True,
            "timestamp": str(os.path.getmtime(__file__) if os.path.exists(__file__) else "")
        }
        
        # Ensure models directory exists
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        metadata_path = model_path.replace(".zip", "_metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(model_metadata, f, indent=2)
        
        # Store results
        training_jobs[job_id]["status"] = "completed"
        training_jobs[job_id]["results"] = {
            "mean_reward": mean_reward,
            "max_reward": max_reward,
            "min_reward": min_reward,
            "total_episodes": num_episodes,
            "episodes_completed": len(total_rewards)
        }
        training_jobs[job_id]["model_saved"] = True
        training_jobs[job_id]["model_metadata"] = model_metadata
        
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        training_jobs[job_id]["status"] = "failed"
        training_jobs[job_id]["error"] = str(e)
        training_jobs[job_id]["error_traceback"] = error_trace
        print(f"Training failed for {environment_name}: {error_trace}")


@app.get("/training/{job_id}")
async def get_training_status(job_id: str):
    """Get training job status"""
    if job_id not in training_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return training_jobs[job_id]


@app.get("/kpis/{environment_name}")
async def get_kpis(
    environment_name: str, 
    episode_id: Optional[int] = None,
    verifier_type: Optional[str] = None,
    verifier_config: Optional[str] = None  # JSON string of verifier config
):
    """Get KPI metrics for an environment"""
    try:
        env_class = get_environment_class(environment_name)
        if env_class is None:
            raise HTTPException(status_code=404, detail=f"Environment {environment_name} not found")
        
        # Parse verifier config if provided
        verifier = None
        if verifier_type or verifier_config:
            try:
                config_dict = json.loads(verifier_config) if verifier_config else {}
                if verifier_type == "ensemble" or verifier_type is None:
                    # Default to ensemble if not specified
                    verifier = VerifierRegistry.create_default_ensemble(
                        configs=config_dict.get("verifiers", {})
                    )
                else:
                    verifier_config_obj = VerifierConfig(
                        weights=config_dict.get("weights", {}),
                        thresholds=config_dict.get("thresholds", {}),
                        enabled=config_dict.get("enabled", True),
                        metadata=config_dict.get("metadata", {})
                    )
                    verifier = VerifierRegistry.create_verifier(verifier_type, verifier_config_obj)
            except Exception as e:
                # If verifier creation fails, use default (environment will create its own)
                print(f"Warning: Failed to create verifier: {e}")
                verifier = None
        
        # Create environment instance with verifier if provided
        try:
            if verifier is not None and hasattr(env_class, '__init__'):
                # Check if constructor accepts verifier parameter
                import inspect
                sig = inspect.signature(env_class.__init__)
                if 'verifier' in sig.parameters:
                    env = env_class(verifier=verifier)
                else:
                    env = env_class()
            else:
                env = env_class()
        except TypeError:
            # Fallback if verifier parameter not supported
            env = env_class()
        
        state, info = env.reset()
        
        # Run a few steps to generate KPIs
        for _ in range(10):
            action = env.action_space.sample()
            state, reward, terminated, truncated, info = env.step(action)
            if terminated or truncated:
                break
        
        # Get KPIs
        kpis = env.get_kpis()
        
        return {
            "environment_name": environment_name,
            "kpis": kpis.__dict__,
            "episode_summary": env.get_episode_summary(),
            "verifier_used": verifier.__class__.__name__ if verifier else "default"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/environment/{environment_name}/metadata")
async def get_environment_metadata(environment_name: str):
    """Get metadata for an environment"""
    try:
        from portal.environment_registry import get_environment_metadata
        metadata = get_environment_metadata(environment_name)
        if metadata is None:
            raise HTTPException(status_code=404, detail=f"Environment {environment_name} not found")
        return metadata
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/{algorithm}/{model_filename}")
async def download_model(algorithm: str, model_filename: str):
    """Download a trained model"""
    models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models", algorithm.lower())
    model_path = os.path.join(models_dir, model_filename)
    
    if not os.path.exists(model_path):
        # Try metadata file
        metadata_path = model_path.replace(".zip", "_metadata.json")
        if os.path.exists(metadata_path):
            return FileResponse(metadata_path, media_type="application/json")
        raise HTTPException(status_code=404, detail="Model not found")
    
    return FileResponse(model_path, media_type="application/zip", filename=model_filename)


@app.get("/validate/{environment_name}")
async def validate_environment(environment_name: str):
    """Validate that an environment can be loaded and instantiated"""
    try:
        env_class = get_environment_class(environment_name)
        if env_class is None:
            return {
                "valid": False,
                "environment_name": environment_name,
                "error": "Environment class not found in registry"
            }
        
        # Try to instantiate
        try:
            env = env_class()
        except TypeError:
            try:
                env = env_class(max_steps=1000)
            except Exception as e:
                return {
                    "valid": False,
                    "environment_name": environment_name,
                    "error": f"Failed to instantiate: {str(e)}"
                }
        except Exception as e:
            return {
                "valid": False,
                "environment_name": environment_name,
                "error": f"Failed to instantiate: {str(e)}"
            }
        
        # Try to reset
        try:
            reset_result = env.reset()
            if isinstance(reset_result, tuple):
                state, info = reset_result
            else:
                state = reset_result
                info = {}
        except Exception as e:
            return {
                "valid": False,
                "environment_name": environment_name,
                "error": f"Failed to reset: {str(e)}"
            }
        
        # Try to take a step
        try:
            action = env.action_space.sample()
            step_result = env.step(action)
            if len(step_result) not in [4, 5]:
                return {
                    "valid": False,
                    "environment_name": environment_name,
                    "error": f"Step returned {len(step_result)} values, expected 4 or 5"
                }
        except Exception as e:
            return {
                "valid": False,
                "environment_name": environment_name,
                "error": f"Failed to step: {str(e)}"
            }
        
        return {
            "valid": True,
            "environment_name": environment_name,
            "observation_space": str(env.observation_space),
            "action_space": str(env.action_space),
            "message": "Environment is valid and ready for training"
        }
        
    except Exception as e:
        import traceback
        return {
            "valid": False,
            "environment_name": environment_name,
            "error": str(e),
            "traceback": traceback.format_exc()
        }


@app.get("/validate-all")
async def validate_all_environments():
    """Validate all environments can be loaded"""
    all_envs = list_all_environments()
    results = []
    
    for env_data in all_envs:
        env_name = env_data["name"]
        validation = await validate_environment(env_name)
        results.append(validation)
    
    valid_count = sum(1 for r in results if r.get("valid", False))
    failed_count = len(results) - valid_count
    
    return {
        "total": len(results),
        "valid": valid_count,
        "failed": failed_count,
        "results": results
    }


# ============================================================================
# VERIFIER ARCHITECTURE ENDPOINTS
# ============================================================================

@app.get("/verifiers")
async def list_verifiers():
    """List all available verifier types"""
    verifier_types = VerifierRegistry.list_verifier_types()
    instances = VerifierRegistry.list_instances()
    
    return {
        "verifier_types": verifier_types,
        "instances": instances,
        "count": len(instances)
    }


class VerifierConfigRequest(BaseModel):
    """Request model for verifier configuration"""
    verifier_type: str
    environment_name: str
    weights: Dict[str, float]
    thresholds: Optional[Dict[str, float]] = None
    enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None


@app.post("/verifiers/configure")
async def configure_verifier(request: VerifierConfigRequest):
    """Configure a verifier for an environment"""
    try:
        config = VerifierConfig(
            weights=request.weights,
            thresholds=request.thresholds or {},
            enabled=request.enabled,
            metadata=request.metadata or {}
        )
        
        verifier = VerifierRegistry.create_verifier(
            verifier_type=request.verifier_type,
            config=config,
            instance_id=f"{request.environment_name}_{request.verifier_type}"
        )
        
        return {
            "success": True,
            "verifier_type": request.verifier_type,
            "environment_name": request.environment_name,
            "instance_id": f"{request.environment_name}_{request.verifier_type}",
            "config": {
                "weights": request.weights,
                "thresholds": request.thresholds,
                "enabled": request.enabled
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/episodes/{episode_id}/reward-breakdown")
async def get_reward_breakdown(episode_id: str):
    """Get reward breakdown for an episode"""
    # Find reward logger for this episode
    # In production, this would query the database
    for logger in reward_loggers.values():
        breakdown = logger.get_reward_breakdown(episode_id, 0)  # Get first step as example
        if breakdown:
            episode_logs = logger.get_episode_rewards(episode_id)
            return {
                "episode_id": episode_id,
                "total_steps": len(episode_logs),
                "reward_breakdowns": [
                    {
                        "step_id": log.step_id,
                        "reward": log.reward,
                        "breakdown": log.reward_breakdown,
                        "verifier": log.verifier_name
                    }
                    for log in episode_logs
                ],
                "summary": logger.get_episode_summary(episode_id)
            }
    
    raise HTTPException(status_code=404, detail=f"Episode {episode_id} not found")


@app.get("/episodes/{episode_id}/audit-log")
async def get_audit_log(episode_id: str):
    """Get audit log for an episode"""
    # Find audit logger for this episode
    for logger in audit_loggers.values():
        audit_log = logger.get_episode_audit_log(episode_id)
        if audit_log:
            return {
                "episode_id": episode_id,
                "events": [
                    {
                        "event_type": log.event_type.value,
                        "message": log.message,
                        "details": log.details,
                        "timestamp": log.timestamp.isoformat(),
                        "step_id": log.step_id
                    }
                    for log in audit_log
                ]
            }
    
    raise HTTPException(status_code=404, detail=f"Audit log for episode {episode_id} not found")


@app.get("/environments/{environment_name}/risk-report")
async def get_risk_report(environment_name: str):
    """Get risk report for an environment"""
    try:
        # Get risk thresholds
        risk_thresholds = RiskThresholds()
        
        # Get compliance violations
        compliance_rules = ComplianceRules()
        violations = compliance_rules.get_violations(environment_name=environment_name)
        
        return {
            "environment_name": environment_name,
            "risk_thresholds": {
                "max_risk_score": risk_thresholds.config.max_risk_score,
                "critical_threshold": risk_thresholds.config.critical_risk_threshold,
                "warning_threshold": risk_thresholds.config.warning_risk_threshold
            },
            "compliance_violations": {
                "total": len(violations),
                "by_severity": {
                    "critical": len([v for v in violations if v.get('severity') == 'critical']),
                    "error": len([v for v in violations if v.get('severity') == 'error']),
                    "warning": len([v for v in violations if v.get('severity') == 'warning'])
                },
                "recent_violations": violations[-10:] if len(violations) > 10 else violations
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class GovernanceConfigRequest(BaseModel):
    """Request model for governance configuration"""
    environment_name: str
    max_risk_threshold: float = 0.8
    compliance_hard_stop: bool = True
    human_in_the_loop: bool = False
    override_actions: Optional[Dict[str, str]] = None


@app.post("/governance/configure")
async def configure_governance(request: GovernanceConfigRequest):
    """Configure governance settings for an environment"""
    try:
        safety_config = SafetyConfig(
            max_risk_threshold=request.max_risk_threshold,
            compliance_hard_stop=request.compliance_hard_stop,
            human_in_the_loop=request.human_in_the_loop,
            override_actions=request.override_actions or {}
        )
        
        governance_configs[request.environment_name] = {
            "safety_config": safety_config.__dict__,
            "environment_name": request.environment_name
        }
        
        return {
            "success": True,
            "environment_name": request.environment_name,
            "config": {
                "max_risk_threshold": request.max_risk_threshold,
                "compliance_hard_stop": request.compliance_hard_stop,
                "human_in_the_loop": request.human_in_the_loop
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/governance")
async def get_governance_configs():
    """Get all governance configurations"""
    return {
        "configs": governance_configs,
        "count": len(governance_configs)
    }


if __name__ == "__main__":
    # Allow port to be configured via environment variable (for cloud platforms)
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)

