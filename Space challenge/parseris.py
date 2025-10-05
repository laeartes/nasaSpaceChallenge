# The main parser code (using beautifulsoup and other modules) were written without AI, however, to improve error catching Copilot was used
# and to help with some technical difficulties ChatGPT was used 

import os
import csv
import json
import logging
from time import sleep

import requests
from requests.adapters import HTTPAdapter
from requests.exceptions import RequestException
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
CSV_PATH = os.path.join(BASE_DIR, "SB_publication_PMC.csv")
OUT_PATH = os.path.join(BASE_DIR, "data.json")

publications = {}
if not os.path.exists(CSV_PATH):
    logging.error("CSV file not found: %s", CSV_PATH)
else:
    with open(CSV_PATH, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        try:
            next(reader)
        except StopIteration:
            pass
        for row in reader:
            if len(row) >= 2:
                publications[row[0]] = row[1]

headers = {"User-Agent": "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/117.0"}

session = requests.Session()
session.headers.update(headers)
retries = Retry(total=3, backoff_factor=0.3, status_forcelist=(500, 502, 503, 504))
adapter = HTTPAdapter(max_retries=retries)
session.mount("https://", adapter)
session.mount("http://", adapter)


def parsing(pub_name, url, timeout=10):
    try:
        resp = session.get(url, timeout=timeout)
        resp.raise_for_status()
    except RequestException as e:
        logging.error("Network error for %s (%s): %s", pub_name, url, e)
        return {"name": pub_name, "link": url, "sectionNames": [], "sections": {}, "error": str(e)}

    try:
        soup = BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        logging.exception("Failed to parse HTML for %s (%s): %s", pub_name, url, e)
        return {"name": pub_name, "link": url, "sectionNames": [], "sections": {}, "error": "parse_error"}

    json_dictionary = {"name": pub_name, "link": url}
    sections = soup.find_all("section")
    all_section_names = []
    inner_text = {}

    for sec in sections:
        try:
            if "class" in sec.attrs and "main-article-body" in sec["class"]:
                subsections = sec.find_all("section")
                for subsec in tqdm(subsections, desc=f"Parsing sections: {pub_name}", leave=False):
                    try:
                        if subsec.h2 is not None:
                            Section_name = subsec.h2.get_text(strip=True)
                            all_section_names.append(Section_name)
                            temp_text = ""
                            subsec.h2.decompose()
                            if subsec.h3 is not None:
                                subsection_name = subsec.h3.get_text(strip=True)
                                temp_text += subsection_name + "\n"

                            for paragraph in subsec.find_all("p"):
                                par = paragraph.get_text(separator="", strip=True)
                                temp_text += par + "\n"

                            if Section_name == "References":
                                ref = subsec.get_text(separator="", strip=True)
                                temp_text += ref

                            inner_text[Section_name] = temp_text
                    except Exception:
                        logging.exception("Error processing subsection in %s", pub_name)
                        continue
        except Exception:
            logging.exception("Error processing section container for %s", pub_name)
            continue

    json_dictionary.update({"sectionNames": all_section_names})
    json_dictionary.update({"sections": inner_text})
    logging.info("done: %s", pub_name)
    return json_dictionary


def main():
    results = []
    items = list(publications.items())
    try:
        for NAME, LINK in tqdm(items, desc="Parsing articles", total=len(items)):
            try:
                res = parsing(NAME, LINK)
                results.append(res)
                sleep(0.05)
            except Exception as e:
                logging.exception("Failed to parse article %s: %s", NAME, e)
                results.append({"name": NAME, "link": LINK, "sectionNames": [], "sections": {}, "error": str(e)})
    except KeyboardInterrupt:
        logging.warning("Interrupted by user, writing partial results...")
    finally:
        try:
            with open(OUT_PATH, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=4)
            logging.info("Wrote %d records to %s", len(results), OUT_PATH)
        except Exception:
            logging.exception("Failed to write output file")

if __name__ == "__main__":
    main()