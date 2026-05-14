#!/usr/bin/env python3
"""
End-to-end test for the vector search pipeline.

Prerequisites:
  - Solr + API containers running  (make run-vector)
  - At least one XML file indexed   (indexer container finished)

Run from the host:
  python3 ftdata/vectors/test_search.py

Or with a custom API base URL:
  API_URL=http://localhost:8000 python3 ftdata/vectors/test_search.py
"""

import os
import sys
import json
import requests

API_URL = os.getenv("API_URL", "http://api:8000")
SEARCH  = f"{API_URL}/search"

GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"
passed = 0
failed = 0


def check(label: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  {GREEN}PASS{RESET}  {label}")
    else:
        failed += 1
        print(f"  {RED}FAIL{RESET}  {label}  — {detail}")


# ── Helpers ───────────────────────────────────────────────────────────────────

def search(query: str, **kwargs) -> dict:
    payload = {"query": query, **kwargs}
    r = requests.post(SEARCH, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


# ── 1. Basic connectivity ─────────────────────────────────────────────────────

print("\n=== 1. API reachable ===")
try:
    r = requests.post(SEARCH, json={"query": "test"}, timeout=10)
    check("POST /search returns 200", r.status_code == 200, f"got {r.status_code}")
except Exception as e:
    check("POST /search returns 200", False, str(e))
    print("\nCannot reach the API — are the containers running?")
    sys.exit(1)


# ── 2. Unfiltered semantic query ──────────────────────────────────────────────

print("\n=== 2. Semantic search (no filters) ===")
res = search("klima og miljø")  # "climate and environment"
docs = res.get("docs", [])
check("Returns results for 'klima og miljø'", len(docs) > 0, f"got {len(docs)} docs")
if docs:
    first = docs[0]
    check("Doc has speaker_name_s", "speaker_name_s" in first)
    check("Doc has party_s",        "party_s" in first)
    check("Doc has meeting_date_dt","meeting_date_dt" in first)
    check("Doc has text_t",         "text_t" in first)
    check("Doc has score",          "score" in first)


# ── 3. Filter by speaker ─────────────────────────────────────────────────────

print("\n=== 3. Filter by speaker ===")

# First, grab a known speaker name from the unfiltered results
if docs:
    known_speaker = docs[0]["speaker_name_s"]
    res_speaker = search("klima og miljø", speaker=known_speaker, top_k=20)
    speaker_docs = res_speaker.get("docs", [])
    check(
        f"All results belong to '{known_speaker}'",
        all(d["speaker_name_s"] == known_speaker for d in speaker_docs),
        f"found {[d['speaker_name_s'] for d in speaker_docs if d['speaker_name_s'] != known_speaker]}"
    )
    check("At least one result returned", len(speaker_docs) > 0)
else:
    check("(skipped — no docs from previous step)", False, "no baseline docs")


# ── 4. Filter by party ───────────────────────────────────────────────────────

print("\n=== 4. Filter by party ===")
if docs:
    known_party = docs[0]["party_s"]
    res_party = search("økonomi og skat", party=known_party, top_k=20)   # "economy and tax"
    party_docs = res_party.get("docs", [])
    check(
        f"All results belong to party '{known_party}'",
        all(d["party_s"] == known_party for d in party_docs),
    )
    check("At least one result returned", len(party_docs) > 0)
else:
    check("(skipped — no docs)", False)


# ── 5. Filter by date range ──────────────────────────────────────────────────
#    Use a date from the already-returned docs so the test works regardless of
#    which sessions have been indexed so far.

print("\n=== 5. Filter by date range ===")
if docs:
    # Pick the year of the first result as our known-good range
    sample_date = docs[0].get("meeting_date_dt", "")
    sample_year = sample_date[:4] if sample_date else None

if docs and sample_year:
    range_from = f"{sample_year}-01-01T00:00:00Z"
    range_to   = f"{sample_year}-12-31T23:59:59Z"
    res_date = search(
        "sundhed og hospitalsvæsen",    # "health and hospitals"
        date_from=range_from,
        date_to=range_to,
        top_k=20,
    )
    date_docs = res_date.get("docs", [])
    check(f"Returns results in {sample_year} range", len(date_docs) > 0, f"got {len(date_docs)} docs")
    for d in date_docs:
        dt = d.get("meeting_date_dt", "")
        in_range = dt >= sample_year and dt < str(int(sample_year) + 1)
        if not in_range:
            check(f"Date {dt} within {sample_year}", False, dt)
            break
    else:
        if date_docs:
            check(f"All dates within {sample_year} range", True)
else:
    check("(skipped — no docs to derive date range)", False, "no baseline docs")


# ── 6. Combined: speaker + date (the "track over time" query) ────────────────

print("\n=== 6. Speaker + date range (track stance over time) ===")
if docs:
    # Use a speaker we know exists
    res_combined = search(
        "miljø og grøn omstilling",   # "environment and green transition"
        speaker=known_speaker,
        date_from="2009-01-01T00:00:00Z",
        date_to="2020-12-31T23:59:59Z",
        top_k=20,
    )
    combined_docs = res_combined.get("docs", [])
    check("Combined speaker+date returns results", len(combined_docs) > 0, f"got {len(combined_docs)}")
    if combined_docs:
        check(
            "All docs match the speaker filter",
            all(d["speaker_name_s"] == known_speaker for d in combined_docs),
        )
        # Print a timeline preview
        print(f"\n  Timeline for '{known_speaker}' on 'miljø og grøn omstilling':")
        for d in combined_docs[:5]:
            snippet = d.get("text_t", "")[:120].replace("\n", " ")
            print(f"    {d.get('meeting_date_dt', '?')[:10]}  [{d.get('party_s', '?')}]  {snippet}...")
else:
    check("(skipped)", False)


# ── Summary ───────────────────────────────────────────────────────────────────

print(f"\n{'='*50}")
print(f"  {passed} passed, {failed} failed")
print(f"{'='*50}\n")

sys.exit(1 if failed else 0)
