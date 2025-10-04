from fastapi import FastAPI, Request, Query
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import os
import json
from typing import List, Dict, Any

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "title": "webapp"
    })

@app.get("/search", response_class=JSONResponse)
def search(term: str = Query(..., alias="query", min_length=1, description="Search query string")) -> List[Dict[str, Any]]:
    data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Space challenge", "data.json"))
    if not os.path.exists(data_path):
        return []

    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []

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

    results: List[Dict[str, Any]] = []
    qlower = term.strip().lower()
    if not isinstance(data, list):
        return []

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

        corpus_parts = [name, link]
        for t, b in sections_map.items():
            corpus_parts.append(t)
            corpus_parts.append(b)
        hay = " ".join([p for p in corpus_parts if isinstance(p, str)]).lower()

        if qlower in hay:
            hits = []
            if qlower in (name or "").lower():
                hits.append({"type": "title", "title": name, "excerpt": make_excerpt(name, qlower)})
            if qlower in (link or "").lower():
                hits.append({"type": "link", "title": link, "excerpt": make_excerpt(link, qlower)})
            for title, body in sections_map.items():
                if qlower in (title or "").lower() or qlower in (body or "").lower():
                    hits.append({"type": "section", "title": title, "excerpt": make_excerpt(body or title, qlower)})

            sections_list = []
            for title, body in sections_map.items():
                body_str = body or ""
                matched_flag = (qlower in (title or "").lower()) or (qlower in body_str.lower())
                sections_list.append({
                    "title": title,
                    "excerpt": make_excerpt(body_str, qlower),
                    "matched": matched_flag,
                    "content": body_str
                })

            overall_excerpt = make_excerpt(corpus_parts[0] + " " + " ".join(list(sections_map.values())), qlower)
            results.append({
                "name": name,
                "link": link,
                "matches": hits if hits else [{"type": "excerpt", "title": name or link, "excerpt": overall_excerpt}],
                "sections": sections_list
            })

    return results
