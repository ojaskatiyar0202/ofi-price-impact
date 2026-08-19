"""
Entry point.

    python -m src.run --source synthetic --freq 10s
    python -m src.run --source binance --path data/BTCUSDT-bookTicker-2026-01-05.csv
    python -m src.run --source lobster --path data/AAPL --date 2026-01-05

Writes a results table to results/ and prints the summary.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from . import data as dataio
from . import evaluate as ev
from . import ofi as ofi_mod


def load(args) -> pd.DataFrame:
    if args.source == "synthetic":
        return dataio.synthetic_book(n_events=args.n_events, seed=args.seed)
    if args.source == "binance":
        return dataio.load_binance_book_ticker(args.path)
    if args.source == "lobster":
        stem = Path(args.path)
        return dataio.load_lobster(
            orderbook_csv=str(stem) + "_orderbook.csv",
            message_csv=str(stem) + "_message.csv",
            date=args.date,
        )
    raise ValueError(args.source)


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--source", choices=["synthetic", "binance", "lobster"], default="synthetic")
    p.add_argument("--path", default=None)
    p.add_argument("--date", default=None)
    p.add_argument("--freq", default="10s", help="bucket length, e.g. 1s 10s 30s")
    p.add_argument("--tick-size", type=float, default=0.01)
    p.add_argument("--fee-ticks", type=float, default=0.0)
    p.add_argument("--train-frac", type=float, default=0.7)
    p.add_argument("--n-events", type=int, default=200_000)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--outdir", default="results")
    args = p.parse_args()

    book = load(args)
    print(f"loaded {len(book):,} top-of-book updates "
          f"from {book['ts'].iloc[0]} to {book['ts'].iloc[-1]}")

    buckets = ofi_mod.bucket(book, freq=args.freq, tick_size=args.tick_size)
    buckets["ofi_scaled"] = ofi_mod.scaled_ofi(buckets)
    print(f"{len(buckets):,} non-empty {args.freq} buckets, "
          f"median {buckets['n_events'].median():.0f} events each")

    fits = [
        ev.fit_split(buckets["ofi"], buckets["d_mid"], "contemporaneous", args.train_frac),
        ev.fit_split(buckets["ofi"], buckets["d_mid_fwd"], "predictive", args.train_frac),
        ev.fit_split(buckets["ofi_scaled"], buckets["d_mid"], "contemp scaled", args.train_frac),
        ev.fit_split(buckets["ofi_scaled"], buckets["d_mid_fwd"], "predictive scaled", args.train_frac),
    ]

    print("\nregressions, mid change in ticks")
    for f in fits:
        print("  " + str(f))

    print("\nimpact coefficient by depth quintile")
    print(ev.depth_stability(buckets).to_string(index=False))

    predictive = fits[1]
    costs = ev.cost_check(
        buckets, predictive,
        tick_size=args.tick_size, fee_ticks=args.fee_ticks, train_frac=args.train_frac,
    )
    print("\ncost check on the predictive fit, test block only")
    for k, v in costs.items():
        print(f"  {k:<24} {v:,.4f}" if isinstance(v, float) else f"  {k:<24} {v:,}")

    outdir = Path(args.outdir)
    outdir.mkdir(exist_ok=True)
    buckets.to_csv(outdir / f"buckets_{args.source}_{args.freq}.csv")
    with open(outdir / f"summary_{args.source}_{args.freq}.json", "w") as fh:
        json.dump(
            {
                "source": args.source,
                "freq": args.freq,
                "n_updates": len(book),
                "n_buckets": len(buckets),
                "fits": [f.__dict__ for f in fits],
                "costs": costs,
            },
            fh,
            indent=2,
        )
    print(f"\nwrote {outdir}/")

    if args.source == "synthetic":
        print(
            "\nSYNTHETIC DATA. These numbers describe the simulator, not a market. "
            "Do not put them in the README or on a CV."
        )


if __name__ == "__main__":
    main()
