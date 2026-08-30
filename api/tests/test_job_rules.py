"""The job lifecycle and the lead fee, without a database."""

from __future__ import annotations

import pytest

from app.core.enums import JobStatus, TransactionType
from app.core.job import can_move, charge_for_lead
from app.core.money import dirhams


def test_a_client_cannot_start_the_work_himself():
    assert not can_move(JobStatus.ASSIGNED, JobStatus.IN_PROGRESS, by_provider=False)
    assert can_move(JobStatus.ASSIGNED, JobStatus.IN_PROGRESS, by_provider=True)


def test_a_tradesman_cannot_confirm_his_own_job():
    """Confirming is the client saying the work happened. It is the only thing
    standing between 'he says he did it' and the job being over."""
    assert not can_move(JobStatus.DONE, JobStatus.CONFIRMED, by_provider=True)
    assert can_move(JobStatus.DONE, JobStatus.CONFIRMED, by_provider=False)


def test_a_confirmed_job_is_over_for_everyone():
    for target in JobStatus:
        assert not can_move(JobStatus.CONFIRMED, target, by_provider=True)
        assert not can_move(JobStatus.CONFIRMED, target, by_provider=False)


def test_a_cancelled_job_does_not_come_back():
    for target in JobStatus:
        assert not can_move(JobStatus.CANCELLED, target, by_provider=True)
        assert not can_move(JobStatus.CANCELLED, target, by_provider=False)


def test_the_client_cannot_walk_away_once_the_work_is_done():
    """He can dispute it or confirm it. Cancelling after the fact would be a
    way to get free work."""
    assert not can_move(JobStatus.DONE, JobStatus.CANCELLED, by_provider=False)


def test_a_free_lead_costs_nothing_and_moves_no_money():
    charge = charge_for_lead(
        free_leads_left=20, balance_centimes=dirhams(50), fee_centimes=dirhams(10)
    )
    assert charge.amount_centimes == 0
    assert charge.balance_after_centimes == dirhams(50)
    assert charge.free_leads_after == 19
    assert charge.transaction_type is TransactionType.FREE_LEAD


def test_the_fee_comes_out_of_the_balance_once_the_free_leads_are_gone():
    charge = charge_for_lead(
        free_leads_left=0, balance_centimes=dirhams(50), fee_centimes=dirhams(10)
    )
    assert charge.amount_centimes == -dirhams(10)
    assert charge.balance_after_centimes == dirhams(40)
    assert charge.transaction_type is TransactionType.LEAD_FEE
    assert not charge.went_negative


def test_a_short_balance_does_not_block_the_client():
    """The client pressed the button and cannot see, let alone fix, the
    tradesman's wallet. The debt is recorded instead."""
    charge = charge_for_lead(
        free_leads_left=0, balance_centimes=dirhams(4), fee_centimes=dirhams(10)
    )
    assert charge.balance_after_centimes == -dirhams(6)
    assert charge.went_negative
    assert charge.transaction_type is TransactionType.LEAD_FEE


def test_the_charge_always_explains_itself():
    """Every balance move carries the reason its ledger row will be written
    with — the two are decided together or the invariant is not enforced."""
    for free in (0, 3):
        charge = charge_for_lead(
            free_leads_left=free, balance_centimes=0, fee_centimes=dirhams(10)
        )
        assert charge.reason


def test_a_negative_fee_is_a_bug_not_a_refund():
    with pytest.raises(ValueError):
        charge_for_lead(free_leads_left=0, balance_centimes=0, fee_centimes=-1)
