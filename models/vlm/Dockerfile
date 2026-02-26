# Dockerfile for VLM KServe Predictor
FROM python:3.10-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
# Install PyTorch with CUDA support first, then the rest
COPY requirements.txt .
RUN pip install --no-cache-dir torch torchvision --index-url https://download.pytorch.org/whl/cu121 && \
    pip install --no-cache-dir -r requirements.txt

# Copy predictor code
COPY predictor.py .

# Set environment variables
# VLM_MODEL_NAME can be overridden via KServe InferenceService env vars
ENV VLM_MODEL_NAME="Qwen/Qwen3-VL-8B-Instruct-FP8"
ENV PYTHONUNBUFFERED=1

# Expose port (KServe uses port 8080 by default)
EXPOSE 8080

# Run the predictor
CMD ["python", "predictor.py"]
