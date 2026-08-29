"""The contract between the API's error codes and the web app's wording.

The API returns a code and never a sentence; `src/lib/i18n.ts` is where a code
becomes something a person can read. That only works if the two stay in step,
so this fails the moment a code is added on this side without the three lines
it needs on the other.

It reads the web app's source rather than importing anything from it — the two
halves share a contract, not a build.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.core.errors import ErrorCode

I18N = Path(__file__).resolve().parents[2] / "web" / "src" / "lib" / "i18n.ts"

LANGUAGES = ("ar", "fr", "en")


def error_keys_per_language() -> dict[str, set[str]]:
    """The keys under `errors:` in each language block, in file order."""
    source = I18N.read_text(encoding="utf-8")

    blocks = re.findall(r"\n  errors: \{\n(.*?)\n  \},\n", source, flags=re.DOTALL)
    assert len(blocks) == len(LANGUAGES), (
        f"expected one errors block per language, found {len(blocks)}"
    )

    return {
        language: set(re.findall(r"^\s{4}([a-z_]+):", block, flags=re.MULTILINE))
        for language, block in zip(LANGUAGES, blocks, strict=True)
    }


@pytest.mark.skipif(not I18N.exists(), reason="web app not present")
@pytest.mark.parametrize("language", LANGUAGES)
def test_every_error_code_has_wording(language: str) -> None:
    translated = error_keys_per_language()[language]
    missing = sorted(code.value for code in ErrorCode if code.value not in translated)

    assert missing == [], (
        f"{len(missing)} error code(s) would reach a user untranslated in {language!r}: "
        f"{missing}. Add them to `errors` in web/src/lib/i18n.ts."
    )


@pytest.mark.skipif(not I18N.exists(), reason="web app not present")
def test_the_three_languages_cover_the_same_codes() -> None:
    per_language = error_keys_per_language()
    assert per_language["ar"] == per_language["fr"] == per_language["en"]
