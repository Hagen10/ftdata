import os
import glob
import time
import requests
import spacy
from xml.etree import ElementTree as ET
from sentence_transformers import SentenceTransformer

SOLR_UPDATE_URL = os.getenv("SOLR_UPDATE_URL", "http://solr:8983/solr/vector_test/update?commit=true")
SOLR_PING_URL   = os.getenv("SOLR_PING_URL",   "http://solr:8983/solr/vector_test/admin/ping")
DATA_DIR        = os.getenv("DATA_DIR", "/data")
BATCH_SIZE      = 50   # documents per Solr POST
MAX_TOKENS      = 400  # leave headroom below the 512-token model limit
OVERLAP_SENTS   = 2    # sentences to carry over into the next chunk
MODEL_NAME      = "paraphrase-multilingual-MiniLM-L12-v2"

BANNED_TEXT = {
    "",
    "Ordføreren.",
    "Værsgo.",
    "Spørgeren."
}

# Load Danish sentence splitter (download: python -m spacy download da_core_news_sm)
try:
    nlp = spacy.load("da_core_news_sm", disable=["ner", "tagger", "parser", "lemmatizer"])
    nlp.enable_pipe("senter")  # fast sentence segmenter
except OSError:
    # Fallback: use the blank tokeniser with sentencizer
    nlp = spacy.blank("da")
    nlp.add_pipe("sentencizer")


def wait_for_solr(retries=20, delay=3):
    for i in range(retries):
        try:
            r = requests.get(SOLR_PING_URL, timeout=5)
            if r.status_code == 200:
                print("Solr is ready")
                return
        except Exception:
            pass
        print(f"Waiting for Solr... ({i + 1}/{retries})")
        time.sleep(delay)
    raise RuntimeError("Solr did not become ready in time")


def collect_char_text(element) -> str:
    """Join all <Char> text nodes inside an element, normalising whitespace."""
    parts = []
    for char in element.iter("Char"):
        if char.text:
            parts.append(char.text.strip())
    return " ".join(parts)


def parse_meeting_file(path: str) -> list[dict]:
    """
    Parse one helemoedet XML file and return a list of speech-segment documents.
    Each document maps to one <TaleSegment> — the natural unit to embed.
    """
    tree = ET.parse(path)
    root = tree.getroot()

    # --- meeting-level metadata ---
    meta = root.find("MetaMeeting")
    session      = (meta.findtext("ParliamentarySession") or "").strip()
    meeting_no   = (meta.findtext("MeetingNumber") or "").strip()
    date_raw     = (meta.findtext("DateOfSitting") or "").strip()
    # Solr expects ISO-8601 with Z suffix for pdate
    meeting_date = date_raw.replace(" ", "T") + "Z" if date_raw and not date_raw.endswith("Z") else date_raw

    documents = []
    segment_counter = 0

    for agenda_item in root.iter("DagsordenPunkt"):
        item_no_text = agenda_item.findtext("MetaFTAgendaItem/ItemNo") or ""
        try:
            item_no = int(item_no_text)
        except ValueError:
            item_no = None

        for tale in agenda_item.iter("Tale"):
            # --- speaker metadata ---
            speaker_meta = tale.find("Taler/MetaSpeakerMP")
            if speaker_meta is not None:
                first   = (speaker_meta.findtext("OratorFirstName") or "").strip()
                last    = (speaker_meta.findtext("OratorLastName") or "").strip()
                party   = (speaker_meta.findtext("GroupNameShort") or "").strip()
                role    = (speaker_meta.findtext("OratorRole") or "").strip()
                speaker = f"{first} {last}".strip()
            else:
                speaker = ""
                party   = ""
                role    = ""

            for segment in tale.iter("TaleSegment"):
                seg_meta   = segment.find("MetaSpeechSegment")
                start_raw  = (seg_meta.findtext("StartDateTime") if seg_meta is not None else "") or ""
                end_raw    = (seg_meta.findtext("EndDateTime")   if seg_meta is not None else "") or ""

                def to_solr_date(s: str) -> str:
                    s = s.strip()
                    if s and not s.endswith("Z"):
                        return s + "Z"
                    return s

                start_dt = to_solr_date(start_raw)
                end_dt   = to_solr_date(end_raw)

                # Collect all text from every TekstGruppe in this segment
                text_parts = []
                for tekstgruppe in segment.iter("TekstGruppe"):
                    chunk = collect_char_text(tekstgruppe)
                    if chunk:
                        text_parts.append(chunk)
                text = " ".join(text_parts).strip()

                normalized = text.lower()
                if not text or normalized in {t.lower() for t in BANNED_TEXT}:
                    continue

                # Split long segments into overlapping chunks
                chunks = chunk_text(text, tokenizer)

                for chunk_idx, chunk in enumerate(chunks):
                    segment_counter += 1
                    doc_id = f"{session}_M{meeting_no}_seg{segment_counter}" + (
                        f"_c{chunk_idx}" if len(chunks) > 1 else ""
                    )

                    doc = {
                        "id":              doc_id,
                        "session_s":       session,
                        "meeting_no_i":    int(meeting_no) if meeting_no.isdigit() else meeting_no,
                        "meeting_date_dt": meeting_date,
                        "speaker_name_s":  speaker,
                        "party_s":         party,
                        "speaker_role_s":  role,
                        "start_dt":        start_dt,
                        "end_dt":          end_dt,
                        "text_t":          chunk,
                    }
                    if item_no is not None:
                        doc["agenda_item_i"] = item_no
                    documents.append(doc)

    return documents


