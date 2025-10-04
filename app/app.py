from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import os
import json
import logging
from typing import List, Dict, Any
import subprocess
import time
import socket
from threading import Thread
import http.client

app = FastAPI()

# --- Ollama auto-start logic ---
_ollama_process = None
_ollama_started_here = False

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1")
OLLAMA_PORT = int(os.environ.get("OLLAMA_PORT", "11434"))
OLLAMA_AUTOSTART = os.environ.get("OLLAMA_AUTOSTART", "1") not in ("0", "false", "False")
OLLAMA_COMMAND = os.environ.get("OLLAMA_COMMAND", "ollama serve")
OLLAMA_START_TIMEOUT = float(os.environ.get("OLLAMA_START_TIMEOUT", "60"))
OLLAMA_LAZY_RETRY = os.environ.get("OLLAMA_LAZY_RETRY", "1") not in ("0", "false", "False")

logger = logging.getLogger("nasaSpaceChallenge")  # ensure logger exists early

def _is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False

def _ollama_healthcheck(timeout: float = 0.75) -> bool:
    try:
        conn = http.client.HTTPConnection(OLLAMA_HOST, OLLAMA_PORT, timeout=timeout)
        conn.request("GET", "/api/version")
        resp = conn.getresponse()
        ok = 200 <= resp.status < 300
        conn.close()
        return ok
    except Exception:
        return False

def _ollama_ready() -> bool:
    return _ollama_healthcheck()

def _log_process_pipes(proc: subprocess.Popen, prefix: str):
    def _reader(stream, level):
        if not stream:
            return
        for line in iter(stream.readline, b""):
            if not line:
                break
            try:
                logger.log(level, "%s%s", prefix, line.decode(errors="ignore").rstrip())
            except Exception:
                pass
    Thread(target=_reader, args=(proc.stdout, logging.INFO), daemon=True).start()
    Thread(target=_reader, args=(proc.stderr, logging.WARNING), daemon=True).start()

