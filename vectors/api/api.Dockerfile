FROM python:3.11-slim@sha256:a3ab0b966bc4e91546a033e22093cb840908979487a9fc0e6e38295747e49ac0

WORKDIR /app

# Install CPU-only PyTorch from the official wheel index only for now.
RUN pip install --no-cache-dir \
      --extra-index-url https://download.pytorch.org/whl/cpu \
      torch && \
    pip install --no-cache-dir \
      fastapi uvicorn requests sentence-transformers \
      diskcache \
      "optimum[onnxruntime]>=1.20"

# Cache both sentence-transformers and HuggingFace (NLI) models in the
# bind-mounted /model-cache so they survive container/image rebuilds.
ENV SENTENCE_TRANSFORMERS_HOME=/model-cache \
    HF_HOME=/model-cache/huggingface

COPY vectors/api/app.py .

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]