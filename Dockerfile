# 1. Base Image
FROM python:3.12-slim

# 2. Install UV (Copy from official image)
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 3. Set Environment Variables
# UV_SYSTEM_PYTHON=1 installs packages to global python (no venv needed in container)
ENV UV_SYSTEM_PYTHON=1
ENV PYTHONUNBUFFERED=1

# 4. Install System Dependencies
# 'curl' is useful for health checks. 
# We don't need ffmpeg for plant images.
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# 5. Set Workdir
WORKDIR /app

# 6. Install Python Dependencies
# We copy requirements first to leverage Docker layer caching
COPY requirements.txt .

# Use 'uv pip install' for blazing fast installs
RUN uv pip install --no-cache -r requirements.txt

# 7. Copy Application Code
COPY . .

# 8. Create Temp Directory (Useful for handling image uploads later)
RUN mkdir -p /app/temp

# 9. Run the App
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]