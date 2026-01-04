# Base image with Node + Python
FROM python:3.11-slim

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y curl build-essential

# Install Node
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs

# Copy backend + install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy frontend and backend
COPY . .

# Build frontend
WORKDIR /app/frontend
RUN npm install
RUN npm run build

# Back to root
WORKDIR /app

# Start server
CMD uvicorn api:app --host 0.0.0.0 --port $PORT

