# vectors/ — Semantic Search over Folketing Debates

Embeds Danish parliamentary debate transcripts into a Solr 9.9 vector index, exposing a
FastAPI search endpoint that supports KNN similarity search with metadata filters
(speaker, party, date range). The intended consumer is the `ftweb-rb` Rails frontend.

## Architecture

```
_data/                       ftdata/vectors/
  20091/                     ┌──────────────────────────────────────────┐
    *_helemoedet.xml ──────▶ │  indexer  (one-shot batch)               │
  20101/                     │  - parses XML  ➜  TaleSegment docs       │
  ...                        │  - chunks long segments (spacy, da)      │
  20241/                     │  - embeds with multilingual MiniLM       │
                             │  - POSTs to Solr in batches of 50        │
                             └────────────────┬─────────────────────────┘
                                              │
                                              ▼
                             ┌──────────────────────────────────────────┐
                             │  solr  (Solr 9.9, core: vector_test)    │
                             │  - DenseVectorField  384-dim  cosine    │
                             │  - metadata fields for filtering        │
                             │  - persistent volume (solr_data)        │
                             └────────────────┬─────────────────────────┘
                                              │
                                              ▼
                             ┌──────────────────────────────────────────┐
                             │  api  (FastAPI on :8000)                 │
                             │  POST /search                            │
                             │  - embeds query with same model          │
                             │  - KNN + optional fq filters ➜ Solr     │
                             │  - returns ranked docs with metadata     │
                             └──────────────────────────────────────────┘
                                              ▲
                                              │
                             ┌──────────────────────────────────────────┐
                             │  ftweb-rb  (future)                      │
                             │  Rails frontend calls POST /search       │
                             └──────────────────────────────────────────┘
```

## Quick start

From the **repository root** (PoliticianTracker/):

```bash
# Start Solr + API + Indexer
make run-vector
make test-vector
```

## Services

### Solr (`solr/`)

| Item | Detail |
|------|--------|
| Image | `solr:9.9.0` |
| Core | `vector_test` |
| Port | `8983` |
| Volume | `solr_data` (named, survives restarts) |

The custom `managed-schema` extends the Solr `_default` configset with:

- A `knn_vector` field type (`solr.DenseVectorField`, 384 dims, cosine similarity)
- An explicit `embedding` field using that type

All metadata fields rely on Solr **dynamic field** naming conventions:

| Field | Type | Purpose |
|-------|------|---------|
| `speaker_name_s` | string | Full name (first + last) |
| `party_s` | string | Party abbreviation (V, S, SF, ...) |
| `speaker_role_s` | string | Role (formand, minister, ordfører, ...) |
| `session_s` | string | Parliamentary session (e.g. `20091`) |
| `meeting_no_i` | pint | Meeting number within session |
| `meeting_date_dt` | pdate | Date of sitting (ISO-8601 + Z) |
| `start_dt` / `end_dt` | pdate | Speech segment start/end time |
| `agenda_item_i` | pint | Agenda item number (omitted when not parseable) |
| `text_t` | text_general | The speech text (chunked) |
| `embedding` | knn_vector | 384-dim float vector |

### Indexer (`indexer/`)

One-shot Python script. Runs once, indexes all `*_helemoedet.xml` files, then exits.

| Item | Detail |
|------|--------|
| Model | `paraphrase-multilingual-MiniLM-L12-v2` (multilingual incl. Danish, 384 dims, 512 token limit) |
| Chunking | Sentence-aware sliding window via spacy `da_core_news_sm`, 400-token limit, 2-sentence overlap |
| Batch size | 50 docs per Solr POST |
| Data mount | `_data/` (repo root) mounted read-only at `/data` |

**XML structure parsed:**

```
<DagsordenPunkt>            ← agenda item
  <Tale>                    ← one speaker's turn
    <Taler><MetaSpeakerMP>  ← name, party, role
    <TaleSegment>           ← one speech block (unit of embedding)
      <MetaSpeechSegment>   ← start/end timestamps
      <TekstGruppe>         ← text content in <Char> elements
```

