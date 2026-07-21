"""Command-line interface for the RAG ingestion pipeline.

Usage:
    python -m app.rag.cli ingest FILE [FILE ...] [--collection NAME]
    python -m app.rag.cli ingest ./docs --collection kb   # a directory

Ingests one or more files (or every supported file in a directory) into
Qdrant. Requires a running Qdrant (docker compose up -d qdrant) and an
embeddings key configured in .env.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

from app.rag import vectorstore
from app.rag.ingest import DEFAULT_COLLECTION, ingest_file
from app.rag.loaders import UnsupportedFormatError

SUPPORTED_SUFFIXES = {".pdf", ".docx", ".pptx", ".xlsx"}


def expand_paths(inputs: list[str]) -> list[Path]:
    """Turn files/dirs into a flat list of supported files."""
    files: list[Path] = []
    for raw in inputs:
        p = Path(raw)
        if p.is_dir():
            files.extend(
                sorted(f for f in p.rglob("*") if f.suffix.lower() in SUPPORTED_SUFFIXES)
            )
        elif p.is_file():
            files.append(p)
        else:
            print(f"skip (not found): {p}", file=sys.stderr)
    return files


async def ingest_paths(paths: list[Path], collection: str) -> int:
    """Ingest each path; return total chunks stored."""
    client = vectorstore.get_client()
    total = 0
    for path in paths:
        try:
            result = await ingest_file(path, client, collection=collection)
        except UnsupportedFormatError as exc:
            print(f"skip {path.name}: {exc}", file=sys.stderr)
            continue
        total += result.num_chunks
        print(f"ingested {path.name}: {result.num_chunks} chunks")
    print(f"done: {total} chunks into '{collection}'")
    return total


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="app.rag.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_cmd = sub.add_parser("ingest", help="Ingest files or directories")
    ingest_cmd.add_argument("paths", nargs="+", help="Files or directories")
    ingest_cmd.add_argument("--collection", default=DEFAULT_COLLECTION)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "ingest":
        files = expand_paths(args.paths)
        if not files:
            print("no supported files found", file=sys.stderr)
            return 1
        asyncio.run(ingest_paths(files, args.collection))
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
