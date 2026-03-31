from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.core.config import get_settings  # noqa: E402
from app.db.engine import dispose_engine, get_session_factory  # noqa: E402
from app.schemas.documents import GenerateDefinitionDraftRequest  # noqa: E402
from app.schemas.search import SearchRequest  # noqa: E402
from app.services.document_drafts import (  # noqa: E402
    DefinitionDraftConfigError,
    DefinitionDraftGenerationError,
    DefinitionDraftNotFoundError,
    generate_definition_draft,
    validate_generated_body,
)
from app.services.glossary import concept_public_slug, concept_search_key, refresh_glossary_concepts, resolve_concept  # noqa: E402
from app.services.search import search_documents  # noqa: E402


@dataclass(slots=True)
class CaseOutcome:
    name: str
    passed: bool
    details: dict[str, Any] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)


def _load_cases(path: Path) -> dict[str, list[dict[str, Any]]]:
    return json.loads(path.read_text(encoding="utf-8"))


def _body_without_title_and_references(markdown: str) -> str:
    body = markdown.split("## References", 1)[0].strip()
    if body.startswith("# "):
        _title, _sep, rest = body.partition("\n")
        body = rest.strip()
    return body


def _family_key_for_slug(slug: str) -> str:
    return concept_search_key(slug)


async def _evaluate_search_case(session, case: dict[str, Any]) -> CaseOutcome:
    response = await search_documents(
        session,
        SearchRequest(
            query=case["query"],
            limit=5,
            owner_team=case.get("owner_team"),
            doc_type=case.get("doc_type"),
            source_system=case.get("source_system"),
        ),
    )
    concept = await resolve_concept(session, case["query"])

    failures: list[str] = []
    if concept is None:
        failures.append("No concept resolved for query.")
    else:
        if concept_public_slug(concept) != case["expected_concept_slug"]:
            failures.append(
                f"Resolved concept slug {concept_public_slug(concept)!r} did not match expected {case['expected_concept_slug']!r}."
            )

    if case.get("require_grounded") and response.weak_grounding:
        failures.append("Search response was marked weak_grounding.")

    if not response.hits:
        failures.append("Search returned no hits.")
    else:
        first_hit = response.hits[0]
        allowed_prefixes = case.get("allowed_first_hit_slug_prefixes", [])
        if allowed_prefixes and not any(first_hit.document_slug.startswith(prefix) for prefix in allowed_prefixes):
            failures.append(
                f"First hit slug {first_hit.document_slug!r} did not match any allowed prefixes {allowed_prefixes!r}."
            )
        if (
            case.get("expect_glossary_first_if_approved")
            and concept is not None
            and concept.status == "approved"
            and concept.canonical_document_id is not None
            and first_hit.result_type != "glossary"
        ):
            failures.append("Approved concept did not rank its canonical glossary document first.")

    min_unique_families = int(case.get("min_unique_families_in_top_hits", 1))
    family_count = len({_family_key_for_slug(hit.document_slug) for hit in response.hits[:5]})
    if family_count < min_unique_families:
        failures.append(
            f"Top hits only covered {family_count} unique families; expected at least {min_unique_families}."
        )

    return CaseOutcome(
        name=case["name"],
        passed=not failures,
        details={
            "query": case["query"],
            "resolved_concept_term": response.resolved_concept_term,
            "weak_grounding": response.weak_grounding,
            "first_hit_slug": response.hits[0].document_slug if response.hits else None,
            "first_hit_type": response.hits[0].result_type if response.hits else None,
            "unique_families_in_top_hits": family_count,
        },
        failures=failures,
    )


