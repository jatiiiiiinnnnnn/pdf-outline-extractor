FROM --platform=linux/amd64 python:3.9-slim-bullseye


# Install system dependencies
RUN apt-get update && apt-get dist-upgrade -y && \
    apt-get install -y --no-install-recommends \
    poppler-utils \
    tesseract-ocr \
    tesseract-ocr-jpn \
    tesseract-ocr-chi-sim \
    tesseract-ocr-chi-tra \
    tesseract-ocr-kor && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*


# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY main.py .

# Create input and output directories
RUN mkdir -p /app/input /app/output

# Set the default command
CMD ["python", "main.py"]