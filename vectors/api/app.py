import os
from fastapi import FastAPI
from pydantic import BaseModel
import requests
from sentence_transformers import SentenceTransformer

app = FastAPI()

# Load embedding model (small + fast)
model = SentenceTransformer('all-MiniLM-L6-v2')

SOLR_URL = os.getenv("SOLR_URL", "http://solr:8983/solr/vector_test/query")

class QueryRequest(BaseModel):
    query: str

@app.post("/search")
def search(req: QueryRequest):
    # 1. Convert text → vector
    vector = model.encode(req.query).tolist()

    # 2. Format for Solr
    vector_str = ",".join(map(str, vector))

    # 3. Query Solr
    response = requests.post(
        SOLR_URL,
        json={
            "query": "{!knn f=embedding topK=5}" + f"[{vector_str}]"
        }
    )

    print("STATUS:", response.status_code)
    print("RAW RESPONSE:", response.text[:500])  # print first 500 chars

    return response.json()