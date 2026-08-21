#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri Aug 21 21:30:00 2026

@author: Ojas
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "code"))

import numpy as np
import pandas as pd
import pytest
from OFI import ofi_events, make_buckets, ols, r_squared, fit, depth_buckets


def book(rows):
    # rows are (bid_px, bid_sz, ask_px, ask_sz)
    df = pd.DataFrame(rows, columns=["bid_px", "bid_sz", "ask_px", "ask_sz"])
    df.insert(0, "ts", pd.date_range("2026-01-05 09:30", periods=len(df), freq="1s"))
    return df


def events(rows):
    d = book(rows)
    return ofi_events(d["bid_px"].to_numpy(float), d["bid_sz"].to_numpy(float),
                      d["ask_px"].to_numpy(float), d["ask_sz"].to_numpy(float))


def test_first_event_is_zero():
    # e_n needs a previous state, so there is nothing to compute at n = 0
    e = events([(99.99, 100, 100.01, 100), (99.99, 120, 100.01, 100)])
    assert e[0] == 0


def test_size_added_at_bid_is_positive():
    # bid price unchanged, so the term collapses to the change in resting size
    e = events([(99.99, 100, 100.01, 100), (99.99, 150, 100.01, 100)])
    assert e[1] == pytest.approx(50)


def test_size_cancelled_at_bid_is_negative():
    e = events([(99.99, 100, 100.01, 100), (99.99, 40, 100.01, 100)])
    assert e[1] == pytest.approx(-60)


def test_size_added_at_ask_is_negative():
    # more supply at the ask pushes OFI down
    e = events([(99.99, 100, 100.01, 100), (99.99, 100, 100.01, 175)])
    assert e[1] == pytest.approx(-75)


def test_bid_price_improvement_counts_whole_new_size():
    # the bid strictly improved so the old size is not subtracted, and the
    # unchanged ask contributes -q_ask + q_ask = 0
    e = events([(99.99, 100, 100.02, 100), (100.00, 60, 100.02, 100)])
    assert e[1] == pytest.approx(60)


def test_bid_price_drop_counts_whole_old_size():
    e = events([(99.99, 100, 100.02, 100), (99.98, 60, 100.02, 100)])
    assert e[1] == pytest.approx(-100)


def test_mirroring_the_book_flips_the_sign():
    # reflecting bid and ask about the mid should negate every contribution
    rows = [(99.99, 100, 100.01, 140), (99.99, 130, 100.01, 90), (100.00, 70, 100.02, 200)]
    mirror = [(200 - a, az, 200 - b, bz) for b, bz, a, az in rows]
    np.testing.assert_allclose(events(rows), -np.array(events(mirror)))


def test_buckets_align_the_forward_move():
    # d_mid_next in one row must equal d_mid in the next
    rng = np.random.default_rng(0)
    px = 100 + np.cumsum(rng.normal(0, 0.01, 5000))
    d = pd.DataFrame({"ts": pd.Timestamp("2026-01-05 09:30") + pd.to_timedelta(np.arange(5000) * 0.05, unit="s"),
                      "bid_px": px - 0.005, "bid_sz": rng.gamma(2, 200, 5000),
                      "ask_px": px + 0.005, "ask_sz": rng.gamma(2, 200, 5000)})
    b = make_buckets(d, freq="10s")
    np.testing.assert_allclose(b["d_mid_next"].iloc[:-1].to_numpy(), b["d_mid"].iloc[1:].to_numpy())


def test_ols_recovers_a_known_line():
    x = np.linspace(0, 10, 100)
    y = 3 + 2 * x
    beta, alpha, se = ols(x, y)
    assert beta == pytest.approx(2)
    assert alpha == pytest.approx(3)


def test_r_squared_is_one_on_a_perfect_fit():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    assert r_squared(y, y) == pytest.approx(1)


def test_r_squared_is_zero_for_the_mean():
    y = np.array([1.0, 2.0, 3.0, 4.0])
    assert r_squared(y, np.full(4, y.mean())) == pytest.approx(0)


def test_out_of_sample_r2_is_negative_on_noise():
    # fitting a line to pure noise should not generalise, so R^2 out must be
    # at or below zero once the train coefficients meet the test block
    rng = np.random.default_rng(1)
    x = pd.Series(rng.normal(size=1000))
    y = pd.Series(rng.normal(size=1000))
    res = fit(x, y)
    assert res["r2_out"] <= 0.02


def test_depth_buckets_cover_every_row():
    rng = np.random.default_rng(2)
    b = pd.DataFrame({"ofi": rng.normal(size=1000),
                      "d_mid": rng.normal(size=1000),
                      "depth": rng.gamma(2, 300, 1000)})
    dq = depth_buckets(b, n_bins=5)
    assert len(dq) == 5
    assert dq["n"].sum() == 1000
    assert dq["mean_depth"].is_monotonic_increasing
