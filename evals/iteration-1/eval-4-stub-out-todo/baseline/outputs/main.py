"""Billing module (work in progress).

Stubs for card charging and refunding. Real implementation lands next sprint.
"""

from __future__ import annotations


def charge_card(amount: int) -> None:
    """Charge a card for the given amount (in minor currency units).

    Args:
        amount: Amount to charge, in the smallest currency unit (e.g. cents).
    """
    # TODO(next-sprint): Integrate with payment processor to charge the card.
    raise NotImplementedError("charge_card is not implemented yet")


def refund_card(charge_id: str) -> None:
    """Refund a previously successful charge.

    Args:
        charge_id: Identifier of the charge to refund.
    """
    # TODO(next-sprint): Look up the charge and issue a refund via the processor.
    raise NotImplementedError("refund_card is not implemented yet")
