# Order flow imbalance and short-horizon price impact

We replicate Cont, Kukanov and Stoikov (2014) and examine whether order flow
imbalance predicts short-horizon price movement. We then compare the predicted
move against the cost of crossing the spread.

## Order flow imbalance

Order flow imbalance measures the net pressure at the top of the book over an
interval. It is built from changes in the size resting at the best bid and ask
rather than from trades. A cancelled order removes liquidity exactly as a trade
does, and from the book's perspective the two are indistinguishable, so a measure
built on trades alone misses most of what happens in an electronic market.

For each update to the top of book, the contribution is

    e_n =  1{P_bid_n >= P_bid_n-1} * q_bid_n  -  1{P_bid_n <= P_bid_n-1} * q_bid_n-1
         - 1{P_ask_n <= P_ask_n-1} * q_ask_n  +  1{P_ask_n >= P_ask_n-1} * q_ask_n-1

The inequalities are weak, which allows one expression to handle three cases.
When the bid price does not change, both bid indicators trigger, and the expression
reduces to the change in the size of the ask prices. When the bid improves, only the first
fires and the whole new size counts as inflow, since the previous level has not
disappeared but has stopped being the best. When the bid falls, only the second
term remains, and so the whole old size counts as outflow. The ask terms carry the opposite
sign because more supply at the ask price pushes the price down.

Summing e_n over an interval gives the imbalance for that interval. The paper
finds that the midprice change over the interval is close to linear in it, with a
slope that scales like one over the average depth.

## Contemporaneous and predictive regressions

The paper's regression measures flow and price change over the same interval, so
it describes a move that has already occurred rather than forecasting one. We
therefore also regress the price change over interval k+1 on the imbalance over
interval k, and report both.

A predictive relationship would still have to clear the cost of trading on it.
The midprice is a computed reference rather than a price anyone will transact at,
so acting on a predicted mid move means buying at the ask and selling at the bid,
paying the full spread over a round trip. A prediction of two ticks against a two
tick spread breaks even regardless of its accuracy.

## Method

Top of book is reconstructed into one row per change, with columns for the bid
and ask price and the size resting at each. We sum e_n into fixed clock buckets
and measure the midprice change in ticks from the end of one bucket to the end of
the next. Prices are expressed in ticks so that the price move and the cost of
crossing the spread are directly comparable.

The regression is ordinary least squares with White standard errors, since
bucketed order flow is strongly heteroskedastic and a bucket containing six
hundred events behaves very differently from one containing twenty. The split is
time ordered with no shuffling. The out-of-sample R-squared applies the
coefficients fitted on the training block to the test block and measures against
the test block's own mean, so a model with no predictive content scores at or
below zero.

To test the depth claim we refit within depth quintiles. If impact scales like
one over depth then the slope should fall as depth rises while the product of
slope and depth stays roughly flat.

Bucket length is a free parameter and the reported R-squared moves with it, so we
run 1s, 10s and 30s and report all three.

## Data

Results below are from Binance BTCUSDT perpetual futures bookTicker for
30 March 2024, obtained from

    data.binance.vision/?prefix=data/futures/um/daily/bookTicker/BTCUSDT/

The file is 84 MB compressed and is not committed. Download it, unzip into
`data/`, and `analysis.py` runs unchanged. The tick size for this contract is
0.10 rather than the 0.01 typical of an equity, and `make_buckets` is called
accordingly.

Binance publishes bookTicker for futures and not for spot, and the daily archives
stop partway through 2024. The paper studies US equities, where order book data
of this kind is not freely available.

## Results

| Bucket | Buckets | Contemporaneous R2 in | Contemporaneous R2 out | Predictive R2 out | Predictive t |
|---|---:|---:|---:|---:|---:|
| 1s | 86,396 | 0.5739 | 0.5957 | 0.0372 | 30.67 |
| 10s | 8,639 | 0.7116 | 0.7244 | 0.0054 | 3.81 |
| 30s | 2,879 | 0.7042 | 0.7317 | -0.0040 | 0.90 |

### Depth quintiles

| Quintile | Mean depth | Slope | Slope x depth | Buckets |
|---|---:|---:|---:|---:|
| 0 | 3.156 | 11.144 | 35.171 | 1,728 |
| 1 | 4.080 | 9.478 | 38.668 | 1,728 |
| 2 | 4.735 | 7.785 | 36.865 | 1,727 |
| 3 | 5.465 | 7.221 | 39.463 | 1,728 |
| 4 | 8.126 | 6.241 | 50.714 | 1,728 |

**Discussion.** [To fill.]

## Files

    code/model.py       imbalance, bucketing, regression, depth quintiles
    code/analysis.py    data loading and the runs that produce the tables
    tests/test_ofi.py   tests

## Running it

```bash
pip install -r requirements.txt
python code/analysis.py
pytest tests/ -q
```

Run from the repository root, since the data and results paths are relative to it.

## Limitations


Imbalance deeper in the book is invisible; that is to say, a large
order sitting behind the touch changes how the price responds and does not appear
in this data. The data also reports total size at each level rather than the
number of orders composing it, so a level held by one participant and one held by
fifty are identical here.

Buckets are fixed in clock time rather than in event count, so a quiet minute and
a busy one carry equal weight in the regression despite containing very different
amounts of information.

The instrument is a crypto perpetual future rather than a US equity. There is no
opening or closing auction, trading runs continuously, and the funding mechanism
that keeps the contract near spot has no equity analogue. The magnitudes are not
directly comparable to the published figures.

## Reference

Cont, R., Kukanov, A. and Stoikov, S. (2014). The price impact of order book
events. *Journal of Financial Econometrics*, 12(1), 47-88.
