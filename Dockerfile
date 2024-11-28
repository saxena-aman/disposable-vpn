# Use the slim variant of the official Python image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies for Flask and any additional packages you need
RUN apt-get update && apt-get install -y

# Copy the requirements.txt file to the working directory
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your Flask app code into the container
COPY . .

# Expose the port your app will run on
EXPOSE 8080

# Command to run the Flask app
CMD ["python", "api.py"]
