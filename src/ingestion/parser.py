"""
Document Ingestion — Parser Module

Handles parsing of PDF, Excel, and CSV files into a unified
pandas DataFrame format for downstream processing.

Fixed:
- Unified Gemini SDK usage (google-generativeai via langchain-google-genai)
- Multi-page OCR support for scanned PDFs
- Better handling of Balance Sheet + P&L combined documents
"""

import os
import pandas as pd
import pdfplumber


def parse_pdf(file_path: str) -> pd.DataFrame:
    """
    Extract tabular data from a PDF using pdfplumber.

    Strategy:
        1. Iterate through each page looking for tables.
        2. If tables are found, combine them into a single DataFrame.
        3. If no tables are found, extract raw text and return it
           as a single-column DataFrame for text-based processing.
        4. Fallback: AI-powered OCR using Gemini for scanned PDFs.
    """
    all_tables = []
    raw_text_pages = []

    with pdfplumber.open(file_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            tables = page.extract_tables()
            if tables:
                for table in tables:
                    if len(table) > 1:
                        header = table[0]
                        rows = table[1:]

                        # Deduplicate headers
                        new_cols = []
                        seen = set()
                        for c in header:
                            c_str = str(c).strip() if c is not None else "Unnamed"
                            if c_str in seen:
                                i = 1
                                while f"{c_str}_{i}" in seen:
                                    i += 1
                                c_str = f"{c_str}_{i}"
                            seen.add(c_str)
                            new_cols.append(c_str)

                        df = pd.DataFrame(rows, columns=new_cols)
                        all_tables.append(df)
            else:
                text = page.extract_text()
                if text:
                    raw_text_pages.append(text)

    if all_tables:
        combined = pd.concat(all_tables, ignore_index=True)
        print(f"[Parser] Extracted {len(combined)} rows from {len(all_tables)} table(s)")
        return combined

    if raw_text_pages:
        full_text = "\n".join(raw_text_pages)
        print(f"[Parser] No tables found — extracted {len(full_text)} chars of raw text")
        return pd.DataFrame({"raw_text": [full_text]})

    # ── Fallback: AI OCR for scanned PDFs ────────────────────────────
    print("[Parser] No extractable text found. Attempting AI-powered OCR with Gemini...")
    return _ocr_with_gemini(file_path)


def _ocr_with_gemini(file_path: str) -> pd.DataFrame:
    """
    Use Gemini Vision to OCR a scanned PDF and extract P&L table data.
    Processes multiple pages and merges results.
    """
    try:
        import io
        import base64
        import json
        import json_repair
        import sys
        
        # Add project root to path for config
        PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        sys.path.insert(0, PROJECT_ROOT)
        import config

        # Use google-generativeai SDK (same as langchain-google-genai uses)
        import google.generativeai as genai
        genai.configure(api_key=config.GOOGLE_API_KEY)
        model = genai.GenerativeModel(config.LLM_MODEL)

        print("[Parser] Converting PDF pages to images for Vision API...")

        all_dfs = []
        with pdfplumber.open(file_path) as pdf:
            # Process all pages (balance sheet may span multiple pages)
            for page_num, page in enumerate(pdf.pages):
                print(f"[Parser] Processing page {page_num + 1}/{len(pdf.pages)}...")
                img = page.to_image(resolution=200)

                buffered = io.BytesIO()
                img.original.save(buffered, format="PNG")
                img_bytes = buffered.getvalue()

                prompt = (
                    "You are a strict financial data extraction tool. "
                    "This is a scanned page from an Indian company's annual report (P&L / Balance Sheet). "
                    "Extract ALL financial data tables into a JSON array of objects. "
                    "Each object = one row, keys = column headers (e.g. 'Particulars', 'Mar 31,2024', 'Mar 31,2023'). "
                    "Include ALL rows: revenue, expenses, profit lines, tax, net income, EPS, etc. "
                    "For numbers in '000s, keep them as-is. "
                    "Return ONLY valid JSON array starting with '[' and ending with ']'. "
                    "No markdown, no backticks, no explanations."
                )

                import PIL.Image
                pil_img = PIL.Image.open(io.BytesIO(img_bytes))

                response = model.generate_content(
                    [prompt, pil_img],
                    generation_config={"max_output_tokens": 4000, "temperature": 0.0},
                )

                json_text = response.text.strip()

                # Strip markdown code fences if present
                if "```" in json_text:
                    lines = json_text.split("\n")
                    json_text = "\n".join(
                        l for l in lines
                        if not l.strip().startswith("```")
                    )

                try:
                    data = json_repair.loads(json_text)
                    if isinstance(data, list) and len(data) > 0:
                        page_df = pd.DataFrame(data)
                        all_dfs.append(page_df)
                        print(f"[Parser] Page {page_num + 1}: extracted {len(page_df)} rows")
                except Exception as parse_err:
                    print(f"[Parser] Could not parse JSON from page {page_num + 1}: {parse_err}")
                    continue

        if all_dfs:
            # Merge all pages — try to align columns
            try:
                combined = pd.concat(all_dfs, ignore_index=True)
            except Exception:
                combined = all_dfs[0]

            print(f"[Parser] AI OCR successful — {len(combined)} total rows extracted")
            return combined

        raise ValueError("Gemini OCR returned no usable data from any page.")

    except ImportError as e:
        raise ValueError(
            f"Missing dependency for OCR: {e}. "
            f"Install: pip install google-generativeai pillow json-repair"
        )
    except Exception as e:
        raise ValueError(
            f"AI OCR failed: {str(e)}. "
            f"Ensure GOOGLE_API_KEY is set and the PDF is readable. "
            f"Consider converting to Excel or CSV for better results."
        )


def parse_excel(file_path: str, sheet_name: int | str = 0) -> pd.DataFrame:
    df = pd.read_excel(file_path, sheet_name=sheet_name, engine="openpyxl")
    return df


def parse_csv(file_path: str) -> pd.DataFrame:
    df = pd.read_csv(file_path)
    return df


def ingest_document(file_path: str, **kwargs) -> pd.DataFrame:
    """
    Auto-detect the file type and route to the correct parser.
    Supported formats: .pdf, .xlsx, .xls, .csv
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    parsers = {
        ".pdf":  parse_pdf,
        ".xlsx": parse_excel,
        ".xls":  parse_excel,
        ".csv":  parse_csv,
    }

    parser = parsers.get(ext)
    if parser is None:
        raise ValueError(
            f"Unsupported file format: '{ext}'. "
            f"Supported: {', '.join(parsers.keys())}"
        )

    print(f"[Parser] Ingesting {ext.upper()} file: {os.path.basename(file_path)}")
    return parser(file_path, **kwargs)