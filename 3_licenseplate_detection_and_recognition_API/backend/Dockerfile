FROM python:3.10.20-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

WORKDIR /app

# Install system dependencies for OpenCV (added libgl1 and libglx-mesa0)
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgl1 \
    libglx-mesa0 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code and models
COPY app ./app
COPY models ./models

# Start server using standard JSON array syntax to prevent port/shell parsing bugs
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]