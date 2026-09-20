"""Expense-split and settle-up arithmetic.

Pure integer-cent maths, no Workers or JS imports, so it can be unit-tested
with plain CPython.

The split rule here is the provisional default: split an expense equally
across the members it covers. The syndicate's real payout rules (weighting by
fixture tier, crediting members who benched a seat) are still being decided;
when they land, ``split_equally`` is the one function that changes.
"""


def split_equally(amount_cents, member_ids):
    """Split ``amount_cents`` across ``member_ids`` as evenly as integers allow.

    The remainder is handed out one cent at a time in ``member_ids`` order, so
    the shares always add back up to the original amount and the same inputs
    always produce the same result.
    """
    if amount_cents < 0:
        raise ValueError("amount_cents must not be negative")
    if not member_ids:
        raise ValueError("an expense needs at least one member to split across")

    count = len(member_ids)
    base, remainder = divmod(amount_cents, count)
    return [
        (member_id, base + (1 if index < remainder else 0))
        for index, member_id in enumerate(member_ids)
    ]


def net_balances(transactions):
    """Net a list of ledger rows down to one balance per member.

    Each transaction is a mapping with ``payer_id``, ``recipient_id`` and
    ``amount_cents``: the payer owes the recipient that much. A positive
    balance means the member is owed money; negative means they owe it.
    """
    balances = {}
    for transaction in transactions:
        payer = transaction["payer_id"]
        recipient = transaction["recipient_id"]
        amount = transaction["amount_cents"]
        balances[payer] = balances.get(payer, 0) - amount
        balances[recipient] = balances.get(recipient, 0) + amount
    return balances


def settle_plan(balances):
    """Turn net balances into the shortest list of transfers that clears them.

    Returns ``(from_member, to_member, amount_cents)`` tuples. Members whose
    balance is already zero are left out. Sorting by member id keeps the plan
    stable for the same input.
    """
    debtors = sorted(
        ((member, -amount) for member, amount in balances.items() if amount < 0),
        key=lambda pair: (-pair[1], pair[0]),
    )
    creditors = sorted(
        ((member, amount) for member, amount in balances.items() if amount > 0),
        key=lambda pair: (-pair[1], pair[0]),
    )

    transfers = []
    debtor_index = 0
    creditor_index = 0
    while debtor_index < len(debtors) and creditor_index < len(creditors):
        debtor, owed = debtors[debtor_index]
        creditor, due = creditors[creditor_index]
        amount = min(owed, due)
        transfers.append((debtor, creditor, amount))

        owed -= amount
        due -= amount
        debtors[debtor_index] = (debtor, owed)
        creditors[creditor_index] = (creditor, due)
        if owed == 0:
            debtor_index += 1
        if due == 0:
            creditor_index += 1
    return transfers
