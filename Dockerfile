# Use a stable, lightweight Python image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy your repository files into the container
COPY . https://github.com/RohetM/Football.git.

# Install dependencies (ignoring cache to save space)
RUN pip install --no-cache-dir -r requirements.txt

# Hugging Face routes external web traffic to port 7860
EXPOSE 7860
# Expose port 8000 for the internal FastAPI communication
EXPOSE 8000

# Start the Simulator, FastAPI backend, and Streamlit frontend together
CMD ["bash", "-c", "python -m backend.simulator.update_state & uvicorn backend.main:app --host 0.0.0.0 --port 8000 & streamlit run frontend/dashboard.py --server.port 7860 --server.address 0.0.0.0"]