"""Tests pin the OFI definition down. If you refactor, these must still pass."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest

from src.ofi import event_contributions, bucket
from src.data import synthetic_book


def _frame(rows):
    df = pd.DataFrame(rows, columns=["bid_px", "bid_sz", "ask_px", "ask_sz"])
    df.insert(0, "ts", pd.date_range("2026-01-05 09:30", periods=len(df), freq="1s"))
    return df


def test_first_event_is_zero():
    df = _frame([(99.99, 100, 100.01, 100), (99.99, 120, 100.01, 100)])
    assert event_contributions(df).iloc[0] == 0


def test_bid_size_added_is_positive_inflow():
    # bid price unchanged, size 100 -> 150, so e = 150 - 100 = +50
    df = _frame([(99.99, 100, 100.01, 100), (99.99, 150, 100.01, 100)])
    assert event_contributions(df).iloc[1] == pytest.approx(50.0)


def test_bid_size_cancelled_is_negative():
    df = _frame([(99.99, 100, 100.01, 100), (99.99, 40, 100.01, 100)])
    assert event_contributions(df).iloc[1] == pytest.approx(-60.0)


def test_ask_size_added_is_negative_ofi():
    # more supply at the ask pushes OFI down
    df = _frame([(99.99, 100, 100.01, 100), (99.99, 100, 100.01, 175)])
    assert event_contributions(df).iloc[1] == pytest.approx(-75.0)


def test_bid_price_improvement_counts_whole_new_size():
    """
    Bid steps 99.99 -> 100.00 with new size 60, ask untouched.
    The 1{P_b_n <= P_b_prev} indicator is 0 because the bid strictly improved,
    so the old size is not subtracted. The unchanged ask contributes
    -q_a_n + q_a_prev = 0. Total is the whole new bid size, +60.
    """
    df = _frame([(99.99, 100, 100.02, 100), (100.00, 60, 100.02, 100)])
    assert event_contributions(df).iloc[1] == pytest.approx(60.0)


def test_bid_price_drop_counts_whole_old_size_as_outflow():
    """Mirror of the above: bid falls, so the old resting size flows out."""
    df = _frame([(99.99, 100, 100.02, 100), (99.98, 60, 100.02, 100)])
    assert event_contributions(df).iloc[1] == pytest.approx(-100.0)


def test_sign_symmetry():
    """Mirroring the book about the mid must flip the sign of every e_n."""
    rows = [(99.99, 100, 100.01, 140), (99.99, 130, 100.01, 90), (100.00, 70, 100.02, 200)]
    df = _frame(rows)
    mirror = _frame([(200 - a, az, 200 - b, bz) for b, bz, a, az in rows])
    np.testing.assert_allclose(
        event_contributions(df).to_numpy(),
        -event_contributions(mirror).to_numpy(),
    )


def test_crossed_book_rejected():
    df = _frame([(100.02, 100, 100.01, 100), (100.02, 100, 100.01, 100)])
    with pytest.raises(ValueError, match="crossed"):
        event_contributions(df)


def test_unsorted_rejected():
    df = _frame([(99.99, 100, 100.01, 100), (99.99, 100, 100.01, 100)])
    df.loc[1, "ts"] = df.loc[0, "ts"] - pd.Timedelta("1s")
    with pytest.raises(ValueError, match="sorted"):
        event_contributions(df)


def test_bucket_shapes_and_forward_alignment():
    book = synthetic_book(n_events=20_000, seed=1)
    b = bucket(book, freq="10s")
    assert (b["n_events"] > 0).all()
    assert b["mid"].notna().all()
    np.testing.assert_allclose(
        b["d_mid_fwd"].iloc[:-1].to_numpy(), b["d_mid"].iloc[1:].to_numpy()
    )


def test_ofi_moves_with_price_in_simulator():
    """Sanity check only: the simulator should produce positive co-movement."""
    book = synthetic_book(n_events=100_000, seed=2)
    b = bucket(book, freq="10s")
    assert b[["ofi", "d_mid"]].corr().iloc[0, 1] > 0
