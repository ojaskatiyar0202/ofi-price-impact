"""
Data loading.

Everything downstream expects one canonical frame:

    ts       pandas datetime64
    bid_px   float, best bid price
    bid_sz   float, size resting at best bid
    ask_px   float, best ask price
    ask_sz   float, size resting at best ask

One row per change to the top of book. Three sources are supported.

LOBSTER   ships a message file and an orderbook file per name per day. The
          free sample covers a handful of names. Levels beyond 1 are ignored
          here, which is fine for baseline OFI.

Binance   the public archive at data.binance.vision publishes bookTicker
          files, one row per best bid/ask change. No API key. Verify the exact
          path for the symbol and date range you want before scripting a bulk
          pull, the layout has changed before.

Synthetic a mechanical book simulator. Use it to check the maths runs end to
          end. Numbers off synthetic data are meaningless and must never end
          up on a CV or in a README result table.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def load_lobster(orderbook_csv: str, message_csv: str, date: str) -> pd.DataFrame:
    """
    LOBSTER orderbook files are headerless with columns repeating as
    ask_px_1, ask_sz_1, bid_px_1, bid_sz_1, ask_px_2, ... Prices are in
    integer ten-thousandths of a currency unit. The message file supplies
    seconds after midnight.
    """
    ob = pd.read_csv(orderbook_csv, header=None)
    msg = pd.read_csv(message_csv, header=None)

    if len(ob) != len(msg):
        raise ValueError(f"row mismatch: orderbook {len(ob)}, message {len(msg)}")

    out = pd.DataFrame(
        {
            "ts": pd.Timestamp(date) + pd.to_timedelta(msg[0].to_numpy(), unit="s"),
            "ask_px": ob[0].to_numpy() / 10_000.0,
            "ask_sz": ob[1].to_numpy(float),
            "bid_px": ob[2].to_numpy() / 10_000.0,
            "bid_sz": ob[3].to_numpy(float),
        }
    )
    return _clean(out)


def load_binance_book_ticker(path: str) -> pd.DataFrame:
    """
    bookTicker archive files carry columns
    update_id, best_bid_price, best_bid_qty, best_ask_price, best_ask_qty,
    transaction_time, event_time. Some vintages omit the header row, so both
    cases are handled.
    """
    cols = [
        "update_id",
        "best_bid_price",
        "best_bid_qty",
        "best_ask_price",
        "best_ask_qty",
        "transaction_time",
        "event_time",
    ]
    head = pd.read_csv(path, nrows=1)
    df = (
        pd.read_csv(path)
        if "best_bid_price" in head.columns
        else pd.read_csv(path, header=None, names=cols)
    )

    out = pd.DataFrame(
        {
            "ts": pd.to_datetime(df["transaction_time"], unit="ms"),
            "bid_px": df["best_bid_price"].astype(float),
            "bid_sz": df["best_bid_qty"].astype(float),
            "ask_px": df["best_ask_price"].astype(float),
            "ask_sz": df["best_ask_qty"].astype(float),
        }
    )
    return _clean(out)


def _clean(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values("ts").reset_index(drop=True)
    df = df[(df["bid_px"] < df["ask_px"]) & (df["bid_sz"] > 0) & (df["ask_sz"] > 0)]
    return df.reset_index(drop=True)


def synthetic_book(
    n_events: int = 200_000,
    tick_size: float = 0.01,
    start_mid: float = 100.0,
    typical_depth: float = 500.0,
    seed: int = 0,
    start: str = "2026-01-05 09:30:00",
) -> pd.DataFrame:
    """
    A deliberately crude one-tick-wide book. Each event either adds size,
    cancels size, or sends a market order into one side. When a side is fully
    consumed the price on that side steps by a tick and fresh size appears,
    which is what generates a relationship between order flow and price.

    This exists to exercise the code path, not to produce a finding.
    """
    rng = np.random.default_rng(seed)

    bid_px = start_mid - tick_size / 2
    ask_px = start_mid + tick_size / 2
    bid_sz = typical_depth
    ask_sz = typical_depth

    rows = np.empty((n_events, 4))
    kinds = rng.choice(["add", "cancel", "market"], size=n_events, p=[0.45, 0.40, 0.15])
    sides = rng.integers(0, 2, size=n_events)
    sizes = rng.gamma(shape=2.0, scale=typical_depth / 8.0, size=n_events)

    for i in range(n_events):
        kind, side, qty = kinds[i], sides[i], sizes[i]

        if kind == "add":
            if side == 0:
                bid_sz += qty
            else:
                ask_sz += qty
        elif kind == "cancel":
            if side == 0:
                bid_sz -= min(qty, bid_sz * 0.9)
            else:
                ask_sz -= min(qty, ask_sz * 0.9)
        else:  # market order consumes the touch
            if side == 0:
                ask_sz -= qty
            else:
                bid_sz -= qty

        # a depleted side means the price moves and the book refills
        if ask_sz <= 0:
            ask_px += tick_size
            bid_px += tick_size
            ask_sz = max(rng.gamma(2.0, typical_depth / 2.0), 1.0)
            bid_sz = max(rng.gamma(2.0, typical_depth / 2.0), 1.0)
        if bid_sz <= 0:
            bid_px -= tick_size
            ask_px -= tick_size
            bid_sz = max(rng.gamma(2.0, typical_depth / 2.0), 1.0)
            ask_sz = max(rng.gamma(2.0, typical_depth / 2.0), 1.0)

        rows[i] = (bid_px, bid_sz, ask_px, ask_sz)

    gaps = rng.exponential(scale=0.05, size=n_events)  # ~20 events per second
    out = pd.DataFrame(rows, columns=["bid_px", "bid_sz", "ask_px", "ask_sz"])
    out.insert(0, "ts", pd.Timestamp(start) + pd.to_timedelta(np.cumsum(gaps), unit="s"))
    out["bid_px"] = out["bid_px"].round(6)
    out["ask_px"] = out["ask_px"].round(6)
    return _clean(out)
