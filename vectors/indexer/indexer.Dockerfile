FROM python:3.11-slim

WORKDIR /app

RUN pip install sentence-transformers requests

COPY vectors/indexer/index.py .

CMD ["python", "index.py"]