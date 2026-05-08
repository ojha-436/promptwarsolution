"""Pydantic model validation — the boundary that protects everything else."""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from app.models import Constraints, Preferences, TripRequest


def test_dates_must_be_ordered():
    with pytest.raises(ValidationError):
        TripRequest(
            destination="Goa",
            start_date=date(2026, 6, 5),
            end_date=date(2026, 6, 1),
            travelers=2,
            constraints=Constraints(budget_total_inr=20000),
        )


def test_max_days_enforced():
    with pytest.raises(ValidationError):
        TripRequest(
            destination="Goa",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 8, 1),
            travelers=2,
            constraints=Constraints(budget_total_inr=20000),
        )


def test_unknown_field_rejected_in_constraints():
    with pytest.raises(ValidationError):
        Constraints(budget_total_inr=20000, malicious="payload")  # type: ignore[call-arg]


def test_minimum_budget():
    with pytest.raises(ValidationError):
        Constraints(budget_total_inr=10)


def test_too_many_travelers():
    with pytest.raises(ValidationError):
        TripRequest(
            destination="Goa",
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 5),
            travelers=20,
            constraints=Constraints(budget_total_inr=20000),
        )


def test_destination_stripped():
    req = TripRequest(
        destination="  Jaipur  ",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 3),
        travelers=2,
        preferences=Preferences(),
        constraints=Constraints(budget_total_inr=20000),
    )
    assert req.destination == "Jaipur"
