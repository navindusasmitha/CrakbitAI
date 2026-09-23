#!/usr/bin/env python3
import unittest

from monetary import (
    COIN,
    INITIAL_SUBSIDY,
    HALVING_INTERVAL,
    TREASURY_START,
    TREASURY_END,
    block_subsidy,
    treasury_subsidy,
    miner_subsidy,
    scheduled_emission,
    treasury_emission,
)


class MonetaryPolicyTests(unittest.TestCase):
    def test_initial_subsidy(self):
        self.assertEqual(block_subsidy(0), 10 * COIN)

    def test_first_halving_boundary(self):
        self.assertEqual(block_subsidy(HALVING_INTERVAL - 1), INITIAL_SUBSIDY)
        self.assertEqual(block_subsidy(HALVING_INTERVAL), INITIAL_SUBSIDY // 2)

    def test_treasury_window_boundaries(self):
        self.assertEqual(treasury_subsidy(TREASURY_START - 1), 0)
        self.assertEqual(treasury_subsidy(TREASURY_START), INITIAL_SUBSIDY // 20)
        self.assertEqual(treasury_subsidy(TREASURY_END), INITIAL_SUBSIDY // 20)
        self.assertEqual(treasury_subsidy(TREASURY_END + 1), 0)

    def test_no_extra_minting(self):
        for height in [0, 1, 2, 400_000, 400_001, HALVING_INTERVAL, HALVING_INTERVAL + 1]:
            self.assertEqual(
                miner_subsidy(height) + treasury_subsidy(height),
                block_subsidy(height),
            )

    def test_exact_total_emission(self):
        self.assertEqual(scheduled_emission(), 2_102_399_986_334_400)

    def test_exact_treasury_emission(self):
        self.assertEqual(treasury_emission(), 200_000 * COIN)

    def test_negative_height_rejected(self):
        with self.assertRaises(ValueError):
            block_subsidy(-1)


if __name__ == "__main__":
    unittest.main()