Long segments are split into multiple Solr docs sharing the same metadata.

### API (`api/`)

| Item | Detail |
|------|--------|
| Framework | FastAPI (uvicorn, port 8000) |
| Model | Same as indexer (`paraphrase-multilingual-MiniLM-L12-v2`) |
| Endpoint | `POST /search` |

**Request body:**

```json
{
  "query": "klima og miljø",
  "speaker": "Mette Frederiksen",
  "party": "S",
  "date_from": "2015-01-01T00:00:00Z",
  "date_to": "2020-12-31T23:59:59Z",
  "top_k": 10
}
```

All fields except `query` are optional. Filters are passed as Solr `fq` clauses
(exact match for speaker/party, range for dates) and applied **on top of** the KNN
vector similarity search.

**Response:**

```json
{
  "num_found": 7,
  "docs": [
    {
      "id": "20151_M42_seg318",
      "speaker_name_s": "Mette Frederiksen",
      "party_s": "S",
      "meeting_date_dt": "2015-12-10T13:00:00Z",
      "text_t": "Vi skal sikre en grøn omstilling ...",
      "score": 0.823
    }
  ]
}
```

### Test (`test/`)

Containerised end-to-end test. Hits the live API over the Docker network.

```bash
make test-vector
```

| # | Test | What it proves |
|---|------|---------------|
| 1 | API reachable | Containers wired, network works |
| 2 | Semantic search (no filters) | KNN returns results with all expected fields |
| 3 | Filter by speaker | `speaker_name_s` fq restricts results to one person |
| 4 | Filter by party | `party_s` fq restricts results to one party |
| 5 | Filter by date range | `meeting_date_dt` range fq works (adapts to indexed data) |
| 6 | Speaker + date combined | The "track a politician over time" query works end-to-end |

## File layout

```
vectors/
├── api/
│   ├── api.Dockerfile
│   └── app.py               ← FastAPI search endpoint
├── indexer/
│   ├── indexer.Dockerfile
│   └── index.py              ← XML parser + embedder + Solr loader
├── solr/
│   ├── solr.Dockerfile
│   ├── entrypoint.sh          ← core creation on first start
│   └── config/
│       └── managed-schema     ← schema with DenseVectorField
├── test/
│   └── test.Dockerfile
├── test_search.py             ← end-to-end test script
└── README.md                  ← this file
```

## Data

The XML files live in `_data/` at the repository root (git-ignored). Directory
structure is one folder per parliamentary session:

```
_data/
├── 20091/          ← 109 meeting files
├── 20101/          ← 108
├── ...
└── 20241/          ← (empty — not yet scraped)
```

Total: ~1 558 XML files across 20 sessions (2009–2024).

## Design notes

- **Model choice:** `paraphrase-multilingual-MiniLM-L12-v2` supports 50+ languages
  including Danish, produces 384-dim vectors, fits in ~470 MB RAM, and runs
  comfortably on Apple M1 CPU. It is used in both the indexer and the API so
  query and document vectors live in the same embedding space.

- **Chunking:** Parliamentary speeches can be very long. The indexer uses spacy's
  Danish sentence segmenter to split text at sentence boundaries with a
  400-token ceiling (leaving headroom below the model's 512-token limit).
  Adjacent chunks overlap by 2 sentences so context is not lost at boundaries.

- **Solr KNN + filters:** Solr 9.9's `DenseVectorField` supports approximate KNN
  search via HNSW. Metadata filters (`fq`) are applied as post-filters on the
  KNN candidate set, which is the standard Solr approach. This means the `topK`
  in the KNN query should be set generously when using narrow filters.

## Not yet done

- **ftweb-rb integration:** The Rails app does not yet have a controller/route
  that calls `POST /search`. The API is ready for it.
- **Incremental indexing:** The indexer is one-shot (full re-index). No delta /
  change detection yet.
- **Sessions 20231 and 20241:** XML files for these sessions have not been
  scraped yet (`_data/20231/` and `_data/20241/` are empty).
