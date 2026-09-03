"""The handshake, with no database in sight.

One rule carries the whole design: you do not sign "the deal", you sign a
version of it. Everything here is a way of checking that a signature never
survives the thing it was given for.
"""

from __future__ import annotations

import pytest

from app.core.errors import DomainError, ErrorCode
from app.core.money import dirhams
from app.core.negotiation import TERMS_MAX, Terms, agree, propose, validate_terms, withdraw


def opening(price: int = dirhams(400)) -> Terms:
    return Terms(
        price_centimes=price,
        terms="",
        version=1,
        client_agreed_version=None,
        provider_agreed_version=None,
    )


def code(excinfo: pytest.ExceptionInfo[DomainError]) -> ErrorCode:
    return excinfo.value.code


class TestSigning:
    def test_one_signature_is_not_a_deal(self):
        signed = agree(opening(), as_client=True, version=1)
        assert signed.client_has_agreed
        assert not signed.provider_has_agreed
        assert not signed.sealed

    def test_both_on_the_same_version_seals_it(self):
        signed = agree(opening(), as_client=True, version=1)
        signed = agree(signed, as_client=False, version=1)
        assert signed.sealed

    def test_signing_a_version_that_has_moved_is_refused(self):
        """The screen he pressed on was showing a different price."""
        with pytest.raises(DomainError) as excinfo:
            agree(opening(), as_client=True, version=3)
        assert code(excinfo) is ErrorCode.CONFLICT

    def test_signing_twice_is_refused(self):
        signed = agree(opening(), as_client=True, version=1)
        with pytest.raises(DomainError) as excinfo:
            agree(signed, as_client=True, version=1)
        assert code(excinfo) is ErrorCode.CONFLICT


class TestMovingThePrice:
    def test_a_proposal_bumps_the_version(self):
        moved = propose(opening(), price_centimes=dirhams(500), terms="")
        assert moved.version == 2
        assert moved.price_centimes == dirhams(500)

    def test_a_proposal_clears_a_signature_already_given(self):
        """The whole point. He agreed to 400, not to the 500 typed after."""
        signed = agree(opening(), as_client=True, version=1)
        assert signed.client_has_agreed

        moved = propose(signed, price_centimes=dirhams(500), terms="")
        assert not moved.client_has_agreed
        assert not moved.sealed

    def test_a_proposal_does_not_count_as_its_own_signature(self):
        """Otherwise one side could move the price after the other had signed
        and have the job created on the spot, at his new number."""
        signed = agree(opening(), as_client=False, version=1)
        moved = propose(signed, price_centimes=dirhams(500), terms="")
        assert not moved.provider_has_agreed
        assert not moved.client_has_agreed

    def test_changing_only_the_terms_is_still_a_new_version(self):
        moved = propose(opening(), price_centimes=dirhams(400), terms="Matériel inclus")
        assert moved.version == 2
        assert moved.terms == "Matériel inclus"

    def test_proposing_what_is_already_on_the_table_is_refused(self):
        """It would clear both signatures and change nothing — a way to undo
        somebody else's agreement by pressing send twice."""
        with pytest.raises(DomainError) as excinfo:
            propose(opening(), price_centimes=dirhams(400), terms="")
        assert code(excinfo) is ErrorCode.CONFLICT

    def test_a_price_of_zero_is_refused(self):
        with pytest.raises(DomainError) as excinfo:
            propose(opening(), price_centimes=0, terms="")
        assert code(excinfo) is ErrorCode.AMOUNT_INVALID


class TestTakingItBack:
    def test_a_signature_can_be_withdrawn_while_the_other_side_waits(self):
        signed = agree(opening(), as_client=True, version=1)
        assert not withdraw(signed, as_client=True).client_has_agreed

    def test_withdrawing_does_not_touch_the_other_side(self):
        signed = agree(opening(), as_client=True, version=1)
        signed = withdraw(signed, as_client=True)
        assert signed.provider_agreed_version is None

    def test_a_sealed_deal_is_not_taken_back_here(self):
        """Money has moved and a job exists. That is a cancellation, on C4."""
        signed = agree(opening(), as_client=True, version=1)
        signed = agree(signed, as_client=False, version=1)

        with pytest.raises(DomainError) as excinfo:
            withdraw(signed, as_client=True)
        assert code(excinfo) is ErrorCode.CONFLICT


class TestTerms:
    def test_terms_may_be_empty(self):
        assert validate_terms("   ") == ""

    def test_terms_are_trimmed(self):
        assert validate_terms("  Matériel inclus  ") == "Matériel inclus"

    def test_a_page_is_the_limit(self):
        with pytest.raises(DomainError) as excinfo:
            validate_terms("x" * (TERMS_MAX + 1))
        assert code(excinfo) is ErrorCode.VALIDATION_FAILED
