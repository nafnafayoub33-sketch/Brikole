"""A password an admin reads down a phone line.

P6 tells people an admin resets their password, so this is what he hands them.
That single fact — **it is spoken, not copied** — decides everything here:

* No character that sounds like another. `0`/`O`, `1`/`l`/`I` and `5`/`S` are
  the pairs that turn a two-minute call into a five-minute one, so none of
  them are in the alphabet at all.
* Upper case only. "Small b or capital B" is a question nobody should have to
  ask, and a Moroccan keyboard is being used by somebody who is stressed.
* Grouped in fours, because that is how a person says a code out loud, and it
  is how the person on the other end writes it down.

It is generated rather than chosen by the admin: an admin inventing passwords
all day invents `brikole2026` on the third one.
"""

from __future__ import annotations

import secrets

#: What survives being read aloud. `O`, `I`, `L`, `S`, `Z` and the digits they
#: are confused with are all gone — the alphabet is smaller and the calls are
#: shorter.
ALPHABET = "ABCDEFGHJKMNPQRTUVWXY34679"

GROUP = 4
GROUPS = 3

#: Long enough to be worth generating, short enough to say once. Three groups
#: of four from a 26-character alphabet is about 56 bits, and it lives for as
#: long as it takes somebody to sign in and change it.
LENGTH = GROUP * GROUPS


def generate() -> str:
    """A one-time password, in groups of four: `ABCD-EF34-7HJK`.

    `secrets`, never `random`: this is a credential, and the difference
    between the two modules is whether it is guessable from another one.

    It is drawn again until it holds both a letter and a digit, because
    `core.security.validate_password` demands both and `hash_password` runs it.
    A generator that can emit a password the platform then refuses to hash is a
    reset that fails once in a few hundred calls — which is to say, on a phone
    call, in front of somebody who is already locked out. Redrawing keeps every
    character uniform; taking the failure and patching a digit in would not.
    """
    while True:
        letters = "".join(secrets.choice(ALPHABET) for _ in range(LENGTH))
        if any(c.isalpha() for c in letters) and any(c.isdigit() for c in letters):
            return "-".join(
                letters[index : index + GROUP] for index in range(0, LENGTH, GROUP)
            )
