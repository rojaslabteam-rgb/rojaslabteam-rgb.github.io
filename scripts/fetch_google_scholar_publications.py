#!/usr/bin/env python3
"""Fetch Google Scholar publications for a target author and generate markdown files.

This script searches Google Scholar by author name, fetches publications, and writes
Academic Pages publication markdown files into _publications.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from scholarly import scholarly

AUTHOR_NAME = "HINAYAH ROJAS DE OLIVEIRA"
OUTPUT_DIR = Path("_publications")
GENERATED_NAME_MARKER = "-gs-"


@dataclass
class Publication:
    year: int
    title: str
    venue: str
    citation: str
    paper_url: str


def normalize_name(text: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def pick_author(author_name: str) -> dict:
    target = normalize_name(author_name)
    matches = scholarly.search_author(author_name)

    best = None
    for candidate in matches:
        candidate_name = normalize_name(candidate.get("name", ""))
        if candidate_name == target:
            return candidate
        if target in candidate_name or candidate_name in target:
            best = best or candidate

    if best:
        return best

    raise RuntimeError(f"No Google Scholar author found for: {author_name}")


def safe_slug(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return cleaned[:80] or "untitled"


def build_venue(bib: dict) -> str:
    for key in ("journal", "conference", "booktitle", "publisher"):
        value = str(bib.get(key, "")).strip()
        if value:
            return value
    return "Unknown venue"


def build_citation(author_name: str, year: int, title: str, venue: str) -> str:
    return f"{author_name.title()} ({year}). {title}. {venue}."


def yaml_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("'", "&apos;")


def publication_from_entry(entry: dict, author_name: str) -> Publication | None:
    bib = entry.get("bib", {})
    title = str(bib.get("title", "")).strip()
    year_str = str(bib.get("pub_year", "")).strip()

    if not title or not year_str.isdigit():
        return None

    year = int(year_str)
    venue = build_venue(bib)
    paper_url = str(entry.get("pub_url", "")).strip()
    citation = build_citation(author_name, year, title, venue)

    return Publication(
        year=year,
        title=title,
        venue=venue,
        citation=citation,
        paper_url=paper_url,
    )


def markdown_for_publication(pub: Publication, slug: str) -> str:
    filename_stub = f"{pub.year:04d}-01-01-{slug}"

    lines = [
        "---",
        f'title: "{yaml_escape(pub.title)}"',
        "collection: publications",
        "category: manuscripts",
        f"permalink: /publication/{filename_stub}",
        f"date: {pub.year:04d}-01-01",
        f"venue: '{yaml_escape(pub.venue)}'",
    ]

    if pub.paper_url:
        lines.append(f"paperurl: '{pub.paper_url}'")

    lines.extend(
        [
            f"citation: '{yaml_escape(pub.citation)}'",
            "---",
            "",
            "<!-- generated: google-scholar-sync -->",
            "",
        ]
    )

    if pub.paper_url:
        lines.append(f"<a href='{pub.paper_url}'>View publication</a>")
        lines.append("")

    lines.append(f"Recommended citation: {pub.citation}")
    lines.append("")

    return "\n".join(lines)


def remove_old_generated_files(output_dir: Path) -> None:
    for path in output_dir.glob(f"*{GENERATED_NAME_MARKER}*.md"):
        path.unlink()


def write_publications(publications: Iterable[Publication], output_dir: Path) -> int:
    output_dir.mkdir(parents=True, exist_ok=True)
    remove_old_generated_files(output_dir)

    count = 0
    for pub in publications:
        slug = f"gs-{safe_slug(pub.title)}"
        file_name = f"{pub.year:04d}-01-01-{slug}.md"
        file_path = output_dir / file_name
        file_path.write_text(markdown_for_publication(pub, slug), encoding="utf-8")
        count += 1

    return count


def main() -> int:
    try:
        author = pick_author(AUTHOR_NAME)
        filled_author = scholarly.fill(author, sections=["publications"], sortby="year")

        publications: list[Publication] = []
        for raw_pub in filled_author.get("publications", []):
            try:
                detailed = scholarly.fill(raw_pub)
            except Exception:
                detailed = raw_pub

            pub = publication_from_entry(detailed, AUTHOR_NAME)
            if pub:
                publications.append(pub)

        publications.sort(key=lambda item: (item.year, item.title.lower()))

        if not publications:
            raise RuntimeError("No publications were found from Google Scholar.")

        written = write_publications(publications, OUTPUT_DIR)
        print(f"Generated {written} publication files in {OUTPUT_DIR}")
        return 0

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