async def _evaluate_generation_case(session, case: dict[str, Any]) -> CaseOutcome:
    failures: list[str] = []
    try:
        result = await generate_definition_draft(
            session,
            GenerateDefinitionDraftRequest(
                topic=case["topic"],
                domain=case.get("domain"),
                owner_team=case.get("owner_team"),
                doc_type=case.get("doc_type"),
                source_system=case.get("source_system"),
            ),
        )
    except DefinitionDraftNotFoundError:
        if case.get("expect_not_found"):
            return CaseOutcome(
                name=case["name"],
                passed=True,
                details={
                    "topic": case["topic"],
                    "outcome": "not_found",
                },
            )
        return CaseOutcome(
            name=case["name"],
            passed=False,
            details={"topic": case["topic"], "outcome": "not_found"},
            failures=["Definition draft generation returned not_found unexpectedly."],
        )
    except (DefinitionDraftGenerationError, DefinitionDraftConfigError) as exc:
        return CaseOutcome(
            name=case["name"],
            passed=False,
            details={"topic": case["topic"], "outcome": "generation_error"},
            failures=[str(exc)],
        )

    if case.get("expect_not_found"):
        failures.append("Definition draft generation succeeded unexpectedly.")

    if len(result.references) < int(case.get("min_references", 1)):
        failures.append(
            f"Only {len(result.references)} references were returned; expected at least {case.get('min_references', 1)}."
        )

    body = _body_without_title_and_references(result.markdown)
    try:
        validate_generated_body(body, reference_count=len(result.references))
    except Exception as exc:  # pragma: no cover - exercised in live verification
        failures.append(f"Generated body failed validation: {exc}")

    allowed_prefixes = case.get("expected_reference_slug_prefixes", [])
    if allowed_prefixes:
        matched = [
            reference.document_slug
            for reference in result.references
            if any(reference.document_slug.startswith(prefix) for prefix in allowed_prefixes)
        ]
        if not matched:
            failures.append(
                f"No reference slug matched the expected prefixes {allowed_prefixes!r}."
            )

    return CaseOutcome(
        name=case["name"],
        passed=not failures,
        details={
            "topic": case["topic"],
            "reference_count": len(result.references),
            "reference_slugs": [reference.document_slug for reference in result.references],
            "slug": result.slug,
        },
        failures=failures,
    )


async def run(args: argparse.Namespace) -> int:
    cases = _load_cases(Path(args.cases))
    settings = get_settings()

    async with get_session_factory()() as session:
        refreshed_count: int | None = None
        if args.refresh_first:
            refreshed_count = await refresh_glossary_concepts(session)
            await session.commit()

        search_outcomes = [
            await _evaluate_search_case(session, case)
            for case in cases.get("search_cases", [])
        ]

        generation_outcomes: list[CaseOutcome] = []
        generation_enabled = bool(settings.generation_model.strip())
        if args.require_generation and not generation_enabled:
            generation_outcomes.append(
                CaseOutcome(
                    name="generation_config",
                    passed=False,
                    failures=["GENERATION_MODEL is not configured."],
                )
            )
        elif generation_enabled:
            for case in cases.get("generation_cases", []):
                generation_outcomes.append(await _evaluate_generation_case(session, case))

    summary = {
        "refreshed_concepts": refreshed_count,
        "generation_enabled": generation_enabled,
        "search": [asdict(outcome) for outcome in search_outcomes],
        "generation": [asdict(outcome) for outcome in generation_outcomes],
    }
    summary["passed"] = all(item["passed"] for item in summary["search"] + summary["generation"])
    summary["failure_count"] = sum(len(item["failures"]) for item in summary["search"] + summary["generation"])

    rendered = json.dumps(summary, ensure_ascii=False, indent=2)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)
    return 0 if summary["passed"] else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run glossary/search quality evaluation against the current corpus.")
    parser.add_argument(
        "--cases",
        default=str(ROOT / "evals" / "sendy_glossary_eval.json"),
        help="Path to the evaluation case JSON file.",
    )
    parser.add_argument(
        "--refresh-first",
        action="store_true",
        help="Refresh glossary concepts from the current published corpus before running the evaluation.",
    )
    parser.add_argument(
        "--require-generation",
        action="store_true",
        help="Fail if generation settings are not configured.",
    )
    parser.add_argument(
        "--output",
        default="",
        help="Optional path to write the JSON summary.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        raise SystemExit(asyncio.run(run(args)))
    finally:
        asyncio.run(dispose_engine())


if __name__ == "__main__":
    main()
