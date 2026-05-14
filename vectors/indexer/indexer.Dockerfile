FROM python:3.11-slim

WORKDIR /app

RUN pip install sentence-transformers requests spacy && \
    python -m spacy download da_core_news_sm

COPY vectors/indexer/index.py .

CMD ["python", "index.py"]