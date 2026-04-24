"""
P&L Summarizer — Main Orchestrator

End-to-end pipeline runner:
    1. Ingest document (PDF / Excel / CSV)
    2. Clean and normalize
    3. Chunk by financial section
    4. Build FAISS vector store
    5. Compute KPIs
    6. Interactive query loop via RAG + Gemini 2.5 Flash
"""

import argparse
import json
import os
import sys

# Ensure project root is on path
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_ROOT)

from src.ingestion.parser import ingest_document
from src.ingestion.cleaner import clean_pipeline
from src.chunking.financial_chunker import chunk_document
from src.vectorstore.store import (
    build_vectorstore, get_retriever, save_vectorstore, load_vectorstore,
)
from src.analysis.kpi_engine import extract_kpis
from src.rag.pipeline import build_rag_chain, query_pipeline


def parse_args():
    parser = argparse.ArgumentParser(
        description="P&L Summarizer — RAG Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --file report.pdf
  python main.py --file q1.csv --quarter "Q1 2025" --company "ABC Ltd"
  python main.py --file data.xlsx --save-index
  python main.py --load-index ./data/vectorstore --query "Summarize this P&L"
        """,
    )
    parser.add_argument(
        "--file", type=str,
        help="Path to the P&L document (PDF, Excel, or CSV).",
    )
    parser.add_argument(
        "--quarter", type=str, default=None,
        help="Quarter label for metadata (e.g., 'Q1 2025').",
    )
    parser.add_argument(
        "--company", type=str, default=None,
        help="Company name for metadata.",
    )
    parser.add_argument(
        "--save-index", action="store_true",
        help="Save the FAISS index to disk after building.",
    )
    parser.add_argument(
        "--load-index", type=str, default=None,
        help="Load a previously saved FAISS index from this path.",
    )
    parser.add_argument(
        "--query", type=str, default=None,
        help="Single query to run (skips interactive mode).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # ── Step 0: Validate inputs ──────────────────────────────────
    if args.load_index is None and args.file is None:
        print("Error: Provide either --file or --load-index.")
        sys.exit(1)

    kpi_data = {}
    retriever = None

    # ── Step 1-4: Ingest → Clean → Chunk → Vectorize ────────────
    if args.file:
        print("\n" + "=" * 60)
        print("  P&L SUMMARIZER — RAG Pipeline")
        print("=" * 60)

        # Step 1: Ingest
        print("\n📄 Step 1: Ingesting document …")
        df = ingest_document(args.file)
        print(f"   Parsed {len(df)} rows × {len(df.columns)} columns")

        # Step 2: Clean
        print("\n🧹 Step 2: Cleaning data …")
        df = clean_pipeline(df)

        # Step 3: Chunk
        print("\n✂️  Step 3: Chunking by financial section …")
        metadata = {}
        if args.quarter:
            metadata["quarter"] = args.quarter
        if args.company:
            metadata["company"] = args.company
        documents = chunk_document(df, metadata)

        # Step 4: Build vector store
        print("\n🔢 Step 4: Building vector store …")
        vectorstore = build_vectorstore(documents)

        if args.save_index:
            save_vectorstore(vectorstore)

        retriever = get_retriever(vectorstore)

        # Step 5: Compute KPIs
        print("\n📊 Step 5: Computing KPIs …")
        kpi_data = extract_kpis(df)
        _print_kpis(kpi_data)

    # ── Or load a saved index ────────────────────────────────────
    elif args.load_index:
        print("\n📂 Loading saved vector store …")
        vectorstore = load_vectorstore(args.load_index)
        retriever = get_retriever(vectorstore)

    # ── Step 6: Build RAG chain ──────────────────────────────────
    print("\n🤖 Step 6: Building RAG chain with Gemini 2.5 Flash …")
    chain = build_rag_chain(retriever)
    print("   Chain ready!\n")

    # ── Step 7: Query ────────────────────────────────────────────
    if args.query:
        # Single query mode
        _run_query(chain, args.query, kpi_data)
    else:
        # Interactive mode
        _interactive_loop(chain, kpi_data)


def _print_kpis(kpi_data: dict):
    """Pretty-print computed KPIs."""
    print("\n   ┌─────────────────────────────────────────┐")
    print("   │         COMPUTED KPIs                    │")
    print("   ├─────────────────────────────────────────┤")
    for key, value in kpi_data.items():
        if value is not None:
            label = key.replace("_", " ").title()
            if key.endswith("_pct"):
                print(f"   │  {label:<30} {value:>6}% │")
            else:
                print(f"   │  {label:<30} {value:>7,.0f} │")
    print("   └─────────────────────────────────────────┘")


def _run_query(chain, query: str, kpi_data: dict):
    """Execute a single query and print results."""
    print(f"\n❓ Query: {query}")
    print("-" * 60)

    result = query_pipeline(chain, query, kpi_data)

    # Print structured output as JSON
    output = result.model_dump()
    # Remove raw_response from pretty-print (it's long)
    display = {k: v for k, v in output.items() if k != "raw_response"}

    print("\n📋 STRUCTURED RESPONSE:")
    print(json.dumps(display, indent=2, ensure_ascii=False))

    print("\n📝 FULL RESPONSE:")
    print(result.raw_response)

    print(f"\n🎯 Confidence: {result.confidence_score}")
    print(f"📚 Sources used: {', '.join(result.sources_used)}")


def _interactive_loop(chain, kpi_data: dict):
    """Run an interactive query loop."""
    print("=" * 60)
    print("  💬 Interactive Query Mode")
    print("  Type your question about the P&L document.")
    print("  Commands: 'quit' | 'exit' | 'kpis' | 'json'")
    print("=" * 60)

    output_json = False

    while True:
        try:
            query = input("\n🔍 You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not query:
            continue

        if query.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        if query.lower() == "kpis":
            _print_kpis(kpi_data)
            continue

        if query.lower() == "json":
            output_json = not output_json
            print(f"   JSON output: {'ON' if output_json else 'OFF'}")
            continue

        result = query_pipeline(chain, query, kpi_data)

        if output_json:
            output = result.model_dump()
            display = {k: v for k, v in output.items() if k != "raw_response"}
            print(json.dumps(display, indent=2, ensure_ascii=False))
        else:
            print(f"\n🤖 Analyst:\n{result.raw_response}")
            print(f"\n   🎯 Confidence: {result.confidence_score}")
            print(f"   📚 Sources: {', '.join(result.sources_used)}")


if __name__ == "__main__":
    main()
