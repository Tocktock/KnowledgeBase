from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import func, or_, select

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.utils import slugify  # noqa: E402
from app.db.engine import dispose_engine, get_session_factory  # noqa: E402
from app.db.models import Document  # noqa: E402
from app.schemas.documents import IngestDocumentRequest  # noqa: E402
from app.services.glossary import refresh_glossary_concepts  # noqa: E402
from app.services.ingest import ingest_document  # noqa: E402

MARKDOWN_SUFFIXES = {".md", ".markdown"}
CSV_SUFFIXES = {".csv"}
IGNORED_FILENAMES = {".ds_store"}
HEX_SUFFIX_PATTERN = re.compile(r"\s+([0-9a-f]{10}|[0-9a-f]{32})$", flags=re.IGNORECASE)


@dataclass(slots=True)
class CorpusFile:
    path: Path
    relative_path: str
    title: str
    slug: str
    content_type: str
    doc_type: str
    owner_team: str | None


def canonical_csv_key(relative_path: str) -> str:
    if relative_path.lower().endswith("_all.csv"):
        return relative_path[:-8] + ".csv"
    return relative_path


def select_corpus_files(root: Path) -> list[Path]:
    markdown_files: list[Path] = []
    csv_files: dict[str, Path] = {}

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name.casefold() in IGNORED_FILENAMES:
            continue

        suffix = path.suffix.lower()
        if suffix in MARKDOWN_SUFFIXES:
            markdown_files.append(path)
            continue
        if suffix not in CSV_SUFFIXES:
            continue

        relative_path = path.relative_to(root).as_posix()
        key = canonical_csv_key(relative_path)
        current = csv_files.get(key)
        if current is None:
            csv_files[key] = path
            continue
        if path.name.lower().endswith("_all.csv") and not current.name.lower().endswith("_all.csv"):
            csv_files[key] = path

    return [*markdown_files, *sorted(csv_files.values())]


def derive_title_and_slug(path: Path) -> tuple[str, str]:
    stem = path.stem
    if stem.endswith("_all"):
        stem = stem[:-4]
    match = HEX_SUFFIX_PATTERN.search(stem)
    hash_suffix = match.group(1).lower()[:10] if match else ""
    title = stem[: match.start()].strip() if match else stem.strip()
    if not title:
        title = stem.strip() or path.stem

    base_slug = slugify(title) or slugify(path.stem) or "document"
    if hash_suffix:
        return title, f"{base_slug}-{hash_suffix}"

    relative_hash = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:10]
    return title, f"{base_slug}-{relative_hash}"


def infer_owner_team(relative_path: str) -> str | None:
    lowered = relative_path.casefold()
    if "platform" in lowered:
        return "platform"
    if "/ml/" in lowered or lowered.startswith("ml/"):
        return "ml"
    if "design" in lowered:
        return "design"
    if (
        "product home" in lowered
        or "product team" in lowered
        or "/pm/" in lowered
        or "화주 스쿼드" in relative_path
        or "차주 스쿼드" in relative_path
        or "ios" in lowered
    ):
        return "product"
    return None


def build_corpus_file(root: Path, path: Path) -> CorpusFile:
    relative_path = path.relative_to(root).as_posix()
    title, slug = derive_title_and_slug(path)
    suffix = path.suffix.lower()
    return CorpusFile(
        path=path,
        relative_path=relative_path,
        title=title,
        slug=slug,
        content_type="markdown" if suffix in MARKDOWN_SUFFIXES else "text",
        doc_type="data" if suffix in CSV_SUFFIXES else "knowledge",
        owner_team=infer_owner_team(relative_path),
    )


async def existing_sample_corpus_count(root: Path, *, source_system: str) -> int:
    top_level_names = sorted(child.name for child in root.iterdir() if child.is_dir())
    if not top_level_names:
        return 0

    clauses = []
    for name in top_level_names:
        clauses.append(Document.source_external_id.ilike(f"{name}/%"))
        clauses.append(Document.source_external_id.ilike(f"%/{name}/%"))

    async with get_session_factory()() as session:
        result = await session.execute(
            select(func.count(Document.id)).where(
                Document.source_system == source_system,
                Document.source_external_id.is_not(None),
                or_(*clauses),
            )
        )
        return int(result.scalar_one())


