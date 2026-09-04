"""What the chat refuses to carry.

The platform earns a dirham when a lead becomes a job, and only if the job goes
through the platform. A number typed into the chat is the business model
walking out of the door, so these are the cases that matter — and, just as
much, the ones that must *not* fire, because a rule that eats prices and dates
gets switched off within a week.
"""

from __future__ import annotations

import pytest

from app.core.redaction import MARK, redact


class TestNumbers:
    @pytest.mark.parametrize(
        "message",
        [
            "3eyet liya f 0612345678",
            "mon numero: 06 12 34 56 78 merci",
            "06-12-34-56-78",
            "06.12.34.56.78",
            "appelle +212 661 22 33 44",
            "00212612345678",
            "0522 33 44 55",
            "الرقم ديالي ٠٦١٢٣٤٥٦٧٨",
        ],
    )
    def test_a_phone_number_is_struck_out(self, message):
        result = redact(message)
        assert result.count == 1
        assert MARK in result.text
        assert "612345678" not in result.text.replace(" ", "")

    @pytest.mark.parametrize(
        "message", ["+33 6 12 34 56 78", "00212612345678", "212612345678"]
    )
    def test_a_foreign_number_goes_too(self, message):
        """A client abroad hiring for his mother's flat is still a lead. It
        counts when it is dialled — a country code or a trunk zero — or when
        it is written unbroken; that is what separates it from a row of
        prices, which is long in digits and neither of those things."""
        assert redact(message).count == 1

    def test_the_sentence_around_it_survives(self):
        """Refusing the message would teach people to write `zero six`."""
        result = redact("ok bghit ntfahmo, 3eyet liya 0612345678 f lmsa")
        assert result.text.startswith("ok bghit ntfahmo,")
        assert result.text.endswith("f lmsa")


class TestWhatMustNotFire:
    @pytest.mark.parametrize(
        "message",
        [
            "le prix est 450 DH pour 2 heures",
            "1500 dh, 300 dh d'avance",
            "viens le 26 aout 2026 vers 15h",
            "j'ai 3 enfants et 2 chats",
            "الثمن 1200 درهم",
            # Three prices collapse to twelve digits and look like a number.
            # A tradesman quoting a list must never be told it costs money.
            "kayn 2000 3000 4000 dh",
            "1500 2000 2500 3000 dh",
            "prix 2000dh",
            "rab3a d nhar",
            "7it ma3endich lwa9t",
            "deux cent cinquante dirhams",
            "viens vers deux ou trois heures",
            "2 m x 3 m",
        ],
    )
    def test_ordinary_talk_passes_through(self, message):
        result = redact(message)
        assert result.clean
        assert result.text == message


class TestTheWaysAround:
    def test_an_email_is_a_contact_too(self):
        result = redact("mail: karim@gmail.com")
        assert result.count == 1
        assert "gmail" not in result.text
        assert "karim@" not in result.text

    @pytest.mark.parametrize(
        "message",
        ["whatsapp wa.me/212612345678", "https://t.me/karim", "visite www.brikole.ma"],
    )
    def test_a_link_is_a_contact_too(self, message):
        assert redact(message).count == 1

    def test_a_handle_is_a_contact_too(self):
        """This product has no mentions, so an `@name` is an Instagram."""
        assert redact("@karim_plombier sur insta").count == 1

    def test_a_number_spelled_out_in_words(self):
        """The oldest trick, and the one a digit rule alone misses."""
        assert redact("zéro six un deux trois quatre cinq six sept").count == 1
        assert redact("zero six douze trente quatre cinquante six").count == 1

    def test_spelling_it_in_darija_does_not_help_either(self):
        assert redact("sifr setta wahed jouj tlata rab3a khamsa").count == 1

    def test_two_number_words_are_still_a_sentence(self):
        """"Come at two or three" must not be a redaction."""
        assert redact("nji f jouj wla tlata").clean


class TestWhatIsKept:
    def test_the_original_is_not_stored(self):
        """Keeping the number would hand it to anybody reading the table."""
        result = redact("0612345678")
        assert "0612345678" not in result.text

    def test_the_count_says_how_many_times_somebody_tried(self):
        result = redact("0612345678 wla 0698765432")
        assert result.count == 2

    def test_a_clean_message_is_returned_unchanged(self):
        message = "Salam, wach momkin tji ghedda f sbah?"
        result = redact(message)
        assert result.clean
        assert result.text == message
