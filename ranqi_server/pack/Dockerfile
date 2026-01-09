# Base: Ubuntu 22.04 + CUDA 12.1 runtime + cuDNN 8
FROM nvidia/cuda:12.1.0-cudnn8-runtime-ubuntu22.04

ENV DEBIAN_FRONTEND=noninteractive \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    ffmpeg libsm6 libxext6 libgl1 libglib2.0-0 \
    git ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# Ensure python and pip commands
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 1 \
 && update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1

WORKDIR /app

# Copy only requirements first for better layer caching
COPY recognize/pack/requirements.txt ./requirements.txt

# Install Python deps except torch via requirements (to avoid CPU torch)
RUN pip install --upgrade pip \
 && pip install --no-cache-dir --no-deps -r requirements.txt

# Install PyTorch with CUDA 12.1 wheels
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cu121 \
    torch torchvision torchaudio

# Copy application source
COPY recognize /app/recognize

# Default environment
ENV PYTHONPATH=/app

# Create outputs directories
RUN mkdir -p /app/recognize/outputs /app/recognize/outputs/frames /app/recognize/outputs/clips

# Default command (can be overridden)
CMD ["python", "recognize/main.py"]
