#!/usr/bin/env python3
"""Consensus-reference monetary arithmetic for Crakbit Chain.

This is a reference/test oracle, not the production C++ consensus implementation.
All values are integer base units.
"""

COIN = 100_000_000
INITIAL_SUBSIDY = 10 * COIN
HALVING_INTERVAL = 1_051_200
TREASURY_START = 1
TREASURY_END = 400_000


def block_subsidy(height: int) -> int:
    if height < 0:
        raise ValueError("height must be non-negative")
    halvings = height // HALVING_INTERVAL
    if halvings >= 63:
        return 0
    return INITIAL_SUBSIDY >> halvings


def treasury_subsidy(height: int) -> int:
    subsidy = block_subsidy(height)
    if TREASURY_START <= height <= TREASURY_END:
        return subsidy // 20
    return 0


def miner_subsidy(height: int) -> int:
    return block_subsidy(height) - treasury_subsidy(height)


def scheduled_emission() -> int:
    total = 0
    reward = INITIAL_SUBSIDY
    while reward:
        total += reward * HALVING_INTERVAL
        reward >>= 1
    return total


def treasury_emission() -> int:
    return sum(treasury_subsidy(h) for h in range(TREASURY_START, TREASURY_END + 1))


def fmt(value: int) -> str:
    return f"{value / COIN:.8f}"


if __name__ == "__main__":
    total = scheduled_emission()
    treasury = treasury_emission()
    print(f"scheduled_emission_base_units={total}")
    print(f"scheduled_emission_cbit={fmt(total)}")
    print(f"treasury_emission_base_units={treasury}")
    print(f"treasury_emission_cbit={fmt(treasury)}")
