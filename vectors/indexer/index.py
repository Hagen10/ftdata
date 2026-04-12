import requests
import time
from sentence_transformers import SentenceTransformer

SOLR_UPDATE_URL = "http://solr:8983/solr/vector_test/update?commit=true"
SOLR_PING_URL = "http://solr:8983/solr/vector_test/admin/ping"

# Wait for Solr
def wait_for_solr():
    for i in range(20):
        try:
            r = requests.get(SOLR_PING_URL)
            if r.status_code == 200:
                print("Solr is ready")
                return
        except:
            pass
        print(f"Waiting for Solr... ({i+1}/20)")
        time.sleep(2)
    raise RuntimeError("Solr not ready")

wait_for_solr()

# Load embedding model (same as API)
model = SentenceTransformer('all-MiniLM-L6-v2')

# Test dataset
documents = [
    {"id": "1", "title": "Red running shoes"},
    {"id": "2", "title": "Blue sneakers"},
    {"id": "3", "title": "Trail running shoes"},
    {"id": "4", "title": "Gaming laptop"},
    {"id": "5", "title": "Ultrabook laptop"},
    {"id": "6", "title": "Macbook computer"},
    {"id": "7", "title": "Banana fruit"},
    {"id": "8", "title": "Fresh apple"},
    {"id": "9", "title": "Orange juice"},
]

# Generate embeddings
texts = [doc["title"] for doc in documents]
embeddings = model.encode(texts)

# Attach embeddings
for doc, emb in zip(documents, embeddings):
    doc["embedding"] = emb.tolist()

# Clear existing data (optional but useful for dev)
requests.post(
    SOLR_UPDATE_URL,
    json={"delete": {"query": "*:*"}},
)

# Index documents
response = requests.post(
    SOLR_UPDATE_URL,
    json=documents,
    headers={"Content-Type": "application/json"}
)

print("Indexing response:", response.status_code, response.text)
print("Done indexing!")