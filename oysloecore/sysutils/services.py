from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from django.db import transaction


INVITER_POINTS = 50
INVITEE_POINTS = 5
INVITER_CASH = Decimal('10.00')
INVITEE_CASH = Decimal('2.00')


@dataclass
class ReferralResult:
	inviter_id: int
	invitee_id: int
	inviter_points: int
	invitee_points: int
	inviter_cash: Decimal
	invitee_cash: Decimal


def apply_referral_bonus(*, inviter, invitee) -> ReferralResult:
	"""Apply referral bonuses to inviter and invitee.
	- Inviter: +50 points and +GHS10 cash
	- Invitee: +5 points and +GHS2 cash
	This function is idempotent per pair if guarded by the caller (e.g., only on first signup with code).
	"""
	from accounts.models import Wallet  # local import to avoid circulars

	with transaction.atomic():
		inviter.add_points(INVITER_POINTS)
		invitee.add_points(INVITEE_POINTS)

		inviter_wallet, _ = Wallet.objects.get_or_create(user=inviter)
		invitee_wallet, _ = Wallet.objects.get_or_create(user=invitee)

		inviter_wallet.deposit(INVITER_CASH)
		invitee_wallet.deposit(INVITEE_CASH)

	return ReferralResult(
		inviter_id=inviter.id,
		invitee_id=invitee.id,
		inviter_points=INVITER_POINTS,
		invitee_points=INVITEE_POINTS,
		inviter_cash=INVITER_CASH,
		invitee_cash=INVITEE_CASH,
	)