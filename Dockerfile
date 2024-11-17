# Use Python base image
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install SSH client
RUN apt-get update && apt-get install -y openssh-client

# Copy application files
COPY . /app

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Expose port
EXPOSE 8080

# Run Flask app
CMD ["python", "api.py"]
