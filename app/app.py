from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
import os
import json
import logging
from typing import List, Dict, Any

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nasaSpaceChallenge")

@app.get("/", response_class=HTMLResponse)
def read_root(request: Request):
	# provide navigation links and default accessibility settings to the template
	nav_links = [
		{"name": "Home", "href": "/"},
		{"name": "Upload", "href": "/upload"},
		{"name": "About", "href": "/about"},
		{"name": "Resources", "href": "/resources"}
	]
	accessibility = {"font_size": "medium", "contrast": "dark"}
	return templates.TemplateResponse("index.html", {
		"request": request,
		"title": "nasaSpaceChallenge",
		"nav_links": nav_links,
		"accessibility": accessibility
	})

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
        combined.append(it)
        return combined
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unexpected error during search")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")
    