#!/usr/bin/env python3
"""
End-to-end tests for the vector search API against fixture data.

The test suite is self-contained: fixture constants mirror
ftdata/vectors/test/fixtures/ so every assertion is deterministic.

Prerequisites (handled by docker-compose vector-test profile):
  - Solr running and fixture data indexed (indexer-test service)
  - API running and pointing at that Solr (api-test service)

Run manually:
  API_URL=http://localhost:8000 python3 test_search.py
"""

import os
import sys
import requests

API_URL = os.getenv("API_URL", "http://api-test:8000")
SEARCH  = f"{API_URL}/search"

# ── Fixture constants (must match fixtures/ XML files) ───────────────────────
SPEAKER_A = "Anna Hansen"   # party A, present in both 20151 and 20171 sessions
PARTY_A   = "A"
SPEAKER_B = "Bo Pedersen"   # party V, present only in 20151 session
PARTY_B   = "V"
YEAR_A = "1526"
YEAR_B = "1527"

EXPECTED_FIELDS = {"speaker_name_s", "party_s", "meeting_date_dt", "text_t", "score"}

GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"
passed = 0
failed = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global passed, failed
    if condition:
        passed += 1
        print(f"  {GREEN}PASS{RESET}  {label}")
    else:
        failed += 1
        print(f"  {RED}FAIL{RESET}  {label}" + (f"  — {detail}" if detail else ""))


def search(query: str, **kwargs) -> dict:
    payload = {"query": query, **kwargs}
    r = requests.post(SEARCH, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()


# ── 1. API reachable ──────────────────────────────────────────────────────────

print("\n=== 1. API reachable ===")
try:
    r = requests.post(SEARCH, json={"query": "test"}, timeout=10)
    check("POST /search returns 200", r.status_code == 200, f"got {r.status_code}")
except Exception as e:
    check("POST /search returns 200", False, str(e))
    print("\nCannot reach the API — are the containers running?")
    sys.exit(1)


# ── 2. Response schema ────────────────────────────────────────────────────────

print("\n=== 2. Response schema ===")
res  = search("klima og miljø", top_k=5)
docs = res.get("docs", [])
check("Search returns documents",      len(docs) > 0, f"got {len(docs)}")
check("Response includes num_found",   "num_found" in res)
if docs:
    missing = EXPECTED_FIELDS - docs[0].keys()
    check("All expected fields present", not missing, f"missing: {missing}")


# ── 3. Filters (each independent, uses fixture constants) ─────────────────────
#
# Pattern: search with a broad query + one filter, assert every returned
# document satisfies that filter.  No dependency on test 2 results.

print("\n=== 3. Filters ===")

filter_cases = [
    (
        "speaker",
        {"speaker": SPEAKER_A},
        lambda d: d.get("speaker_name_s") == SPEAKER_A,
        f"speaker_name_s == '{SPEAKER_A}'",
    ),
    (
        "party",
        {"party": PARTY_B},
        lambda d: d.get("party_s") == PARTY_B,
        f"party_s == '{PARTY_B}'",
    ),
    (
        "date range",
        {
            "date_from": f"{YEAR_A}-01-01T00:00:00Z",
            "date_to":   f"{YEAR_A}-12-31T23:59:59Z",
        },
        lambda d: d.get("meeting_date_dt", "").startswith(YEAR_A),
        f"meeting_date_dt starts with '{YEAR_A}'",
    ),
]

for name, filters, predicate, description in filter_cases:
    fdocs = search("politik Danmark", top_k=50, **filters).get("docs", [])
    check(f"{name}: returns at least one result", len(fdocs) > 0, "no docs returned")
    if fdocs:
        violations = [d for d in fdocs if not predicate(d)]
        check(
            f"{name}: all results satisfy {description}",
            not violations,
            str([d.get("speaker_name_s") or d.get("party_s") or d.get("meeting_date_dt") for d in violations]),
        )


# ── 4. Combined filters (speaker + date range) ────────────────────────────────

print("\n=== 4. Combined filters ===")
combined = search(
    "miljø og grøn omstilling",
    speaker=SPEAKER_A,
    date_from=f"{YEAR_B}-01-01T00:00:00Z",
    date_to=f"{YEAR_B}-12-31T23:59:59Z",
    top_k=20,
).get("docs", [])

check("Combined speaker+date returns results", len(combined) > 0, f"got {len(combined)}")
if combined:
    bad_speaker = [d["speaker_name_s"] for d in combined if d.get("speaker_name_s") != SPEAKER_A]
    bad_year    = [d["meeting_date_dt"] for d in combined if not d.get("meeting_date_dt", "").startswith(YEAR_B)]
    check(f"All docs match speaker '{SPEAKER_A}'",  not bad_speaker, str(bad_speaker))
    check(f"All docs fall within {YEAR_B}",      not bad_year,    str(bad_year))

    if not bad_speaker and not bad_year:
        print(f"\n  Sample: '{SPEAKER_A}' on grøn omstilling in {YEAR_B}:")
        for d in combined[:3]:
            snippet = d.get("text_t", "")[:120].replace("\n", " ")
            print(f"    {d.get('meeting_date_dt', '?')[:10]}  [{d.get('party_s', '?')}]  {snippet}...")


# ── Summary ───────────────────────────────────────────────────────────────────

print(f"\n{'='*50}")
print(f"  {passed} passed, {failed} failed")
print(f"{'='*50}\n")

sys.exit(1 if failed else 0)
