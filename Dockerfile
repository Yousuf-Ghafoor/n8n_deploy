# Use Playwright's official Python image (browsers + deps preinstalled)
FROM mcr.microsoft.com/playwright/python:v1.55.0-jammy

# Working directory inside container
WORKDIR /app

# Copy and install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port (match what uvicorn will use)
ENV PORT 10000
EXPOSE 10000

# Run the app with a single worker (recommended when using Playwright)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000", "--workers", "1"]
