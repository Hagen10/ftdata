# Pin to a manifest-list digest so the FROM layer stays cache-stable across rebuilds.
FROM python:3.11-slim@sha256:a3ab0b966bc4e91546a033e22093cb840908979487a9fc0e6e38295747e49ac0

WORKDIR /app

# Install CPU-only PyTorch from the official wheel index only for now.
RUN pip install --no-cache-dir \
      --extra-index-url https://download.pytorch.org/whl/cpu \
      torch && \
    pip install --no-cache-dir sentence-transformers requests spacy && \
    python -m spacy download da_core_news_sm

ENV SENTENCE_TRANSFORMERS_HOME=/model-cache

COPY vectors/indexer/index.py .

CMD ["python", "index.py"]