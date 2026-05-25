import os
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
import requests
import numpy as np
from sentence_transformers import SentenceTransformer

app = FastAPI()

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
model = SentenceTransformer(MODEL_NAME)

# Zero-shot NLI for stance detection. Loaded lazily on first call.
NLI_MODEL_NAME = os.getenv(
    "NLI_MODEL_NAME",
    "MoritzLaurer/multilingual-MiniLMv2-L6-mnli-xnli",
)
# Two-stage retrieval knobs: over-fetch min(POOL_MAX, POOL_MULTIPLIER * top_k)
# on-topic segments from Solr, NLI-score them, keep top_k by confidence.
# Segments below CONFIDENCE_THRESHOLD are treated as neutral and excluded
# from stance_summary aggregates.
STANCE_CONFIDENCE_THRESHOLD = float(os.getenv("STANCE_CONFIDENCE_THRESHOLD", "0.55"))
STANCE_POOL_MULTIPLIER = int(os.getenv("STANCE_POOL_MULTIPLIER", "10"))
STANCE_POOL_MAX = int(os.getenv("STANCE_POOL_MAX", "100"))
# NLI cost is ~quadratic in token count; cap input length.
STANCE_TEXT_MAX_CHARS = int(os.getenv("STANCE_TEXT_MAX_CHARS", "1000"))
# In-process cache keyed on (doc_id, subject); doc texts never change.
STANCE_CACHE_SIZE = int(os.getenv("STANCE_CACHE_SIZE", "20000"))
_nli_pipeline = None
_stance_cache: "dict[tuple[str, str], tuple[float, float]]" = {}


def _get_nli():
    global _nli_pipeline
    if _nli_pipeline is None:
        from transformers import pipeline
        _nli_pipeline = pipeline(
            "zero-shot-classification",
            model=NLI_MODEL_NAME,
            device=-1,  # CPU
        )
    return _nli_pipeline


def _stance_scores_with_confidence(
    texts: list[str], subject: str
) -> list[tuple[float, float]]:
    """Return (stance, confidence) per text.

    `stance` is P(støtter) - P(imod) in [-1, +1].
    `confidence` is max(P(støtter), P(imod)) in [0, 1].
    """
    if not texts:
        return []
    nli = _get_nli()
    labels = [f"st\u00f8tter {subject}", f"imod {subject}"]
    truncated = [(t or "")[:STANCE_TEXT_MAX_CHARS] for t in texts]
    results = nli(
        truncated,
        candidate_labels=labels,
        hypothesis_template="Taleren {}.",
        multi_label=True,
    )
    if isinstance(results, dict):
        results = [results]
    out: list[tuple[float, float]] = []
    for r in results:
        score_map = dict(zip(r["labels"], r["scores"]))
        pro = float(score_map.get(labels[0], 0.0))
        con = float(score_map.get(labels[1], 0.0))
        out.append((pro - con, max(pro, con)))
    return out


def _stance_scores_for_docs(
    docs: list[tuple[str, str]], subject: str
) -> dict[str, tuple[float, float]]:
    """Cached stance scoring keyed on doc id. Misses are batched."""
    cached: dict[str, tuple[float, float]] = {}
    missing_ids: list[str] = []
    missing_texts: list[str] = []
    for doc_id, text in docs:
        hit = _stance_cache.get((doc_id, subject))
        if hit is not None:
            cached[doc_id] = hit
        else:
            missing_ids.append(doc_id)
            missing_texts.append(text)
    if missing_texts:
        for doc_id, pair in zip(
            missing_ids,
            _stance_scores_with_confidence(missing_texts, subject),
        ):
            if len(_stance_cache) >= STANCE_CACHE_SIZE:
                _stance_cache.pop(next(iter(_stance_cache)))  # ~FIFO eviction
            _stance_cache[(doc_id, subject)] = pair
            cached[doc_id] = pair
    return cached


def _stance_scores(texts: list[str], subject: str) -> list[float]:
    """Per-text stance score in [-1, +1], no confidence."""
    return [s for s, _ in _stance_scores_with_confidence(texts, subject)]


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
    vector = model.encode(req.query).tolist()
    vector_str = ",".join(map(str, vector))

    solr_params: dict = {
        "query": f"{{!knn f=embedding topK={req.top_k}}}[{vector_str}]",
        "fields": "id,speaker_name_s,party_s,speaker_role_s,meeting_date_dt,"
                   "session_s,meeting_no_i,agenda_item_i,start_dt,end_dt,text_t,score",
        "limit": req.top_k,
    }
    fqs = _build_filter_queries(req)
    if fqs:
        solr_params["filter"] = fqs

    response = requests.post(SOLR_URL, json=solr_params, timeout=30)
    if response.status_code != 200:
        return {"error": response.text, "status": response.status_code}

    body = response.json()
    return {
        "num_found": body.get("response", {}).get("numFound", 0),
        "docs": body.get("response", {}).get("docs", []),
    }


