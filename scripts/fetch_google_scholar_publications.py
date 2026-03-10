#!/usr/bin/env python3
"""Fetch ORCID publications and generate markdown files for Academic Pages."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import requests

AUTHOR_NAME = "HINAYAH Rojas de Oliveira"
OUTPUT_DIR = Path("_publications")
GENERATED_NAME_MARKER = "-gs-"
MIN_PUBLICATION_YEAR = 2024
ORCID_API_BASE = "https://pub.orcid.org/v3.0"
OPENALEX_API_BASE = "https://api.openalex.org"
REQUEST_TIMEOUT_SECONDS = 30


@dataclass
class Publication:
    year: int
    title: str
    venue: str
    citation: str
    paper_url: str


def get_orcid_id() -> str:
    orcid_id = os.getenv("ORCID_ID", "").strip()
    if not orcid_id:
        return ""
    if not re.match(r"^\d{4}-\d{4}-\d{4}-[\dX]{4}$", orcid_id):
        raise RuntimeError("ORCID_ID format is invalid. Expected 0000-0000-0000-0000.")
    return orcid_id


def safe_slug(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return cleaned[:80] or "untitled"


def build_venue(bib: dict) -> str:
    value = str(bib.get("journal_title", "")).strip()
    if value:
        return value
    value = str(bib.get("type", "")).strip()
    if value:
        return value.replace("-", " ").title()
    return "Unknown venue"


def build_citation(author_name: str, year: int, title: str, venue: str) -> str:
    return f"{author_name.title()} ({year}). {title}. {venue}."


def yaml_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace('"', '\\"').replace("'", "&apos;")


def extract_best_url(external_ids: list[dict]) -> str:
    doi_value = ""
    for ext in external_ids:
        ext_type = str(ext.get("external-id-type", "")).lower()
        value = str(ext.get("external-id-value", "")).strip()
        if ext_type == "doi" and value:
            doi_value = value
            break
    if doi_value:
        return f"https://doi.org/{doi_value}"
    return ""


def publication_from_work_summary(summary: dict, author_name: str) -> Publication | None:
    title_obj = (((summary.get("title") or {}).get("title") or {}).get("value"))
    title = str(title_obj or "").strip()

    pub_date = summary.get("publication-date") or {}
    year_obj = (pub_date.get("year") or {}).get("value")
    year_str = str(year_obj or "").strip()

    if not title or not year_str.isdigit():
        return None

    year = int(year_str)
    venue = build_venue(
        {
            "journal_title": ((summary.get("journal-title") or {}).get("value") or ""),
            "type": summary.get("type", ""),
        }
    )

    external_ids = ((summary.get("external-ids") or {}).get("external-id") or [])
    paper_url = extract_best_url(external_ids)
    citation = build_citation(author_name, year, title, venue)

    return Publication(
        year=year,
        title=title,
        venue=venue,
        citation=citation,
        paper_url=paper_url,
    )


def fetch_orcid_works(orcid_id: str) -> list[dict]:
    headers = {"Accept": "application/json"}
    response = requests.get(
        f"{ORCID_API_BASE}/{orcid_id}/works",
        headers=headers,
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()

    summaries: list[dict] = []
    for group in data.get("group", []):
        work_summaries = group.get("work-summary", [])
        for summary in work_summaries:
            summaries.append(summary)

    return summaries


def pick_openalex_author_id(author_name: str) -> str:
    response = requests.get(
        f"{OPENALEX_API_BASE}/authors",
        params={"search": author_name, "per-page": 10},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    results = response.json().get("results", [])
    if not results:
        return ""

    target = normalize_name(author_name)
    best_id = ""
    best_score = -1

    for item in results:
        display = normalize_name(str(item.get("display_name", "")))
        if not display:
            continue

        score = 0
        if display == target:
            score += 100
        if target in display or display in target:
            score += 50

        if "rojas" in display:
            score += 10

        works_count = int(item.get("works_count", 0) or 0)
        score += min(works_count, 40)

        if score > best_score:
            best_score = score
            best_id = str(item.get("id", ""))

    return best_id


def publication_from_openalex_work(work: dict, author_name: str) -> Publication | None:
    title = str(work.get("title", "")).strip()
    year = work.get("publication_year")
    if not title or not isinstance(year, int):
        return None

    source = ((work.get("primary_location") or {}).get("source") or {})
    venue = str(source.get("display_name", "")).strip() or "Unknown venue"

    doi = str((work.get("ids") or {}).get("doi", "")).strip()
    if doi and doi.startswith("https://"):
        paper_url = doi
    elif doi and doi.startswith("doi:"):
        paper_url = f"https://doi.org/{doi.split(':', 1)[1]}"
    elif doi:
        paper_url = f"https://doi.org/{doi}"
    else:
        paper_url = str((work.get("primary_location") or {}).get("landing_page_url", "")).strip()

    citation = build_citation(author_name, year, title, venue)
    return Publication(year=year, title=title, venue=venue, citation=citation, paper_url=paper_url)


def fetch_openalex_publications(author_name: str) -> list[Publication]:
    author_id = pick_openalex_author_id(author_name)
    if not author_id:
        return []

    response = requests.get(
        f"{OPENALEX_API_BASE}/works",
        params={
            "filter": f"author.id:{author_id},from_publication_date:{MIN_PUBLICATION_YEAR}-01-01",
            "sort": "publication_date:asc",
            "per-page": 200,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    results = response.json().get("results", [])

    publications: list[Publication] = []
    for item in results:
        pub = publication_from_openalex_work(item, author_name)
        if pub and pub.year >= MIN_PUBLICATION_YEAR:
            publications.append(pub)

    return publications


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
        orcid_id = get_orcid_id()
        publications: list[Publication] = []

        if orcid_id:
            works = fetch_orcid_works(orcid_id)
            print(f"Fetched {len(works)} ORCID work summaries for {orcid_id}.")

            for work_summary in works:
                pub = publication_from_work_summary(work_summary, AUTHOR_NAME)
                if pub and pub.year >= MIN_PUBLICATION_YEAR:
                    publications.append(pub)
        else:
            print("ORCID_ID not set; skipping ORCID source.")

        if not publications:
            print("Falling back to OpenAlex by author name.")
            publications = fetch_openalex_publications(AUTHOR_NAME)
            print(f"Fetched {len(publications)} publications from OpenAlex.")

        publications.sort(key=lambda item: (item.year, item.title.lower()))

        if not publications:
            print(
                f"No ORCID publications found for year >= {MIN_PUBLICATION_YEAR}; nothing to update."
            )
            return 0

        written = write_publications(publications, OUTPUT_DIR)
        print(f"Generated {written} publication files in {OUTPUT_DIR}")
        return 0

    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
