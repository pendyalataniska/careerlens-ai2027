import json
import logging
import re
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING

from app.core.config import PROJECT_ROOT, get_settings

if TYPE_CHECKING:
    from spacy.language import Language

_TOKEN_BOUNDARY = r"(?<![\w+#.]){term}(?![\w+#.])"
logger = logging.getLogger(__name__)


@lru_cache(maxsize=4)
def _load_nlp(model_name: str) -> "Language | None":
    try:
        import spacy
    except (ImportError, OSError) as exc:
        logger.warning(
            "spaCy is unavailable; using exact taxonomy matching without NLP segmentation",
            extra={"model_name": model_name, "error_type": type(exc).__name__},
        )
        return None

    try:
        nlp = spacy.load(model_name, disable=["ner", "parser", "lemmatizer"])
    except OSError:
        # A blank English tokenizer still provides spaCy NLP tokenization without
        # downloading an implicit model or inventing semantic entities.
        logger.warning(
            "Configured spaCy model is unavailable; using blank English NLP pipeline",
            extra={"model_name": model_name},
        )
        nlp = spacy.blank("en")
    if "sentencizer" not in nlp.pipe_names and "senter" not in nlp.pipe_names:
        nlp.add_pipe("sentencizer")
    return nlp


def _taxonomy_path(configured_path: Path | None) -> Path:
    path = configured_path or PROJECT_ROOT / "backend" / "app" / "ml" / "skill_taxonomy.json"
    return path if path.is_absolute() else PROJECT_ROOT / path


@lru_cache(maxsize=4)
def _load_taxonomy(path_string: str, modified_ns: int) -> dict[str, tuple[str, ...]]:
    del modified_ns
    path = Path(path_string)
    try:
        raw_taxonomy = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to load skill taxonomy: {path}") from exc
    if not isinstance(raw_taxonomy, dict):
        raise RuntimeError("Skill taxonomy must be a JSON object.")

    taxonomy: dict[str, tuple[str, ...]] = {}
    for canonical, aliases in raw_taxonomy.items():
        if not isinstance(canonical, str) or not canonical.strip():
            raise RuntimeError("Skill taxonomy names must be non-empty strings.")
        if not isinstance(aliases, list) or not all(
            isinstance(alias, str) for alias in aliases
        ):
            raise RuntimeError(f"Aliases for {canonical!r} must be a list of strings.")
        taxonomy[canonical.strip()] = tuple(
            dict.fromkeys((canonical.strip(), *(alias.strip() for alias in aliases if alias.strip())))
        )
    return taxonomy


def load_skill_taxonomy(path: Path | None = None) -> dict[str, tuple[str, ...]]:
    taxonomy_path = _taxonomy_path(path or get_settings().skill_taxonomy_path)
    try:
        modified_ns = taxonomy_path.stat().st_mtime_ns
    except OSError as exc:
        raise RuntimeError(f"Unable to access skill taxonomy: {taxonomy_path}") from exc
    return _load_taxonomy(str(taxonomy_path), modified_ns)


def extract_skills(text: str, taxonomy_path: Path | None = None) -> list[str]:
    nlp = _load_nlp(get_settings().spacy_model)
    if nlp is None:
        sentences = [(0, text)]
    else:
        document = nlp(text)
        sentences = [(sentence.start_char, sentence.text) for sentence in document.sents]
    matches: list[tuple[int, int, str]] = []
    for canonical, aliases in load_skill_taxonomy(taxonomy_path).items():
        for alias in aliases:
            escaped = re.escape(alias.casefold()).replace(r"\ ", r"\s+")
            for sentence_start, sentence_text in sentences:
                for match in re.finditer(
                    _TOKEN_BOUNDARY.format(term=escaped), sentence_text.casefold()
                ):
                    matches.append(
                        (
                            sentence_start + match.start(),
                            sentence_start + match.end(),
                            canonical,
                        )
                    )

    # Keep one canonical match per overlapping text span and preserve source order.
    matches.sort(key=lambda item: (item[0], -(item[1] - item[0]), item[2].casefold()))
    found: list[str] = []
    occupied_until = -1
    for start, end, canonical in matches:
        if start < occupied_until:
            continue
        occupied_until = end
        if canonical.casefold() not in {skill.casefold() for skill in found}:
            found.append(canonical)
    return found


def spacy_available() -> bool:
    return _load_nlp(get_settings().spacy_model) is not None