# ── Per-politician discourse-consistency endpoints ────────────────────────────

TIMELINE_FIELDS = (
    "id,speaker_name_s,party_s,speaker_role_s,meeting_date_dt,"
    "session_s,meeting_no_i,agenda_item_i,start_dt,end_dt,text_t,embedding"
)


def _normalize(v):
    arr = np.asarray(v, dtype=np.float32)
    n = float(np.linalg.norm(arr))
    return arr / n if n else arr


def _solr_select(params: dict, timeout: int = 60) -> list[dict]:
    r = requests.post(SOLR_URL, json=params, timeout=timeout)
    r.raise_for_status()
    return r.json().get("response", {}).get("docs", [])


def _strip_embedding(d: dict) -> dict:
    return {k: v for k, v in d.items() if k != "embedding"}


class PoliticianTimelineRequest(BaseModel):
    speaker: str
    query: str
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    limit: int = 5000
    top_k: int = 10
    include_stance: bool = False
    # Noun phrase for the NLI hypothesis "Taleren støtter/imod <subject>".
    # Defaults to `query`.
    stance_subject: Optional[str] = None


class StanceScoreRequest(BaseModel):
    texts: list[str]
    subject: str


@app.post("/stance_score")
def stance_score(req: StanceScoreRequest):
    """Standalone batched NLI stance scorer; returns one score per text."""
    return {"scores": _stance_scores(req.texts, req.subject)}


@app.post("/politician_timeline")
def politician_timeline(req: PoliticianTimelineRequest):
    """Discourse-consistency timeline for one politician on one topic.

    1. Solr KNN (speaker-prefiltered) fetches top-K on-topic segments.
    2. If `include_stance`, over-fetch a pool and NLI-rerank by stance
       confidence to surface *opinionated* moments (not procedural ones).
    3. Anchor = highest topic-similarity segment; report each kept
       segment's similarity to the anchor and ship the embedding so the
       client can re-anchor without a roundtrip.
    """
    qv = _normalize(model.encode(req.query))
    vector_str = ",".join(map(str, qv.tolist()))

    pre_fqs = [f'speaker_name_s:"{req.speaker}"']
    if req.date_from or req.date_to:
        lo = req.date_from or "*"
        hi = req.date_to or "*"
        pre_fqs.append(f"meeting_date_dt:[{lo} TO {hi}]")
    pre_filter = " AND ".join(pre_fqs)

    top_k = max(1, req.top_k)
    pool_k = (
        min(STANCE_POOL_MAX, max(top_k, top_k * STANCE_POOL_MULTIPLIER))
        if req.include_stance else top_k
    )
    # `preFilter=$pf` dodges nested-quote escaping in Solr local-params.
    knn_q = f"{{!knn f=embedding topK={pool_k} preFilter=$pf}}[{vector_str}]"

    # Speaker-on-topic count for the "K af N udtalelser" UI label.
    total = requests.post(
        SOLR_URL,
        json={"query": "*:*", "filter": pre_fqs, "fields": "id", "limit": 0},
        timeout=30,
    ).json().get("response", {}).get("numFound", 0)

    knn_docs = _solr_select({
        "query": knn_q,
        "fields": TIMELINE_FIELDS + ",score",
        "limit": pool_k,
        "params": {"pf": pre_filter},
    })

    scored = []
    for d in knn_docs:
        emb = d.get("embedding")
        if not emb:
            continue
        nemb = _normalize(emb)
        scored.append((float(np.dot(qv, nemb)), d, nemb))

    if not scored:
        return {"num_found": 0, "total_on_topic": int(total), "anchor_id": None, "docs": []}

    stance_subject = (req.stance_subject or req.query).strip()
    pool_size = len(scored)
    scores_by_id: dict[str, tuple[float, float]] = {}
    neutral_frac: Optional[float] = None

    if req.include_stance:
        scores_by_id = _stance_scores_for_docs(
            [(d.get("id") or "", d.get("text_t") or "") for _, d, _ in scored],
            stance_subject,
        )
        neutral_frac = sum(
            1 for _, c in scores_by_id.values() if c < STANCE_CONFIDENCE_THRESHOLD
        ) / pool_size
        if pool_size > top_k:
            # Rerank: keep top_k by (confidence, topic_sim).
            scored.sort(
                key=lambda x: (
                    scores_by_id.get(x[1].get("id") or "", (0.0, 0.0))[1],
                    x[0],
                ),
                reverse=True,
            )
            scored = scored[:top_k]

    scored.sort(key=lambda x: x[0], reverse=True)
    anchor_topic_sim, anchor_doc, anchor_emb = scored[0]
    anchor_id = anchor_doc.get("id")

    out = []
    for topic_sim, d, nemb in scored:
        rec = _strip_embedding(d)
        rec["topic_similarity"] = topic_sim
        rec["similarity"] = float(np.dot(anchor_emb, nemb))
        rec["is_anchor"] = d.get("id") == anchor_id
        rec["embedding"] = nemb.tolist()
        if req.include_stance:
            s, conf = scores_by_id.get(d.get("id") or "", (0.0, 0.0))
            rec["stance"] = float(s)
            rec["stance_confidence"] = float(conf)
        out.append(rec)

    out.sort(key=lambda x: x.get("meeting_date_dt") or "")

    stance_summary = None
    if req.include_stance:
        # Aggregate over confident segments only; neutrals stay in `docs`
        # for transparency but are excluded from mean/std/consistency.
        confident = [
            r["stance"] for r in out
            if r.get("stance_confidence", 0.0) >= STANCE_CONFIDENCE_THRESHOLD
        ]
        arr = np.asarray(confident, dtype=np.float32) if confident else None
        stance_summary = {
            "mean": float(arr.mean()) if arr is not None else None,
            "std": float(arr.std()) if arr is not None else None,
            # std of values in [-1, 1] is bounded by 1, so 1 - std ∈ [0, 1].
            "consistency": float(max(0.0, 1.0 - arr.std())) if arr is not None else None,
            "n_confident": len(confident),
            "n_total": len(out),
            "pool_size": pool_size,
            "neutral_frac_in_pool": neutral_frac,
            "confidence_threshold": STANCE_CONFIDENCE_THRESHOLD,
        }

    return {
        "num_found": len(out),
        "total_on_topic": int(total),
        "anchor_id": anchor_id,
        "stance_subject": stance_subject if req.include_stance else None,
        "stance_summary": stance_summary,
        "docs": out,
    }


