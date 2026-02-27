# Stage 1: Build RL-Env-Studio (React SPA)
FROM node:20-slim AS studio-builder
WORKDIR /app
COPY package.json ./
COPY apps/RL-Env-Studio/package.json apps/RL-Env-Studio/
COPY apps/RL-Env-Studio apps/RL-Env-Studio
RUN cd apps/RL-Env-Studio && npm install && npm run build

# Stage 2: Python API + serve built Studio
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy built RL-Env-Studio from stage 1
COPY --from=studio-builder /app/api/static/studio /app/api/static/studio

# Run test suite before producing artifact (validate Jira workflow + registry)
RUN python -m pytest tests/ -v --tb=short -x

# Create models directory
RUN mkdir -p models/ppo models/dqn models/a2c models/sac

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# Run the application
CMD ["python", "-m", "api.main"]

