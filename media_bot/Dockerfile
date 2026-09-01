FROM python:3.12-slim

# Install system dependencies (ffmpeg is required for audio extraction and conversion)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . .

# Create volume for persistent temp downloads if needed
RUN mkdir -p /app/temp_downloads

# Run the bot
CMD ["python", "bot.py"]
