FROM python:3.11-slim

WORKDIR /app

RUN pip install sentence-transformers requests spacy && \
    python -m spacy download da_core_news_sm

ENV SENTENCE_TRANSFORMERS_HOME=/model-cache

COPY vectors/indexer/index.py .

CMD ["python", "index.py"]