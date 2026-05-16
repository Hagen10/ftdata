FROM python:3.11-slim

WORKDIR /app

RUN pip install requests

COPY vectors/test/test_search.py .

CMD ["python", "test_search.py"]
