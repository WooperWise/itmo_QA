FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Make scripts executable
RUN chmod +x split_md.py embedder.py

# Create directories for input and output
RUN mkdir -p pages embeddings data

# Create log file and set permissions
RUN touch embedding.log && chmod 666 embedding.log

# Copy the input markdown file
COPY data.md /app/data/

# Command to run the complete embedding process
CMD ["python", "embedder.py"]