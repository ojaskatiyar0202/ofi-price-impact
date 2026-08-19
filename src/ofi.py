"""
Order flow imbalance, following Cont, Kukanov & Stoikov (2014),
"The Price Impact of Order Book Events", Journal of Financial Econometrics.

The per-event contribution is

    e_n =  1{P^b_n >= P^b_{n-1}} q^b_n  -  1{P^b_n <= P^b_{n-1}} q^b_{n-1}
         - 1{P^a_n <= P^a_{n-1}} q^a_n  +  1{P^a_n >= P^a_{n-1}} q^a_{n-1}

Note the indicators use weak inequalities on purpose. When the bid price is
unchanged both bid indicators fire and the contribution collapses to
q^b_n - q^b_{n-1}, the change in resting size at the touch. When the bid price
improves, the whole new size counts as inflow. When it drops, the whole old
size counts as outflow. Same logic mirrored on the ask.

OFI over an interval is the sum of e_n over the events in that interval.
"""

import numpy as np
import pandas as pd

REQUIRED_COLS = ["ts", "bid_px", "bid_sz", "ask_px", "ask_sz"]


def _check(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {missing}")
    if not df["ts"].is_monotonic_increasing:
        raise ValueError("ts must be sorted ascending")
    crossed = (df["bid_px"] >= df["ask_px"]).sum()
    if crossed:
        raise ValueError(f"{crossed} crossed or locked quotes in input")


def event_contributions(df: pd.DataFrame) -> pd.Series:
    """Per-event e_n. First row is 0 since e_n needs a previous state."""
    _check(df)

    bp = df["bid_px"].to_numpy(float)
    bs = df["bid_sz"].to_numpy(float)
    ap = df["ask_px"].to_numpy(float)
    az = df["ask_sz"].to_numpy(float)

    e = np.zeros(len(df))
    e[1:] = (
        (bp[1:] >= bp[:-1]) * bs[1:]
        - (bp[1:] <= bp[:-1]) * bs[:-1]
        - (ap[1:] <= ap[:-1]) * az[1:]
        + (ap[1:] >= ap[:-1]) * az[:-1]
    )
    return pd.Series(e, index=df.index, name="e")


def bucket(df: pd.DataFrame, freq: str = "10s", tick_size: float = 0.01) -> pd.DataFrame:
    """
    Aggregate events into fixed time buckets.

    Returns one row per bucket with
        ofi        sum of e_n over the bucket
        mid        midprice at the end of the bucket
        d_mid      change in end-of-bucket mid, in ticks
        d_mid_fwd  next bucket's d_mid, so the predictive regression is honest
        depth      mean of (bid_sz + ask_sz) / 2 over the bucket
        spread     mean spread in ticks
        n_events   number of L1 updates in the bucket

    Empty buckets are dropped. Buckets are contiguous in clock time, so a gap
    breaks the d_mid chain; the first bucket after a gap is dropped by dropna.
    """
    e = event_contributions(df)
    work = df.copy()
    work["e"] = e.to_numpy()
    work["mid"] = (work["bid_px"] + work["ask_px"]) / 2.0
    work["depth"] = (work["bid_sz"] + work["ask_sz"]) / 2.0
    work["spread"] = (work["ask_px"] - work["bid_px"]) / tick_size

    g = work.resample(freq, on="ts")
    out = pd.DataFrame(
        {
            "ofi": g["e"].sum(),
            "mid": g["mid"].last(),
            "depth": g["depth"].mean(),
            "spread": g["spread"].mean(),
            "n_events": g["e"].size(),
        }
    )
    out = out[out["n_events"] > 0].copy()

    out["d_mid"] = out["mid"].diff() / tick_size
    out["d_mid_fwd"] = out["d_mid"].shift(-1)
    return out.dropna(subset=["d_mid"])


def scaled_ofi(buckets: pd.DataFrame) -> pd.Series:
    """
    OFI divided by average depth. CKS find the impact coefficient scales
    roughly like 1 / depth, so dividing first should stabilise the slope
    across days and across names. Worth testing rather than assuming.
    """
    return buckets["ofi"] / buckets["depth"].replace(0, np.nan)
