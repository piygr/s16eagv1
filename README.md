# S16EAGv1: Agentic AI (Multi Agent) System

A modular Python framework to orchestrate autonomous AI agents using memory, perception, heuristics, action execution, and browser control. The project is built around the concept of `agentLoop`, allowing AI agents to think, plan, and act via a persistent mesh of capabilities.

[DEMO](https://youtu.be/3Y3x0Lr05PQ)

---

## 🧠 Key Features

- **Agentic Loop Core (`agentLoop`)**  
  Executes multi-step agent workflows using memory, planning, perception, and action.

- **Tooling Layer**  
  Asynchronous and browser-based tools via Playwright for web tasks, integrated with a FastAPI server.

- **Memory Management**  
  Vector-based memory using FAISS for long-term recall and embeddings (OpenAI/Google-based).

- **Heuristics & Safety**  
  Pluggable safety and control mechanisms (`heuristics`) to govern output and decision chains.

- **LLM Orchestration (`mcp_servers`)**  
  Uses Gemini/OpenAI-powered command processors with dynamic tool routing and streaming.

- **Web Interface & LiveKit Integration**  
  Hooks for interactive usage through web sockets and real-time interview agents.

---

## 🗂️ Project Structure

```
s16eagv1/
├── action/ # Tool execution and action framework
├── agentLoop/ # Core logic for agent decision loop
├── browserMCP/ # Browser-based task controller
├── config/ # Environment and settings
├── heuristics/ # Rule-based filtering and validation
├── media/ # Audio/visual I/O tools (TTS/STT)
├── memory/ # FAISS-based memory system
├── mcp_servers/ # Command processors + FastAPI servers
├── prompts/ # Agent prompt templates
├── tools/ # Web and file-based utility tools
└── main.py # Entry point to launch agent system
```


---

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/piygr/s16eagv1.git
cd s16eagv1
```
### 2. Setup environment (with uv)
```
uv venv
source .venv/bin/activate
uv pip install .
```

### 3. Install Playwright browser (e.g., Chromium)
```
python -m playwright install chromium
```

### 4. Run the agent loop

```
uv run main.py
```

## 🔧 Configuration

Update .env to configure:

- LLM providers (OpenAI, Gemini)
- Embedding models
- Web search tools
- Tool API keys (Google, SerpAPI, etc.)

## 📦 Dependencies

Key dependencies include:

- playwright — browser automation
- faiss-cpu — vector memory backend
- llama-index — document and embedding framework
- fastapi, httpx, uvicorn — API & server
- mcp — multi-agent command processor
- spacy, markdownify, tqdm, jinja2

## 🧪 Development Notes

- Designed around modular, testable agent logic (agentLoop.run_agent())
- Compatible with uv for clean dependency resolution
- Embedding tools can be swapped between OpenAI/Google

##### Example prompts
```
- Find the ASCII values of characters in INDIA and then return sum of exponentials of those values.
- How much Anmol singh paid for his DLF apartment via Capbridge? 
- What do you know about Don Tapscott and Anthony Williams?
- What is the relationship between Gensol and Go-Auto?
- which course are we teaching on Canvas LMS? "H:\DownloadsH\How to use Canvas LMS.pdf"
- Summarize this page: https://theschoolof.ai/
- What is the log value of the amount that Anmol singh paid for his DLF apartment via Capbridge? Hint: use local 
- find the the main difference between latest BMW 7 and 5 series online. Reply back in detail and in markdown.
- How much money did Anmol Singh paid to DLF to buy an apartment in Camelias indirectly? Search local storage agian?
- What are the main differences between Mercedes S Class end E Class. Reply back in markdown list. 
- Who is the current chairman of DLF? Search local documents. 
```

