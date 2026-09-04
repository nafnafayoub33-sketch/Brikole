"""Keeping contact details out of the chat.

The platform charges one dirham when a lead turns into a job, and it can only
charge it if the job goes through the platform. A phone number typed into the
chat before the two sides shake hands is the whole business model walking out
of the door: they call each other, they agree on the pavement, and nothing was
ever accepted.

So the chat carries the negotiation and nothing that would end it early. A
message that contains a number, an email or a link is **still delivered** —
with the contact struck out of it. Refusing the message instead would teach
people to write `zero six` and would lose the sentence around it; striking it
out keeps the conversation and makes the rule obvious the first time it fires.

**This is a deterrent, not a wall,** and it is worth being honest about which:
somebody determined can photograph a business card or spell a number across
three messages. The wall is elsewhere and it is structural — the tradesman's
phone number is on the job payload and on nothing that exists before it. This
module raises the cost of the shortcut; the schema is what makes it pointless.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

#: What replaces a struck-out contact. The web app renders it as a chip, so it
#: is a marker rather than a row of asterisks somebody could mistake for typing.
MARK = "[###]"

#: Arabic-Indic and Eastern Arabic digits, so a number typed on an Arabic
#: keyboard is not a hole in the rule.
_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")

#: Digits, optionally split by the things people split them with.
_MAYBE_NUMBER = re.compile(r"\+?\d[\d\s./\-()]{5,}\d")

#: Moroccan landline and mobile, with or without the country code.
_MOROCCAN = re.compile(r"^(?:\+?212|00212|0)?[5-7]\d{8}$")

#: A run this long is a phone number rather than a quantity — but only when
#: it is written as one. `2000 3000 4000` is three prices, and it collapses to
#: twelve digits like a number would.
_LONG_ENOUGH = 9

#: How a number that is not Moroccan still announces itself: a country code, or
#: a national trunk zero. Without one of these a long run has to be unbroken to
#: count, which is what keeps a list of prices out of it.
_DIALS = re.compile(r"^(?:\+|00|0)")

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+", re.UNICODE)

#: A link, with or without a scheme. `wa.me/2126…` is the shortcut this exists
#: for; a domain with a slash after it is the general case.
_LINK = re.compile(
    r"(?:https?://|www\.)\S+|\b[\w-]+\.(?:com|net|org|ma|me|io|co|fr|link)\b\S*",
    re.IGNORECASE,
)

#: Social handles: `@someone` is an Instagram or a Telegram, not a mention —
#: this product has no mentions.
_HANDLE = re.compile(r"(?<![\w])@[A-Za-z0-9._]{3,}")

#: Number words, for the oldest trick in the book: "zero six, twelve, …".
#: The tens and the teens matter as much as the units: a French number is read
#: in pairs — "zéro six, douze, trente-quatre, cinquante-six" — and a list that
#: stops at ten catches none of it.
_WORDS = {
    # fr
    "zero", "zéro", "un", "une", "deux", "trois", "quatre", "cinq", "six",
    "sept", "huit", "neuf", "dix",
    "onze", "douze", "treize", "quatorze", "quinze", "seize",
    "vingt", "vingts", "trente", "quarante", "cinquante", "soixante", "cent",
    # en
    "oh", "one", "two", "three", "four", "five", "seven", "eight", "nine", "ten",
    # ar / darija, as typed in Arabic and in Latin letters
    "صفر", "واحد", "جوج", "زوج", "اثنين", "تلاتة", "ثلاثة", "ربعة", "أربعة",
    "خمسة", "ستة", "سبعة", "تمنية", "ثمانية", "تسعة", "عشرة",
    "sifr", "wahed", "jouj", "zouj", "tlata", "rab3a", "khamsa", "setta",
    "sab3a", "tmanya", "tes3a", "3achra",
}

#: How many number words in a row stop being a sentence and start being a
#: phone number. Six is comfortably past "come at two or three".
_WORD_RUN = 6

#: Letters *and* digits, because Darija written in Latin letters spells with
#: them: `rab3a`, `7it`, `9al`. A tokeniser that stopped at the `3` would cut
#: "sifr setta wahed jouj tlata rab3a khamsa" in half and see two short runs
#: where there is one phone number.
_WORD_TOKEN = re.compile(r"[^\W_]+", re.UNICODE)


@dataclass(frozen=True, slots=True)
class Redacted:
    """The message as it will be stored, and how much was taken out of it.

    The original is deliberately **not** kept. Storing the number the rule just
    struck out would hand it to anybody who reads the table and make the whole
    exercise theatre; the count is enough for a moderator to see that somebody
    kept trying.
    """

    text: str
    count: int

    @property
    def clean(self) -> bool:
        return self.count == 0


def redact(message: str) -> Redacted:
    """Strike every contact detail out of one message."""
    removed = 0

    def strike(_match: re.Match[str]) -> str:
        nonlocal removed
        removed += 1
        return MARK

    text = message.translate(_DIGITS)

    # Emails before links, and both before the number rule. An email contains
    # a domain, so a link rule that ran first would strike `gmail.com` out of
    # `karim@gmail.com` and leave `karim@` sitting there readable.
    text = _EMAIL.sub(strike, text)
    text = _LINK.sub(strike, text)
    text = _HANDLE.sub(strike, text)

    def strike_number(match: re.Match[str]) -> str:
        raw = match.group()
        digits = re.sub(r"\D", "", raw)

        if _MOROCCAN.match(digits):
            return strike(match)

        if len(digits) >= _LONG_ENOUGH and (
            _DIALS.match(raw.strip()) or digits == raw.strip()
        ):
            # Long, and either dialled or written unbroken. A row of prices is
            # neither, and a tradesman quoting three of them must not be told
            # his message costs money.
            return strike(match)

        return match.group()

    text = _MAYBE_NUMBER.sub(strike_number, text)
    text, spelled = _strike_spelled_out(text)

    return Redacted(text=text, count=removed + spelled)


def _strike_spelled_out(text: str) -> tuple[str, int]:
    """`zéro six douze…` is a phone number written to get past a regex."""
    tokens = list(_WORD_TOKEN.finditer(text))
    if len(tokens) < _WORD_RUN:
        return text, 0

    runs: list[tuple[int, int]] = []
    start: int | None = None
    length = 0

    for index, token in enumerate(tokens):
        if token.group().casefold() in _WORDS:
            if start is None:
                start = index
            length += 1
            continue
        if start is not None and length >= _WORD_RUN:
            runs.append((tokens[start].start(), tokens[index - 1].end()))
        start, length = None, 0

    if start is not None and length >= _WORD_RUN:
        runs.append((tokens[start].start(), tokens[-1].end()))

    if not runs:
        return text, 0

    out = []
    cursor = 0
    for begin, end in runs:
        out.append(text[cursor:begin])
        out.append(MARK)
        cursor = end
    out.append(text[cursor:])

    return "".join(out), len(runs)
