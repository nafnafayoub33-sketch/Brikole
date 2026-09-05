"""The password an admin reads down a phone line.

Everything here follows from one fact: it is *spoken*, not copied. So the
tests are about what survives being said out loud and written down by somebody
who is already having a bad afternoon.
"""

from __future__ import annotations

from app.core.security import MAX_PASSWORD_LENGTH, MIN_PASSWORD_LENGTH, validate_password
from app.core.temp_password import ALPHABET, GROUP, GROUPS, generate

#: Enough draws that a one-in-a-few-hundred generator bug shows up here rather
#: than on a phone call.
DRAWS = 400


def test_it_reads_as_groups_of_four() -> None:
    """`ABCD-EF34-7HJK`. That is how a person says a code, and how the person
    on the other end writes it down."""
    groups = generate().split("-")
    assert len(groups) == GROUPS
    assert all(len(group) == GROUP for group in groups)


def test_no_character_sounds_like_another() -> None:
    """`0`/`O`, `1`/`l`/`I` and `5`/`S` are what turn a two-minute call into a
    five-minute one, so none of them exist here at all."""
    assert not set("O0IL1S5Z2") & set(ALPHABET)

    letters = generate().replace("-", "")
    assert set(letters) <= set(ALPHABET)


def test_it_is_upper_case() -> None:
    """"Small b or capital B" is a question nobody should have to ask."""
    password = generate()
    assert password == password.upper()


def test_every_draw_passes_the_platforms_password_policy() -> None:
    """`hash_password` runs `validate_password`, so a draw that fails it is a
    reset that fails — in front of somebody who is already locked out. The
    generator needs a letter and a digit in every single password, not in most
    of them."""
    for _ in range(DRAWS):
        password = generate()
        assert validate_password(password) == password


def test_it_fits_the_length_the_policy_allows() -> None:
    assert MIN_PASSWORD_LENGTH <= len(generate()) <= MAX_PASSWORD_LENGTH


def test_two_draws_differ() -> None:
    """Not a proof of randomness — a guard against the generator being wired to
    a constant, which is the way this breaks in practice."""
    assert len({generate() for _ in range(DRAWS)}) > DRAWS // 2
