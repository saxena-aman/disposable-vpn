# Step 1: Use an official Python image as a base image
FROM python:3.9-slim

# Step 2: Set the working directory inside the container
WORKDIR /app

# Step 3: Copy the requirements.txt into the container
COPY requirements.txt /app/

# Step 4: Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Step 5: Copy the application code into the container
COPY . /app/

# Step 6: Expose the port your Flask app runs on (e.g., 8080)
EXPOSE 8080

# Step 7: Run the Flask application with Python
CMD ["python", "api.py"]
