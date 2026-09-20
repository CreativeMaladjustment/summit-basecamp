import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from splits import net_balances, settle_plan, split_equally  # noqa: E402


class SplitEquallyTests(unittest.TestCase):
    def test_an_even_split_divides_exactly(self):
        self.assertEqual(
            split_equally(1200, ["a", "b", "c"]),
            [("a", 400), ("b", 400), ("c", 400)],
        )

    def test_the_remainder_is_handed_out_a_cent_at_a_time(self):
        shares = split_equally(1000, ["a", "b", "c"])
        self.assertEqual(shares, [("a", 334), ("b", 333), ("c", 333)])
        self.assertEqual(sum(share for _, share in shares), 1000)

    def test_shares_always_add_back_up_to_the_amount(self):
        for amount in range(0, 200):
            for size in range(1, 8):
                members = ["m{}".format(i) for i in range(size)]
                shares = split_equally(amount, members)
                self.assertEqual(sum(share for _, share in shares), amount)

    def test_a_negative_amount_is_rejected(self):
        with self.assertRaises(ValueError):
            split_equally(-1, ["a"])

    def test_an_empty_member_list_is_rejected(self):
        with self.assertRaises(ValueError):
            split_equally(100, [])


class LedgerTests(unittest.TestCase):
    def test_balances_net_out_across_transactions(self):
        transactions = [
            {"payer_id": "bo", "recipient_id": "ada", "amount_cents": 1000},
            {"payer_id": "cyd", "recipient_id": "ada", "amount_cents": 1000},
            {"payer_id": "ada", "recipient_id": "bo", "amount_cents": 400},
        ]
        self.assertEqual(
            net_balances(transactions),
            {"ada": 1600, "bo": -600, "cyd": -1000},
        )

    def test_a_cleared_ledger_needs_no_transfers(self):
        self.assertEqual(settle_plan({"ada": 0, "bo": 0}), [])

    def test_one_debtor_pays_one_creditor(self):
        self.assertEqual(
            settle_plan({"ada": 1000, "bo": -1000}),
            [("bo", "ada", 1000)],
        )

    def test_a_debt_is_spread_across_creditors(self):
        plan = settle_plan({"ada": 600, "cyd": 400, "bo": -1000})
        self.assertEqual(plan, [("bo", "ada", 600), ("bo", "cyd", 400)])

    def test_every_transfer_is_positive_and_clears_the_balances(self):
        balances = {"ada": 1600, "bo": -600, "cyd": -1000}
        remaining = dict(balances)
        for payer, recipient, amount in settle_plan(balances):
            self.assertGreater(amount, 0)
            remaining[payer] += amount
            remaining[recipient] -= amount
        self.assertEqual(set(remaining.values()), {0})


if __name__ == "__main__":
    unittest.main()
