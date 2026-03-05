Azure Refactor + Full CI/CD Automation
You are acting as a Senior Platform Engineer and DevOps Architect.
Your task is to refactor an existing application to support production-grade Azure deployment using GitHub Actions.
The goals:
1. Decouple the ML model from the application code.
2. Containerize app, API, and model services independently.
3. Create infrastructure-as-code for Azure deployment.
4. Securely manage secrets (including Jira config).
5. Create GitHub Actions workflows that build, test, push, and deploy automatically.
You must output:
* Required code refactoring changes
* Folder structure updates
* Dockerfiles
* Infrastructure code (Bicep or Terraform)
* GitHub Actions YAML files
* Environment variable strategy
* Azure configuration steps

Architecture Requirements
We are deploying:
* App Service (UI / orchestration layer)
* API Service
* Model Service (training + inference)
* Azure Container Registry (ACR)
* Azure Container Apps
* Azure Key Vault
* Azure API Management (optional but preferred)
* Azure Monitor + App Insights
All services must:
* Run as separate containers
* Be independently deployable
* Use Managed Identity (no hardcoded credentials)
* Pull secrets from Key Vault at runtime

Model Decoupling Requirements
Refactor the model so that:
* It is removed from application code
* It runs as a standalone microservice
* It exposes REST endpoints:
POST /trainPOST /simulatePOST /predictGET /healthGET /version
The app must call the model using an environment variable:
MODEL_SERVICE_URL
No direct model imports allowed inside app code.

Jira Config Encryption
Requirements:
* Remove all hardcoded Jira credentials
* Store Jira credentials in Azure Key Vault
* Fetch credentials at runtime using Managed Identity
* Implement secure configuration loading
* Use environment-based configuration
* Ensure no secrets appear in repo or logs
 Required Repo Structure
Refactor to:
/app
/api
/model
/infra
/.github/workflows
Each service must include:
* Dockerfile
* requirements.txt or package.json
* health endpoint

GitHub Actions Requirements
Create workflows:
1. infra-deploy.yml
Trigger:
* On push to /infra
* Manual dispatch
Steps:
* Azure login using OIDC
* Validate IaC
* Deploy infrastructure
* Output resource values

2. build-and-deploy.yml
Trigger:
* On push to main
* On PR merge
Stages:
Build:
* Run tests
* Lint
* Security scan
* Build Docker images
* Tag with commit SHA
Push:
* Push images to ACR
Deploy:
* Deploy to Azure Container Apps
* Update container revision
* Inject Key Vault references
* Configure environment variables
* Set traffic routing
Include:
* Separate jobs for app, api, model
* Environment promotion support (dev → staging → prod)

Deployment Requirements
* Zero downtime deployments
* Blue/Green or revision-based traffic shifting
* Rollback strategy included
* Autoscaling configuration
* Health checks configured

Security Requirements
* Use GitHub OIDC federation (no stored Azure secrets)
* Use Managed Identity
* Use RBAC least privilege
* Add container vulnerability scan step
* Disable public access where possible

Observability
* Enable Application Insights
* Enable Azure Monitor logs
* Add structured logging
* Add correlation IDs across services

Deliverables Format
You must output:
1. Updated folder structure
2. Refactored app code changes
3. Model microservice code example
4. Dockerfiles (all services)
5. Bicep or Terraform infra template
6. GitHub Actions YAML (complete)
7. Azure CLI commands needed
8. Required GitHub secrets configuration
9. Step-by-step deployment explanation
Assume:
* Python backend
* FastAPI
* Docker-based deployment
* Azure subscription already exists
Do not give high-level explanation only. Provide concrete files and production-ready code.