def chunk_text(text: str, tokenizer) -> list[str]:
    """
    Split text into chunks of at most MAX_TOKENS tokens using sentence boundaries.
    Adjacent chunks overlap by OVERLAP_SENTS sentences so context is not lost
    at chunk boundaries.
    """
    doc = nlp(text)
    sentences = [s.text.strip() for s in doc.sents if s.text.strip()]
    if not sentences:
        return []

    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for sent in sentences:
        sent_tokens = len(tokenizer.encode(sent, add_special_tokens=False))

        if current_tokens + sent_tokens > MAX_TOKENS and current:
            chunks.append(" ".join(current))
            current = current[-OVERLAP_SENTS:] + [sent]
            current_tokens = sum(
                len(tokenizer.encode(s, add_special_tokens=False)) for s in current
            )
        else:
            current.append(sent)
            current_tokens += sent_tokens

    if current:
        chunks.append(" ".join(current))

    return chunks if chunks else [text]


def index_batch(docs: list[dict], model: SentenceTransformer):
    texts      = [d["text_t"] for d in docs]
    embeddings = model.encode(texts, show_progress_bar=False)
    for doc, emb in zip(docs, embeddings):
        doc["embedding"] = emb.tolist()

    resp = requests.post(
        SOLR_UPDATE_URL,
        json=docs,
        headers={"Content-Type": "application/json"},
        timeout=60,
    )
    if resp.status_code != 200:
        print(f"  ERROR {resp.status_code}: {resp.text[:300]}")
    return resp.status_code


# ── main ──────────────────────────────────────────────────────────────────────

wait_for_solr()

model     = SentenceTransformer(MODEL_NAME)
tokenizer = model.tokenizer

xml_files = sorted(glob.glob(os.path.join(DATA_DIR, "**", "*_helemoedet.xml"), recursive=True))
print(f"Found {len(xml_files)} meeting file(s) in {DATA_DIR}")

if not xml_files:
    print("No XML files found — exiting. Mount your _data directory to /data")
    exit(0)

total_indexed = 0

for path in xml_files:
    print(f"Parsing {os.path.basename(path)} ...")
    docs = parse_meeting_file(path)
    print(f"  {len(docs)} speech segments")

    for i in range(0, len(docs), BATCH_SIZE):
        batch = docs[i : i + BATCH_SIZE]
        status = index_batch(batch, model)
        print(f"  Batch {i // BATCH_SIZE + 1}: {status}")
        total_indexed += len(batch)

print(f"\nDone. Indexed {total_indexed} speech segments total.")