def _start_ollama_background(block: bool = False):
    global _ollama_process, _ollama_started_here
    if _ollama_ready():
        logger.info("Ollama already responsive at %s:%s", OLLAMA_HOST, OLLAMA_PORT)
        return True
    try:
        logger.info("Starting Ollama server with command: %s", OLLAMA_COMMAND)
        if os.name == 'nt':
            _ollama_process = subprocess.Popen(OLLAMA_COMMAND, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        else:
            # split only when not using shell
            parts = OLLAMA_COMMAND if isinstance(OLLAMA_COMMAND, list) else OLLAMA_COMMAND.split()
            _ollama_process = subprocess.Popen(parts, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        _ollama_started_here = True
        _log_process_pipes(_ollama_process, "[ollama] ")
    except FileNotFoundError:
        logger.error("Ollama command not found. Set OLLAMA_COMMAND env var to full path, e.g. C:/Users/<user>/AppData/Local/Programs/Ollama/ollama.exe serve")
        return False
    except Exception as e:
        logger.error("Failed to launch Ollama: %s", e)
        return False

    if not block:
        # background wait thread just logs readiness
        def _wait():
            deadline = time.time() + OLLAMA_START_TIMEOUT
            while time.time() < deadline:
                if _ollama_ready():
                    logger.info("Ollama became ready.")
                    return
                time.sleep(0.5)
            logger.warning("Ollama did not become ready within %.1fs (non-blocking)", OLLAMA_START_TIMEOUT)
        Thread(target=_wait, daemon=True).start()
        return True

    # blocking wait
    deadline = time.time() + OLLAMA_START_TIMEOUT
    while time.time() < deadline:
        if _ollama_ready():
            logger.info("Ollama ready (blocking wait).")
            return True
        # process crashed?
        if _ollama_process and _ollama_process.poll() is not None:
            logger.error("Ollama process exited early with code %s", _ollama_process.returncode)
            return False
        time.sleep(0.5)
    logger.warning("Ollama did not become ready within %.1fs (blocking)", OLLAMA_START_TIMEOUT)
    return False

@app.on_event("startup")
async def ensure_ollama_running():
    if not OLLAMA_AUTOSTART:
        logger.info("OLLAMA_AUTOSTART disabled; expecting external Ollama server.")
        return
    Thread(target=_start_ollama_background, kwargs={"block": False}, daemon=True).start()

@app.on_event("shutdown")
async def stop_local_ollama():
    global _ollama_process
    if _ollama_process and _ollama_started_here:
        try:
            logger.info("Terminating Ollama process started by this app...")
            _ollama_process.terminate()
            try:
                _ollama_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                logger.info("Ollama did not exit gracefully; killing...")
                _ollama_process.kill()
        except Exception as e:
            logger.warning("Error stopping Ollama: %s", e)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nasaSpaceChallenge")

@app.get("/", response_class=HTMLResponse)
def homepage(request: Request):
    return templates.TemplateResponse("main.html", {"request": request})

@app.get("/search", response_class=JSONResponse)
def search(term: str = Query(..., alias="query", min_length=1, description="Search query string"),
           exact: bool = Query(False, alias="exact", description="If true, return only case-insensitive exact matches")) -> List[Dict[str, Any]]:
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Space challenge", "data.json"))
    if not os.path.exists(data_path):
        logger.error("Data file not found: %s", data_path)
        raise HTTPException(status_code=500, detail=f"Data file not found: {data_path}")

    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.exception("Failed to load JSON from %s", data_path)
        raise HTTPException(status_code=500, detail=f"Failed to read/parse data.json: {e}")

    try:
        def make_excerpt(text: str, q: str, radius: int = 80) -> str:
            if not isinstance(text, str):
                return ""
            lower = text.lower()
            idx = lower.find(q)
            if idx == -1:
                snippet = text[: radius * 2]
            else:
                start = max(0, idx - radius)
                end = min(len(text), idx + len(q) + radius)
                snippet = text[start:end]
            snippet = snippet.strip()
            if len(snippet) < len(text):
                return snippet + "..."
            return snippet

        phrase_results: List[Dict[str, Any]] = []
        word_results: List[Dict[str, Any]] = []
        qlower = term.strip().lower()
        if not isinstance(data, list):
            logger.error("Data file does not contain a list")
            raise HTTPException(status_code=500, detail="Data file format error: expected a list of items")

        words = [w for w in qlower.split() if w]

        def count_occurrences(haystack: str, needle: str) -> int:
            if not needle:
                return 0
            count = 0
            start = 0
            while True:
                idx = haystack.find(needle, start)
                if idx == -1:
                    break
                count += 1
                start = idx + len(needle)
            return count

        for entry in data:
            if not isinstance(entry, dict):
                continue
            name = entry.get("name", "") or ""
            link = entry.get("link", "") or ""

            sections_map = {}
            if isinstance(entry.get("sections"), dict):
                for k, v in entry.get("sections", {}).items():
                    sections_map[str(k)] = str(v) if v is not None else ""
            elif isinstance(entry.get("sections"), list):
                for sec in entry.get("sections", []):
                    if isinstance(sec, dict):
                        title = sec.get("title") or sec.get("name") or "section"
                        body = sec.get("text") or sec.get("body") or ""
                        sections_map[str(title)] = str(body)
                    elif isinstance(sec, str):
                        sections_map[sec] = ""
            if not sections_map and isinstance(entry.get("sectionNames"), list) and isinstance(entry.get("sections"), dict):
                for title in entry.get("sectionNames", []):
                    body = entry.get("sections", {}).get(title, "")
                    sections_map[str(title)] = str(body) if body is not None else ""

            corpus_parts = [name, link] + [t for t in sections_map.keys()] + [b for b in sections_map.values()]
            hay = " ".join([p for p in corpus_parts if isinstance(p, str)]).lower()

            # phrase-level occurrences (case-insensitive)
            occ_count = count_occurrences(hay, qlower)

            # if no phrase occurrences, compute how many distinct words from query appear
            word_match_count = 0
            if occ_count == 0 and words:
                for w in set(words):
                    if w and w in hay:
                        word_match_count += 1

            if occ_count == 0 and word_match_count == 0:
                continue

            # build hits (sections where query appears as substring) - keep for context
            hits = []
            if qlower in (name or "").lower():
                hits.append({"type": "title", "title": name, "excerpt": make_excerpt(name, qlower)})
            if qlower in (link or "").lower():
                hits.append({"type": "link", "title": link, "excerpt": make_excerpt(link, qlower)})
            for title, body in sections_map.items():
                if qlower in (title or "").lower() or qlower in (body or "").lower():
                    hits.append({"type": "section", "title": title, "excerpt": make_excerpt(body or title, qlower)})

            # prepare sections list with matched flags according to phrase or word matching
            sections_list = []
            for title, body in sections_map.items():
                body_str = body or ""
                title_l = (title or "").lower()
                body_l = body_str.lower()
                if occ_count > 0:
                    matched_flag = (qlower in title_l) or (qlower in body_l)
                else:
                    matched_flag = any((w in title_l) or (w in body_l) for w in set(words))
                sections_list.append({
                    "title": title,
                    "excerpt": make_excerpt(body_str, qlower),
                    "matched": matched_flag,
                    "content": body_str
                })

            match_count = sum(1 for s in sections_list if s.get("matched"))
            overall_excerpt = make_excerpt((name or "") + " " + " ".join(list(sections_map.values())), qlower)

            result_item = {
                "name": name,
                "link": link,
                "matches": hits if hits else [{"type": "excerpt", "title": name or link, "excerpt": overall_excerpt}],
                "sections": sections_list,
                "match_count": match_count,
                "occurrence_count": occ_count,
                "word_match_count": word_match_count
            }

            if occ_count > 0:
                phrase_results.append(result_item)
            else:
                word_results.append(result_item)

        # sort phrase results by occurrence_count desc
        phrase_results.sort(key=lambda x: x.get("occurrence_count", 0), reverse=True)
        # sort word results by number of distinct words matched desc
        word_results.sort(key=lambda x: x.get("word_match_count", 0), reverse=True)

        if exact:
            return phrase_results

        # combine while avoiding duplicates (by name+link)
        combined = []
        seen = set()
        for group in (phrase_results, word_results):
            for it in group:
                key = (it.get("name") or "", it.get("link") or "")
                if key in seen:
                    continue
                seen.add(key)
                combined.append(it)

        return combined
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during search")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

from langchain_community.vectorstores import Chroma
from langchain_community.docstore.document import Document
from langchain.chains import RetrievalQA
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_ollama import OllamaLLM
from langchain.prompts import PromptTemplate

def sanitize_answer(text: str) -> str:
    if not isinstance(text, str):
        return text
    sanitized = text.replace("**", "")
    return sanitized

# Scholarly default prompt template to enforce academic, truthful tone
ACADEMIC_PROMPT = PromptTemplate(
    input_variables=["context", "question"],
    template=(
        "You are an academic research assistant for space biology researchers, scholars, and university-level students. "
        "Respond in a precise, formal, scholarly register without condescension. Be truthful; do NOT fabricate. "
        "Output MUST be plain text only: absolutely NO markdown, NO bold, NO italics, NO asterisks (*), NO code fences, "
        "and NO decorative symbols. Do not surround headings or phrases with ** or *. Do not introduce bullet points unless the "
        "exact bullet characters already appear verbatim in the provided context; otherwise write in sentences. "
        "If the context does not contain the answer, explicitly state that and suggest what additional data would help.\n\n"
        "When citing supporting context, use the format (Source: <title>) where <title> is the metadata title of a document. "
        "Do not invent or speculate beyond the given context; minimize speculative language.\n\n"
        "Context:\n{context}\n\nQuestion: {question}\n\nScholarly Answer:"
    )
)

@app.get("/ask", response_class=JSONResponse)
def ask_question(query: str = Query(..., description="Ask a question about the research data")):
    # Load the data file
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Space challenge", "data.json"))
    if not os.path.exists(data_path):
        raise HTTPException(status_code=500, detail=f"Data file not found: {data_path}")

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Convert JSON entries to LangChain Documents
    docs = []
    for entry in data:
        name = entry.get("name", "Untitled")
        sections = entry.get("sections", {})
        # Normalize sections if they might be a list form
        if isinstance(sections, list):
            normalized = {}
            for idx, sec in enumerate(sections):
                if isinstance(sec, dict):
                    title = sec.get("title") or sec.get("name") or f"section_{idx}"
                    body = sec.get("text") or sec.get("body") or ""
                    normalized[title] = body
            sections = normalized
        if not isinstance(sections, dict):
            sections = {}
        text_parts = [f"{sec_name}: {sec_content}" for sec_name, sec_content in sections.items()]
        full_text = "\n".join(text_parts)
        docs.append(Document(page_content=full_text, metadata={"title": name, "link": entry.get("link", "")}))

    # Embeddings & Vector Store
    embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = Chroma.from_documents(docs, embedding_function)

    # Ensure Ollama is running (retry lazily if initial startup failed)
    if not _ollama_ready():
        if OLLAMA_AUTOSTART and OLLAMA_LAZY_RETRY:
            logger.info("Ollama not ready at query time; attempting blocking start now...")
            ok = _start_ollama_background(block=True)
            if not ok or not _ollama_ready():
                raise HTTPException(status_code=503, detail="Ollama backend not available after retry.")
        else:
            raise HTTPException(status_code=503, detail="Ollama backend not reachable.")

    # LLM
    llm = OllamaLLM(model="llama3", base_url="http://127.0.0.1:11434", temperature=0)

    # RetrievalQA with academic prompt
    qa = RetrievalQA.from_chain_type(
        llm=llm,
        chain_type="stuff",
        retriever=db.as_retriever(search_kwargs={"k": 3}),
        return_source_documents=True,
        chain_type_kwargs={"prompt": ACADEMIC_PROMPT},  # inject scholarly instructions
    )

    try:
        result = qa({"query": query})
        answer = result.get("result", "")
        answer = sanitize_answer(answer)
        sources = [
            {"title": d.metadata.get("title", "Unknown"), "link": d.metadata.get("link", "")}
            for d in result.get("source_documents", [])
        ]
        return {"answer": answer, "sources": sources}
    except Exception as e:
        logger.exception("Error running QA chain")
        raise HTTPException(status_code=500, detail=f"Error answering question: {e}")

@app.get("/ai", response_class=HTMLResponse)
def ai_page(request: Request):
    accessibility = {"font_size": "medium"}  # Default accessibility settings
    return templates.TemplateResponse("AI.html", {"request": request, "accessibility": accessibility})

@app.get("/index", response_class=HTMLResponse)
def index_page(request: Request):
    context = {
        "request": request,
        "accessibility": {"font_size": "medium"}  # Default value for accessibility
    }
    return templates.TemplateResponse("index.html", context)
