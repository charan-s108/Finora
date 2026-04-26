FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Bake HuggingFace models into image — zero cold-start penalty on Railway
ENV HF_HOME=/app/data/hf_cache
RUN python -c "\
from sentence_transformers import SentenceTransformer, CrossEncoder; \
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2'); \
CrossEncoder('BAAI/bge-reranker-base'); \
print('HF models baked in.')"

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
