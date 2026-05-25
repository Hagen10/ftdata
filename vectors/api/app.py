import os
from typing import Optional
from fastapi import FastAPI
from pydantic import BaseModel
import requests
import numpy as np
import diskcache
from sentence_transformers import SentenceTransformer

app = FastAPI()

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
model = SentenceTransformer(MODEL_NAME)

# Zero-shot NLI for stance detection. Loaded lazily on first call.
# mDeBERTa-v3-base trained on MNLI + XNLI (15 languages including Danish).
# Substantially stronger than MiniLMv2-L6 at the cost of ~3-4x more CPU per
# segment. Combined with int8 ONNX and the disk cache this stays workable
# for pool sizes up to ~30.
NLI_MODEL_NAME = os.getenv(
    "NLI_MODEL_NAME",
    "MoritzLaurer/mDeBERTa-v3-base-mnli-xnli",
)
# ---------------------------------------------------------------------------
# Stance-detection knobs. All overridable via env. Tweak here or in compose.
# ---------------------------------------------------------------------------
# Two-stage retrieval: over-fetch min(POOL_MAX, POOL_MULTIPLIER * top_k)
# on-topic segments from Solr, NLI-score them, keep top_k by margin.
# Segments below CONFIDENCE_THRESHOLD are treated as neutral and excluded
# from stance_summary aggregates.
STANCE_CONFIDENCE_THRESHOLD = float(os.getenv("STANCE_CONFIDENCE_THRESHOLD", "0.40"))
STANCE_POOL_MULTIPLIER = int(os.getenv("STANCE_POOL_MULTIPLIER", "2"))
# Default lowered from 100 → 20: NLI is the dominant cost on cold pages, and
# 20 candidates is enough to surface a few strongly-positioned segments
# without making the page block for tens of seconds per topic.
STANCE_POOL_MAX = int(os.getenv("STANCE_POOL_MAX", "20"))
# NLI cost is ~quadratic in token count; cap input length.
STANCE_TEXT_MAX_CHARS = int(os.getenv("STANCE_TEXT_MAX_CHARS", "1000"))
# Batch size for NLI pipeline calls. Larger = better CPU throughput, more RAM.
NLI_BATCH_SIZE = int(os.getenv("NLI_BATCH_SIZE", "16"))
# Use ONNX Runtime (2-3x faster on CPU vs torch).
NLI_USE_ONNX = os.getenv("NLI_USE_ONNX", "1") == "1"
# Apply dynamic int8 quantization on top of ONNX. Disable for big models
# (e.g. mDeBERTa-base ~1.1GB) when the container memory budget is tight:
# the quantizer keeps both fp32 and int8 copies resident and OOM-kills.
NLI_QUANTIZE = os.getenv("NLI_QUANTIZE", "0") == "1"
# Stance hypothesis labels. Single softmax over {pro, con} (multi_label=False)
# so the two sides compete: wishy-washy speech lands near 0.5/0.5, scoring
# stance ≈ 0 with low margin. Adding a third "neutral" label was tried and
# absorbed almost all mass on general policy speech — not useful.
# {subject} is filled in from the request's stance_subject.
STANCE_LABEL_PRO = os.getenv("STANCE_LABEL_PRO", "st\u00f8tter {subject}")
STANCE_LABEL_CON = os.getenv("STANCE_LABEL_CON", "er imod {subject}")
STANCE_HYPOTHESIS_TEMPLATE = os.getenv("STANCE_HYPOTHESIS_TEMPLATE", "Taleren {}.")

# Persistent stance cache keyed on (doc_id, subject, model). Survives restarts.
STANCE_CACHE_DIR = os.getenv("STANCE_CACHE_DIR", "/model-cache/stance-cache")
STANCE_CACHE_SIZE_BYTES = int(os.getenv("STANCE_CACHE_SIZE_BYTES", str(512 * 1024 * 1024)))
_stance_cache = diskcache.Cache(STANCE_CACHE_DIR, size_limit=STANCE_CACHE_SIZE_BYTES)
_nli_pipeline = None


def _materialize_onnx_nli(target_dir: str) -> None:
    """Materialize an ONNX NLI model (optionally int8-quantized) in `target_dir`.

    Prefers the model's pre-shipped ONNX (export=False) when available on
    the Hub. Re-exporting large architectures (e.g. mDeBERTa-v3 with
    DisentangledSelfAttention) from PyTorch can take many minutes on CPU
    or hang outright, while download+load of pre-exported weights is
    seconds. Falls back to export=True only if no pre-exported variant
    exists.

    Memory note: we drop the in-memory model before invoking the quantizer
    because the quantizer loads its own copy of the fp32 weights, and
    holding both at once is enough to OOM-kill a 2GB container on a ~1GB
    model like mDeBERTa-base. If quantization still fails we keep the
    fp32 ONNX and fall back to it at load time.
    """
    import gc
    from optimum.onnxruntime import ORTModelForSequenceClassification, ORTQuantizer
    from optimum.onnxruntime.configuration import AutoQuantizationConfig
    from transformers import AutoTokenizer

    os.makedirs(target_dir, exist_ok=True)
    try:
        m = ORTModelForSequenceClassification.from_pretrained(NLI_MODEL_NAME, export=False)
        print(f"[stance] using pre-exported ONNX from hub for {NLI_MODEL_NAME}", flush=True)
    except Exception as e:
        print(f"[stance] no pre-exported ONNX ({e}); falling back to torch->ONNX export", flush=True)
        m = ORTModelForSequenceClassification.from_pretrained(NLI_MODEL_NAME, export=True)
    tok = AutoTokenizer.from_pretrained(NLI_MODEL_NAME)
    m.save_pretrained(target_dir)
    tok.save_pretrained(target_dir)
    # Free the fp32 model before quantizing so we don't hold two copies.
    del m
    gc.collect()

    if not NLI_QUANTIZE:
        print("[stance] quantization disabled (NLI_QUANTIZE=0); using fp32 ONNX", flush=True)
        return
    try:
        quantizer = ORTQuantizer.from_pretrained(target_dir)
        qconfig = AutoQuantizationConfig.avx2(is_static=False, per_channel=False)
        quantizer.quantize(save_dir=target_dir, quantization_config=qconfig)
        print("[stance] int8 quantization complete", flush=True)
    except Exception as e:  # noqa: BLE001 - best-effort
        print(f"[stance] quantization failed ({e!r}); will use fp32 ONNX", flush=True)


