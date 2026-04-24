"""
Financial Section Chunker

Chunks P&L DataFrames and raw text into LangChain Documents
grouped by financial section for higher RAG retrieval precision.

Section classification uses SECTION_MAP from financial_keywords.py.
"""

import os
import re
import sys
import pandas as pd
from langchain_core.documents import Document

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from financial_keywords import SECTION_MAP, SKIP_ROW_KEYWORDS


# ── Row classifier ───────────────────────────────────────────────────

def classify_row(label: str) -> str:
    """
    Map a P&L row label to its financial section using SECTION_MAP.

    Matching is substring-based (keyword in label), which handles
    verbose label variants without requiring exact matches.

    Returns 'Other' if no section matches.
    """
    if not isinstance(label, str):
        return "Other"

    ll = label.strip().lower()

    # Skip header/metadata rows
    if any(skip in ll for skip in SKIP_ROW_KEYWORDS):
        return "Other"

    for section, keywords in SECTION_MAP.items():
        for kw in keywords:
            if kw.lower() in ll:
                return section

    return "Other"


# ── DataFrame chunker ────────────────────────────────────────────────

def chunk_dataframe_by_section(
    df: pd.DataFrame,
    metadata: dict | None = None,
) -> list[Document]:
    """
    Group DataFrame rows into LangChain Documents by financial section.

    Each section becomes one Document whose page_content is a
    human-readable block of the rows in that section.
    """
    if metadata is None:
        metadata = {}

    label_col = None
    for col in df.columns:
        if df[col].dtype == object:
            label_col = col
            break

    if label_col is None:
        return [Document(
            page_content=df.to_string(index=False),
            metadata={"section": "Full Document", **metadata},
        )]

    sections: dict[str, list[str]] = {}
    for _, row in df.iterrows():
        label = str(row[label_col])
        section = classify_row(label)

        values = [
            f"{col}: {val}"
            for col, val in zip(df.columns, row)
            if pd.notna(val)
        ]
        line = " | ".join(values)
        sections.setdefault(section, []).append(line)

    documents = []
    for section_name, lines in sections.items():
        content = f"=== {section_name} ===\n" + "\n".join(lines)
        documents.append(Document(
            page_content=content,
            metadata={"section": section_name, **metadata},
        ))

    return documents


# ── Raw-text chunker ─────────────────────────────────────────────────

def chunk_raw_text_by_section(
    text: str,
    metadata: dict | None = None,
) -> list[Document]:
    """
    Split raw text (from PDF) into chunks at financial section headers.

    Builds a regex from all section keywords in SECTION_MAP so any
    new keyword added to financial_keywords.py is automatically used
    here too.
    """
    if metadata is None:
        metadata = {}

    # Build pattern from all keywords in SECTION_MAP
    all_kws = sorted(
        {kw for kws in SECTION_MAP.values() for kw in kws},
        key=len, reverse=True   # longest first → more specific wins
    )
    # Escape and join; use word boundaries on the left, flexible right
    escaped = [re.escape(kw) for kw in all_kws[:120]]  # cap regex size
    pattern = re.compile(
        r"^(" + "|".join(escaped) + r")",
        re.IGNORECASE | re.MULTILINE,
    )

    splits: list[tuple[str, str]] = []
    last_idx = 0
    last_section = "Header"

    for match in pattern.finditer(text):
        if match.start() > last_idx:
            chunk_text = text[last_idx:match.start()].strip()
            if chunk_text:
                splits.append((last_section, chunk_text))
        last_section = classify_row(match.group(0))
        last_idx = match.start()

    remaining = text[last_idx:].strip()
    if remaining:
        splits.append((last_section, remaining))

    if not splits:
        return [Document(
            page_content=text,
            metadata={"section": "Full Document", **metadata},
        )]

    return [
        Document(
            page_content=f"=== {section_name} ===\n{content}",
            metadata={"section": section_name, **metadata},
        )
        for section_name, content in splits
    ]


# ── Main entry point ─────────────────────────────────────────────────

def chunk_document(
    df: pd.DataFrame,
    metadata: dict | None = None,
) -> list[Document]:
    """
    Auto-detect tabular vs raw-text DataFrame and chunk accordingly.
    """
    if "raw_text" in df.columns:
        raw = df["raw_text"].iloc[0]
        print(f"[Chunker] Processing raw text ({len(raw)} chars) …")
        docs = chunk_raw_text_by_section(raw, metadata)
    else:
        print(f"[Chunker] Processing tabular data ({len(df)} rows) …")
        docs = chunk_dataframe_by_section(df, metadata)

    sections_found = [d.metadata.get("section", "?") for d in docs]
    print(f"[Chunker] Created {len(docs)} chunks: {sections_found}")
    return docs