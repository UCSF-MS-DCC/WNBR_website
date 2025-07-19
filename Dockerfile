# Use a slim, official Python image as a parent image
FROM python:3.11-slim

# Set the working directory in the container
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Install system dependencies if any are needed in the future
# RUN apt-get update && apt-get install -y --no-install-recommends gcc

# Install Python dependencies
# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir gunicorn -r requirements.txt

# Create a non-root user to run the application
RUN addgroup --system app && adduser --system --group app

# Copy the application source code
# Make sure all files (app.py, email_form_handler.py, templates/, etc.) are in the same directory
COPY . .

# Create and set permissions for directories the app writes to
# These will be mounted as volumes in docker-compose
RUN mkdir -p /app/reports /app/static/data /app/data && chown -R app:app /app/reports /app/static/data /app/data
RUN chown -R app:app /app

# Switch to the non-root user
USER app

# Expose the port the app runs on
EXPOSE 5000

# Define the command to run the application using Gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]