class NearestSpeechesRequest(BaseModel):
    doc_id: str
    top_k: int = 5
    exclude_same_speaker: bool = True


@app.post("/nearest_speeches")
def nearest_speeches(req: NearestSpeechesRequest):
    """Most-similar and most-different segments to `doc_id`.

    Two Solr KNN queries: one against +v (most similar) and one against
    -v (most antipodal, since vectors are L2-normalized cosine).
    """
    src_docs = _solr_select({
        "query": f'id:"{req.doc_id}"',
        "fields": TIMELINE_FIELDS,
        "limit": 1,
    }, timeout=30)
    if not src_docs:
        return {"error": "doc not found", "doc_id": req.doc_id}

    src = src_docs[0]
    src_emb_raw = src.get("embedding")
    if not src_emb_raw:
        return {"error": "source doc has no embedding", "doc_id": req.doc_id}
    src_emb = _normalize(src_emb_raw)
    src_speaker = src.get("speaker_name_s")

    pre_fqs = [f'-id:"{req.doc_id}"']
    if req.exclude_same_speaker and src_speaker:
        pre_fqs.append(f'-speaker_name_s:"{src_speaker}"')
    pre_filter = " AND ".join(pre_fqs)

    top_k = max(1, req.top_k)
    sim_vec_str = ",".join(map(str, src_emb.tolist()))
    opp_vec_str = ",".join(map(str, (-src_emb).tolist()))

    def knn(vec_str: str):
        return _solr_select({
            "query": f"{{!knn f=embedding topK={top_k} preFilter=$pf}}[{vec_str}]",
            "fields": TIMELINE_FIELDS,
            "limit": top_k,
            "params": {"pf": pre_filter},
        }, timeout=30)

    sim_docs = knn(sim_vec_str)
    opp_docs = knn(opp_vec_str)

    def pack(docs):
        out = []
        for d in docs:
            emb = d.get("embedding")
            if not emb:
                continue
            sim = float(np.dot(src_emb, _normalize(emb)))
            rec = _strip_embedding(d)
            rec["similarity"] = sim
            out.append(rec)
        return out

    most_similar = pack(sim_docs)
    most_similar.sort(key=lambda r: r["similarity"], reverse=True)
    most_different = pack(opp_docs)
    most_different.sort(key=lambda r: r["similarity"])

    return {
        "source": _strip_embedding(src),
        "most_similar": most_similar,
        "most_different": most_different,
    }