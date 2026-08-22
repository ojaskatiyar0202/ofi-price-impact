#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import numpy as np
import pandas as pd
from model import make_buckets, fit, depth_buckets, cost_check
def load_binance(path):
    df = pd.read_csv(path)
    out = pd.DataFrame({"ts": pd.to_datetime(df["transaction_time"], unit="ms"),
                        "bid_px": df["best_bid_price"].astype(float),
                        "bid_sz": df["best_bid_qty"].astype(float),
                        "ask_px": df["best_ask_price"].astype(float),
                        "ask_sz": df["best_ask_qty"].astype(float)})
    out = out.sort_values("ts")
    return out[out["bid_px"] < out["ask_px"]].reset_index(drop=True)
os.makedirs("results", exist_ok=True)

book = load_binance("data/BTCUSDT-bookTicker-2024-03-30.csv")

print(len(book), "updates")


ows = []
for freq in ["1s", "10s", "30s"]:
    b = make_buckets(book, freq=freq)
    contemp = fit(b["ofi"], b["d_mid"])
    predict = fit(b["ofi"], b["d_mid_next"])
    costs = cost_check(b, predict)
    rows.append({"freq": freq, "n_buckets": len(b), "contemp_r2_in": contemp["r2_in"], 
                 "contemp_r2_out": contemp["r2_out"], "predict_r2_out": predict["r2_out"], "predict_t": predict["t"],
                 "hit_rate": costs["hit_rate"], "gross_ticks": costs["gross_ticks"],
                 "cost_ticks": costs["cost_ticks"], "net_ticks": costs["net_ticks"]})

df = pd.DataFrame(rows)
print(df.to_string(index=False))
df.to_csv("results/ofi_by_frequency.csv", index=False)
b = make_buckets(book, freq="10s")
dq = depth_buckets(b)
print(dq.to_string(index=False))
dq.to_csv("results/depth_quintiles.csv", index=False)
