import os
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
import requests
from sentence_transformers import SentenceTransformer

app = FastAPI()

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
model = SentenceTransformer(MODEL_NAME)

SOLR_URL = os.getenv("SOLR_URL", "http://solr:8983/solr/vector_test/query")


class SearchRequest(BaseModel):
    query: str
    speaker: Optional[str] = None
    party: Optional[str] = None
    date_from: Optional[str] = None   # ISO date, e.g. 2015-01-01T00:00:00Z
    date_to: Optional[str] = None
    top_k: int = 10


def _build_filter_queries(req: SearchRequest) -> list[str]:
    """Build Solr fq clauses from the optional metadata filters."""
    fqs = []
    if req.speaker:
        fqs.append(f'speaker_name_s:"{req.speaker}"')
    if req.party:
        fqs.append(f'party_s:"{req.party}"')
    if req.date_from or req.date_to:
        lo = req.date_from or "*"
        hi = req.date_to or "*"
        fqs.append(f"meeting_date_dt:[{lo} TO {hi}]")
    return fqs


@app.post("/search")
def search(req: SearchRequest):
    # 1. Embed the query with the same model used at index time
    vector = model.encode(req.query).tolist()
    vector_str = ",".join(map(str, vector))

    # 2. Build Solr KNN query + optional metadata filters
    solr_params: dict = {
        "query": f"{{!knn f=embedding topK={req.top_k}}}[{vector_str}]",
        "fields": "id,speaker_name_s,party_s,speaker_role_s,meeting_date_dt,"
                   "session_s,meeting_no_i,agenda_item_i,start_dt,end_dt,text_t,score",
        "limit": req.top_k,
    }

    fqs = _build_filter_queries(req)
    if fqs:
        solr_params["filter"] = fqs

    # 3. Query Solr
    response = requests.post(
        SOLR_URL,
        json=solr_params,
        timeout=30,
    )

    if response.status_code != 200:
        return {"error": response.text, "status": response.status_code}

    body = response.json()
    docs = body.get("response", {}).get("docs", [])

    return {
        "num_found": body.get("response", {}).get("numFound", 0),
        "docs": docs,
    }