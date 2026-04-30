<div align="center">

<img src="https://img.shields.io/badge/-%F0%9F%93%8A%20AI%20P%26L%20Analyzer-0d1117?style=for-the-badge" alt="title" />

# 📊 AI P&L Analyzer

### *Intelligent Financial Statement Analysis, Powered by RAG*

**An End-to-End RAG Pipeline & Interactive Dashboard for Financial Statement Analysis**

<br/>

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=flat-square&logo=fastapi&logoColor=white)
![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-AI%20Powered-FF6D00?style=flat-square&logo=google&logoColor=white)
![FAISS](https://img.shields.io/badge/FAISS-Vector%20Store-6C757D?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat-square)

<br/>

[🚀 Quick Start](#-getting-started) · [✨ Features](#-key-features) · [🗂️ Structure](#️-repository-structure) · [💡 Why This Project?](#-why-this-project)

---

</div>

## 📌 Overview

The **AI P&L Analyzer** is a comprehensive RAG (Retrieval-Augmented Generation) system designed to **automate the extraction, analysis, and visualization** of financial data from Profit & Loss statements.

By seamlessly ingesting raw financial documents (PDFs, Excel, or CSVs), this project cleans, chunks, and vectorizes the data to provide actionable insights. It computes key **KPIs** and allows users to ask complex financial questions via a **conversational AI interface**.

> Originally built as a powerful CLI pipeline, the project has evolved into a fully interactive web application featuring a modern dashboard, automated charting, and real-time AI-powered financial querying.

---

## ✨ Key Features

<details open>
<summary><b>🧠 Advanced RAG & NLP Pipeline</b></summary>
<br/>

| Feature | Description |
|---------|-------------|
| **Intelligent Document Processing** | Automatically ingests and cleans structured or semi-structured financial documents (PDF, XLSX, CSV), handling varying formats with a centralized financial keyword ontology (`financial_keywords.py`) |
| **Semantic Chunking & Vector Search** | Chunks financial data by section and builds a highly efficient FAISS vector store to ensure accurate and context-aware retrieval |
| **AI Financial Analyst** | Integrates with **Google Gemini 2.5 Flash** to answer complex financial queries, generate revenue/expense summaries, and highlight risk factors with confidence scoring and source citations |

</details>

<details open>
<summary><b>💻 Interactive Web Application</b></summary>
<br/>

| Feature | Description |
|---------|-------------|
| **Unified Full-Stack Deployment** | The FastAPI backend seamlessly serves the sleek HTML/JS frontend, requiring just a **single command** to launch |
| **Automated KPI Extraction** | Instantly calculates critical metrics such as **Gross Margin**, **EBITDA**, **Net Margin**, and **Operating Income** |
| **Conversational Q&A** | An interactive chat interface that lets you interrogate the uploaded P&L statements directly |

</details>

<details open>
<summary><b>📊 Rich Analytical Dashboards (Plotly)</b></summary>
<br/>

| Chart Type | Description |
|------------|-------------|
| **P&L Bridge (Waterfall)** | Visualizes the step-by-step transition from total revenue down to net income |
| **Expense Breakdown** | Interactive donut charts detailing spending across COGS, Employee Costs, R&D, and more |
| **Trend Analysis** | Grouped bar charts comparing revenue against key expenses over multiple financial periods |

</details>

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Language** | ![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white) | Core runtime |
| **AI / LLM** | ![Gemini](https://img.shields.io/badge/Gemini_2.5_Flash-FF6D00?style=flat-square&logo=google&logoColor=white) | Conversational intelligence |
| **Vector Store** | ![FAISS](https://img.shields.io/badge/FAISS-6C757D?style=flat-square) | Semantic document retrieval |
| **Data Processing** | ![Pandas](https://img.shields.io/badge/Pandas-150458?style=flat-square&logo=pandas&logoColor=white) | Financial data wrangling |
| **Backend** | ![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white) + Uvicorn | REST API server |
| **Frontend** | ![HTML5](https://img.shields.io/badge/HTML%2FCSS%2FJS-E34F26?style=flat-square&logo=html5&logoColor=white) | Interactive dashboard UI |
| **Environment** | `venv` + `dotenv` | Dependency & secrets management |

---

## 🚀 Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- ✅ **Python 3.10+**
- ✅ **Git**
- ✅ A valid **Google Gemini API Key** → [Get one here](https://aistudio.google.com/)

---

### ⚡ Installation & Run

**Step 1 — Clone the repository**
```bash
git clone https://github.com/yourusername/AI-PL-Analyzer.git
cd AI-PL-Analyzer
```

**Step 2 — Set up the virtual environment**
```bash
# Create the virtual environment
python -m venv venv

# Activate on Windows
.\venv\Scripts\activate

# Activate on macOS / Linux
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt
```

**Step 3 — Configure environment variables**

Create a `.env` file in the project root:
```env
GOOGLE_API_KEY=your_gemini_api_key_here
```

> ⚠️ **Never commit your `.env` file!** It is already listed in `.gitignore`.

**Step 4 — Launch the application**
```bash
uvicorn src.api.server:app --reload
```

Then open your browser and go to: **`http://127.0.0.1:8000/`** 🎉

---

### 🖥️ Optional — Run the CLI Pipeline

If you prefer to run the analysis directly in the terminal without the web UI:
```bash
python main.py --file "path/to/financial_statement.pdf"
```

---

## 🗂️ Repository Structure

```
AI P&L Analyzer/
│
├── 🌐 frontend/                     # Static files served by FastAPI
│   ├── index.html                   # Landing page & document upload interface
│   ├── dashboard.html               # Main interactive KPI & chart dashboard
│   └── analysis.html                # Conversational RAG / Q&A interface
│
├── ⚙️  src/                          # Main source code
│   │
│   ├── 📐 analysis/
│   │   └── kpi_engine.py            # Gross Margin, EBITDA, Net Margin logic
│   │
│   ├── 🌍 api/
│   │   ├── schemas.py               # Pydantic models for API requests/responses
│   │   └── server.py                # FastAPI server & route definitions
│   │
│   ├── ✂️  chunking/
│   │   └── financial_chunker.py     # Semantic segmentation for vectorization
│   │
│   ├── 📥 ingestion/
│   │   ├── cleaner.py               # Normalizes data & handles missing values
│   │   └── parser.py                # Extracts tables from PDF, CSV, and Excel
│   │
│   ├── 🤖 rag/
│   │   ├── output_schema.py         # Enforces structured JSON output from Gemini
│   │   ├── pipeline.py              # Core RAG logic (retrieval + generation)
│   │   └── prompts.py               # System prompts for the AI Financial Analyst
│   │
│   └── 🗄️  vectorstore/
│       └── store.py                 # Build, save, and load the FAISS index
│
│
├── .env                             # 🔑 Secret environment variables (not committed)
├── .gitignore                       # Files excluded from version control
├── config.py                        # Configuration loader (reads .env into Python)
├── financial_keywords.py            # 📖 Global financial term dictionary (Revenue, COGS…)
├── main.py                          # 🖥️  CLI orchestrator for pipeline without web UI
├── README.md                        # Project documentation
└── requirements.txt                 # Python library dependencies
```

---

## 💡 Why This Project?

This application demonstrates the **complete lifecycle of an applied Generative AI financial tool** across three core engineering disciplines:

```
┌─────────────────────┐      ┌───────────────────────┐    ┌──────────────────────┐
│   Data Engineering  │      │    AI Integration     │    │ Software Engineering │
├─────────────────────┤      ├───────────────────────┤    ├──────────────────────┤
│ Parsing unstructured│      │ Building a robust     │    │ Packaging complex    │
│ financial tables    │───▶ │ RAG architecture       │───▶│ data science into a │
│ Standardizing terms │      │ that grounds LLMs     │    │ production-ready     │
│ Handling missing    │      │ in factual, vectorized│    │ full-stack app for   │
│ data & formats      │      │ data — reducing       │    │ financial analysts   │
│                     │      │ hallucinations        │    │ and end-users        │
└─────────────────────┘      └───────────────────────┘    └──────────────────────┘
```

---

## 📄 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Built with ❤️ using Python, FastAPI & Google Gemini**

If you find this project interesting, feel free to ⭐ the repository or connect with me on LinkedIn! -
https://www.linkedin.com/in/shone-prince/

</div>
