#!/usr/bin/env bash
# Run the vector search end-to-end tests in an isolated Docker environment.
#
# Spins up a temporary Solr, indexes the fixture data, starts the API, runs
# the test container, then tears everything down — no docker-compose needed.
#
# Usage:
#   ./test-vector.sh              # from any directory
#   ./test-vector.sh --no-build   # skip image rebuilds (faster re-runs)

set -euo pipefail

FTDATA="$(cd "$(dirname "$0")/.." && pwd)"
FIXTURES="${FTDATA}/vectors/test/fixtures"
MODELS="${FTDATA}/vectors/models"
NETWORK="vector-test-$$"  # unique per invocation so parallel runs don't clash

BUILD=true
if [[ "${1:-}" == "--no-build" ]]; then
    BUILD=false
fi

# ── Image tags ────────────────────────────────────────────────────────────────
IMG_SOLR="ft-solr-test"
IMG_INDEXER="ft-indexer-test"
IMG_API="ft-api-test"
IMG_TEST="ft-vector-test"

# ── Cleanup on exit ───────────────────────────────────────────────────────────
cleanup() {
    echo ""
    echo "==> Cleaning up..."
    docker rm -f "solr-${NETWORK}" "api-${NETWORK}" 2>/dev/null || true
    docker network rm "${NETWORK}" 2>/dev/null || true
}
trap cleanup EXIT

# ── Build images ──────────────────────────────────────────────────────────────
mkdir -p "${MODELS}"
if [[ "${BUILD}" == "true" ]]; then
    echo "==> Building images..."
    docker build -q -t "${IMG_SOLR}"    -f "${FTDATA}/vectors/solr/solr.Dockerfile"       "${FTDATA}"
    docker build -q -t "${IMG_INDEXER}" -f "${FTDATA}/vectors/indexer/indexer.Dockerfile"  "${FTDATA}"
    docker build -q -t "${IMG_API}"     -f "${FTDATA}/vectors/api/api.Dockerfile"          "${FTDATA}"
    docker build -q -t "${IMG_TEST}"    -f "${FTDATA}/vectors/test/test.Containerfile"     "${FTDATA}"
fi

# ── Network ───────────────────────────────────────────────────────────────────
echo "==> Creating network ${NETWORK}..."
docker network create "${NETWORK}" > /dev/null

# ── Solr ──────────────────────────────────────────────────────────────────────
echo "==> Starting Solr..."
docker run -d \
    --name "solr-${NETWORK}" \
    --network "${NETWORK}" \
    "${IMG_SOLR}"

# ── Indexer (runs to completion before API starts) ────────────────────────────
echo "==> Indexing fixture data..."
docker run --rm \
    --network "${NETWORK}" \
    -v "${FIXTURES}:/data:ro" \
    -v "${MODELS}:/model-cache" \
    -e DATA_DIR=/data \
    -e SOLR_UPDATE_URL="http://solr-${NETWORK}:8983/solr/vector_test/update?commit=true" \
    -e SOLR_PING_URL="http://solr-${NETWORK}:8983/solr/vector_test/admin/ping" \
    "${IMG_INDEXER}"

# ── API ───────────────────────────────────────────────────────────────────────
echo "==> Starting API..."
docker run -d \
    --name "api-${NETWORK}" \
    --network "${NETWORK}" \
    -v "${MODELS}:/model-cache" \
    -e SOLR_URL="http://solr-${NETWORK}:8983/solr/vector_test/query" \
    "${IMG_API}"

echo "==> Waiting for API to be ready..."
for i in $(seq 1 30); do
    if docker run --rm --network "${NETWORK}" curlimages/curl:latest \
        -sf "http://api-${NETWORK}:8000/docs" > /dev/null 2>&1; then
        echo "    API is ready."
        break
    fi
    echo "    (${i}/30) waiting..."
    sleep 3
    if [[ $i -eq 30 ]]; then
        echo "API did not become ready in time."
        exit 1
    fi
done

# ── Tests ─────────────────────────────────────────────────────────────────────
echo "==> Running tests..."
docker run --rm \
    --network "${NETWORK}" \
    -e API_URL="http://api-${NETWORK}:8000" \
    "${IMG_TEST}"
