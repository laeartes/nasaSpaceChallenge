# NASA Space App Challenge

This repository contains the project created by Vytautė, Žygis, Jokūbas, and Mykolas for the NASA Space App Challenge Hackathon.

## About the Project
Our project targets the **Build a Space Biology Knowledge Engine** challenge. It aims to organize space biology data so researchers and enthusiasts can explore effects of space conditions on biological systems.

## What the Code Does
The code provides:
- Scraping & processing of space biology data (data consolidated into a JSON knowledge base).
- An interactive FastAPI web application for searching structured sections.
- Query and filtering endpoints for quick information retrieval (/search, /ask).
- Integrated local LLM question answering (retrieval augmented) using Ollama + llama3.

(Visualization of relationship graphs was removed from scope in this version.)

## Installation & Running
1. Clone the repository
```
git clone <repository-url>
cd nasaSpaceChallenge
```
2. Install Python dependencies
```
pip install -r requirements.txt
```
3. (Optional but recommended) Install Ollama and pull the model before first run (see next section). If you skip, the app will still try to use a local Ollama service on default port.
4. Run the application 

```
cd nasaSpaceChallenge/app && python -m uvicorn app:app --reload
```
App runs at: http://127.0.0.1:8000

## Ollama Setup (Local LLM Backend)
Install Ollama (choose your platform):
- macOS (Homebrew): `brew install ollama`
- macOS/Linux (script): `curl -fsSL https://ollama.com/install.sh | sh`
- Windows: Download installer from https://ollama.com OR `winget install Ollama.Ollama`

After installation, start (if not auto-started) and pull the llama3 model:
```
ollama serve   # may already be running as a background service
ollama pull llama3
```
You can substitute another compatible model; ensure it is pulled before use to avoid first-request delays.

## Using the App
- Navigate to `/` for the main interface.


## Troubleshooting
- Model download delay: run `ollama pull llama3` ahead of time.
- Ollama not reachable: ensure it listens on 127.0.0.1:11434 (default) and not blocked by firewall.
- Memory issues: pull and switch to a smaller model variant.

## Team Members
- Vytautė
- Žygis
- Jokūbas
- Mykolas

## License
This project is open-source and available under the MIT License.

---
Created during the NASA Space App Challenge Hackathon.