async def import_corpus(
    *,
    root: Path,
    source_system: str,
    import_batch: str,
    refresh_glossary: bool,
    skip_if_detected: bool,
    detection_threshold: int,
) -> dict[str, object]:
    if skip_if_detected:
        existing_count = await existing_sample_corpus_count(root, source_system=source_system)
        if existing_count >= detection_threshold:
            return {
                "root": str(root),
                "selected_files": 0,
                "imported": 0,
                "unchanged": 0,
                "skipped_existing_corpus": True,
                "detected_existing_documents": existing_count,
                "refreshed_concepts": None,
            }

    selected_paths = select_corpus_files(root)
    files = [build_corpus_file(root, path) for path in selected_paths]

    imported = 0
    unchanged = 0
    for index, file in enumerate(files, start=1):
        content = file.path.read_text(encoding="utf-8-sig", errors="ignore").strip()
        if not content:
            continue
        payload = IngestDocumentRequest(
            source_system=source_system,
            source_external_id=file.relative_path,
            source_url=None,
            slug=file.slug,
            title=file.title,
            content_type=file.content_type,  # type: ignore[arg-type]
            content=content,
            doc_type=file.doc_type,
            language_code="ko",
            owner_team=file.owner_team,
            status="published",
            priority=120,
            metadata={
                "corpus_key": "sendy-knowledge",
                "import_batch": import_batch,
                "relative_path": file.relative_path,
                "file_ext": file.path.suffix.lower(),
            },
        )
        async with get_session_factory()() as session:
            result = await ingest_document(session, payload)
        if result.unchanged:
            unchanged += 1
        else:
            imported += 1
        if index % 250 == 0:
            print(
                json.dumps(
                    {
                        "event": "progress",
                        "processed": index,
                        "total": len(files),
                        "imported": imported,
                        "unchanged": unchanged,
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

    refreshed_concepts: int | None = None
    if refresh_glossary:
        async with get_session_factory()() as session:
            refreshed_concepts = await refresh_glossary_concepts(session)
            await session.commit()

    return {
        "root": str(root),
        "selected_files": len(files),
        "imported": imported,
        "unchanged": unchanged,
        "skipped_existing_corpus": False,
        "detected_existing_documents": 0,
        "refreshed_concepts": refreshed_concepts,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import the local sample corpus into the running knowledge base.")
    parser.add_argument("--root", required=True, help="Absolute path to the sample corpus root directory.")
    parser.add_argument("--source-system", default="notion-export", help="Source system name for imported documents.")
    parser.add_argument(
        "--import-batch",
        default="sample-data-sendy-knowledge",
        help="Stable metadata marker for this corpus import batch.",
    )
    parser.add_argument(
        "--refresh-glossary",
        action="store_true",
        help="Run a direct glossary refresh after import completes.",
    )
    parser.add_argument(
        "--skip-if-detected",
        action="store_true",
        help="Skip the import when an existing Sendy-like notion-export corpus is already present.",
    )
    parser.add_argument(
        "--detection-threshold",
        type=int,
        default=100,
        help="Minimum matching document count required to treat the sample corpus as already imported.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root).expanduser().resolve()
    if not root.is_dir():
        raise SystemExit(f"Sample corpus root not found: {root}")

    try:
        result = asyncio.run(
            import_corpus(
                root=root,
                source_system=args.source_system,
                import_batch=args.import_batch,
                refresh_glossary=args.refresh_glossary,
                skip_if_detected=args.skip_if_detected,
                detection_threshold=args.detection_threshold,
            )
        )
        print(json.dumps(result, ensure_ascii=False, indent=2))
        raise SystemExit(0)
    finally:
        asyncio.run(dispose_engine())


if __name__ == "__main__":
    main()