def _get_nli():
    global _nli_pipeline
    if _nli_pipeline is not None:
        return _nli_pipeline
    from transformers import pipeline
    if NLI_USE_ONNX:
        try:
            from optimum.onnxruntime import ORTModelForSequenceClassification
            from transformers import AutoTokenizer
            onnx_dir = os.path.join(
                os.getenv("HF_HOME", "/model-cache/huggingface"),
                "onnx-int8",
                NLI_MODEL_NAME.replace("/", "__"),
            )
            quantized = os.path.join(onnx_dir, "model_quantized.onnx")
            fp32 = os.path.join(onnx_dir, "model.onnx")
            if not (os.path.isfile(quantized) or os.path.isfile(fp32)):
                print(f"[stance] materializing NLI ONNX in {onnx_dir}", flush=True)
                _materialize_onnx_nli(onnx_dir)
            if os.path.isfile(quantized):
                file_name = "model_quantized.onnx"
            else:
                file_name = "model.onnx"
            print(f"[stance] loading ONNX file {file_name}", flush=True)
            m = ORTModelForSequenceClassification.from_pretrained(
                onnx_dir, file_name=file_name
            )
            tok = AutoTokenizer.from_pretrained(onnx_dir)
            _nli_pipeline = pipeline(
                "zero-shot-classification",
                model=m,
                tokenizer=tok,
                batch_size=NLI_BATCH_SIZE,
            )
            return _nli_pipeline
        except Exception as e:  # noqa: BLE001 - fallback path
            print(f"[stance] ONNX path failed ({e!r}); falling back to torch", flush=True)
    _nli_pipeline = pipeline(
        "zero-shot-classification",
        model=NLI_MODEL_NAME,
        device=-1,
        batch_size=NLI_BATCH_SIZE,
    )
    return _nli_pipeline


def _stance_scores_with_confidence(
    texts: list[str], subject: str
) -> list[tuple[float, float]]:
    """Return (stance, confidence) per text.

    Three-way single-softmax classification: {pro, con, neutral} compete.
    This forces the model to pick a side instead of firing high on both
    pro and con simultaneously (the multi_label=True failure mode).

    `stance`     = P(pro) - P(con) in [-1, +1].
    `confidence` = |P(pro) - P(con)| in [0, 1] (margin between sides).
                   Wishy-washy speech now scores low confidence even when
                   P(neutral) is small.
    """
    if not texts:
        return []
    nli = _get_nli()
    pro = STANCE_LABEL_PRO.format(subject=subject)
    con = STANCE_LABEL_CON.format(subject=subject)
    labels = [pro, con]
    truncated = [(t or "")[:STANCE_TEXT_MAX_CHARS] for t in texts]
    results = nli(
        truncated,
        candidate_labels=labels,
        hypothesis_template=STANCE_HYPOTHESIS_TEMPLATE,
        multi_label=False,
    )
    if isinstance(results, dict):
        results = [results]
    out: list[tuple[float, float]] = []
    for r in results:
        score_map = dict(zip(r["labels"], r["scores"]))
        p_pro = float(score_map.get(pro, 0.0))
        p_con = float(score_map.get(con, 0.0))
        diff = p_pro - p_con
        out.append((diff, abs(diff)))
    return out


def _stance_scores_for_docs(
    docs: list[tuple[str, str]], subject: str
) -> dict[str, tuple[float, float]]:
    """Cached stance scoring keyed on doc id. Misses are batched."""
    cached: dict[str, tuple[float, float]] = {}
    missing_ids: list[str] = []
    missing_texts: list[str] = []
    for doc_id, text in docs:
        hit = _stance_cache.get((doc_id, subject, NLI_MODEL_NAME))
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
            _stance_cache[(doc_id, subject, NLI_MODEL_NAME)] = pair
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
    # Medoid anchor: the segment most central to the kept set (highest mean
    # cosine to its peers) is a stabler reference than argmax-topic-sim,
    # which can be an outlier that warps the similarity axis.
    embs = np.stack([nemb for _, _, nemb in scored])  # already L2-normalised
    centrality = (embs @ embs.T).sum(axis=1)
    anchor_idx = int(np.argmax(centrality))
    anchor_topic_sim, anchor_doc, anchor_emb = scored[anchor_idx]
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