"""
Exam Paper Pipeline
===================
Usage:
  # Process all PDFs and Word docs in a folder (batch mode):
  python run_pipeline.py --folder data/raw_pdfs/sample

  # Process a single file (PDF or .docx):
  python run_pipeline.py --file data/raw_pdfs/sample/paper.pdf

  # Watch a folder for new files (auto-processes on drop):
  python run_pipeline.py --watch data/raw_pdfs/sample
"""

import argparse
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import RAW_PDF_DIR, EXTRACTED_TEXT_DIR, CLEANED_JSON_DIR, get_branch
from extraction.pdf_to_text import process_file, SUPPORTED_EXTENSIONS
from cleaning.text_to_json import process_text_file
from db.database import init_db
from db.insert import upsert_paper

# Lazy imports for optional components
_chroma_available = None


def is_chroma_available():
    global _chroma_available
    if _chroma_available is None:
        try:
            import chromadb  # noqa: F401
            import sentence_transformers  # noqa: F401
            _chroma_available = True
        except ImportError:
            _chroma_available = False
    return _chroma_available


def process_single_file(file_path):
    """Full pipeline for one file: extract -> clean -> DB -> ChromaDB."""
    file_path = Path(file_path)
    print(f"\n--- Processing: {file_path.name} ---")

    # Step 1: Document -> Text
    txt_path = process_file(file_path, EXTRACTED_TEXT_DIR)
    if not txt_path:
        print(f"  [skip] Unsupported file: {file_path.name}")
        return None

    # Step 2: Text -> JSON
    result = process_text_file(txt_path, CLEANED_JSON_DIR)
    if not result:
        print(f"  [skip] Could not extract metadata from {file_path.name}")
        return None

    json_path, metadata, paper_id = result

    # Step 3: Derive branch from subject code
    metadata["branch"] = get_branch(metadata.get("subject_code"))

    # Step 4: All data -> PostgreSQL (paper + metadata + questions + subparts)
    upsert_paper(paper_id, metadata, json_path, source_file_path=file_path)

    # Step 5: Build ChromaDB vectors (if available)
    if is_chroma_available():
        try:
            import json as json_lib
            from chroma.builder import insert_paper_to_chroma

            data = json_lib.loads(json_path.read_text(encoding="utf-8"))
            count = insert_paper_to_chroma(paper_id, metadata, data.get("questions", []))
            print(f"  [chroma] {count} vectors indexed")
        except Exception as e:
            print(f"  [chroma] Warning: {e}")

    print(f"  [done] {file_path.name} -> {paper_id}")
    return paper_id


def process_folder(folder_path, max_workers=4):
    """Process all supported files in a folder concurrently."""
    folder = Path(folder_path)
    files = sorted(f for f in folder.rglob("*") if f.suffix.lower() in SUPPORTED_EXTENSIONS)

    if not files:
        print(f"No supported files found in {folder}")
        return

    print(f"Found {len(files)} file(s) in {folder}")

    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(process_single_file, f): f for f in files}

        for future in as_completed(futures):
            f = futures[future]
            try:
                paper_id = future.result()
                if paper_id:
                    results.append(paper_id)
            except Exception as e:
                print(f"  [error] {f.name}: {e}")

    print(f"\nProcessed {len(results)}/{len(files)} papers successfully.")
    return results


def watch_folder(folder_path):
    """Watch a folder and auto-process new files when they appear."""
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    folder = Path(folder_path).resolve()

    class DocHandler(FileSystemEventHandler):
        def on_created(self, event):
            if event.is_directory:
                return
            if Path(event.src_path).suffix.lower() in SUPPORTED_EXTENSIONS:
                # Small delay to let the file finish writing
                time.sleep(1)
                try:
                    process_single_file(event.src_path)
                except Exception as e:
                    print(f"  [error] Failed to process {event.src_path}: {e}")

    observer = Observer()
    observer.schedule(DocHandler(), str(folder), recursive=True)
    observer.start()

    print(f"Watching {folder} for new files (.pdf, .docx)... (Ctrl+C to stop)")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopped watching.")

    observer.join()


def main():
    parser = argparse.ArgumentParser(description="Exam Paper Processing Pipeline")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=str, help="Process a single file (PDF or .docx)")
    group.add_argument("--folder", type=str, help="Process all files in a folder")
    group.add_argument("--watch", type=str, help="Watch a folder for new files")
    parser.add_argument("--workers", type=int, default=4, help="Max parallel workers (default: 4)")

    args = parser.parse_args()

    # Initialize database tables
    print("Initializing database...")
    init_db()
    print("Database ready.\n")

    if args.file:
        process_single_file(args.file)
    elif args.folder:
        process_folder(args.folder, max_workers=args.workers)
    elif args.watch:
        # Process existing files first, then watch for new ones
        print("Processing existing files first...")
        process_folder(args.watch, max_workers=args.workers)
        print()
        watch_folder(args.watch)


if __name__ == "__main__":
    main()
