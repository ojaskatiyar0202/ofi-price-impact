# Order flow imbalance and short-horizon price impact

We replicate Cont, Kukanov and Stoikov (2014) and examine whether order flow
imbalance predicts short-horizon price movement. We then compare the predicted
move against the cost of crossing the spread.

## Order flow imbalance

Order flow imbalance measures the net pressure at the top of the book over an
interval. It is built from changes in the size available at the best bid and ask
rather than from trades. A cancelled order removes size just as a trade does, and
the book looks the same either way, so a measure built on trades alone misses much
of what happens.

For each update to the top of book, the contribution is

    e_n =  1{P_bid_n >= P_bid_n-1} * q_bid_n  -  1{P_bid_n <= P_bid_n-1} * q_bid_n-1
         - 1{P_ask_n <= P_ask_n-1} * q_ask_n  +  1{P_ask_n >= P_ask_n-1} * q_ask_n-1

The inequalities are weak, which is what allows one expression to cover three
cases. If the bid price is unchanged, both bid indicators equal one and the two
bid terms become q_bid_n minus q_bid_n-1, the change in the size available at the
bid. If the bid price has risen, only the first indicator holds, so the term is
q_bid_n and the whole size at the new level counts as inflow. If the bid price has
fallen, only the second holds, so the term is minus q_bid_n-1 and the whole size
at the old level counts as outflow. The two ask terms work the same way with the
inequalities reversed and the signs flipped, since size arriving at the ask is
supply and pushes the price down.

Summing e_n over an interval gives the imbalance for that interval. The paper
finds that the midprice change over the interval is close to linear in it, with a
slope that scales like one over the average depth.

## Contemporaneous and predictive regressions

The paper's regression measures flow and price change over the same interval, so
it describes a move that has already happened rather than forecasting one. We
therefore also regress the price change over interval k+1 on the imbalance over
interval k, and report both.

A predictive relationship would still have to clear the cost of trading on it. The
midprice is a computed reference rather than a price anyone will transact at, so
acting on a predicted mid move means buying at the ask and selling at the bid,
paying the full spread over a round trip. A prediction of two ticks against a two
tick spread breaks even regardless of its accuracy.

## Method

Top of book is reconstructed into one row per change, with columns for the bid and
ask price and the size available at each. We sum e_n into fixed clock buckets and
measure the midprice change in ticks from the end of one bucket to the end of the
next. Prices are in ticks so that the price move and the cost of crossing the
spread are directly comparable.

The regression is ordinary least squares with White standard errors, since bucketed
order flow is strongly heteroskedastic and a bucket containing six hundred events
behaves very differently from one containing twenty. The split is time ordered with
no shuffling. The out-of-sample R-squared applies the coefficients fitted on the
training block to the test block and measures against the test block's own mean, so
a model with no predictive content scores at or below zero.

To test the depth claim we refit within depth quintiles. If impact scales like one
over depth then the slope should fall as depth rises while the product of slope and
depth stays roughly flat.

For the cost comparison we take the fitted predictive coefficient, trade its sign on
the test block, and measure the realised next-bucket move. That move is demeaned
over the test block, so a strategy that happens to sit long through a rising market
is not credited with the drift. Cost is the average spread over the buckets traded,
which is what a round trip costs when both legs cross.

Bucket length is a free parameter and the reported R-squared moves with it, so we
run 1s, 10s and 30s and report all three.

## Data

Results below are from Binance BTCUSDT perpetual futures bookTicker for
30 March 2024, obtained from

    data.binance.vision/?prefix=data/futures/um/daily/bookTicker/BTCUSDT/

The file is 84 MB compressed and is not committed. Download it, unzip into `data/`,
and `analysis.py` runs unchanged. The tick size for this contract is 0.10 rather
than the 0.01 typical of an equity, and `make_buckets` is called accordingly.

Binance publishes bookTicker for futures and not for spot, and the daily archives
stop partway through 2024. The paper studies US equities, where order book data of
this kind is not freely available.

## Results

| Bucket | Buckets | Contemporaneous R2 in | Contemporaneous R2 out | Predictive R2 out | Predictive t |
|---|---:|---:|---:|---:|---:|
| 1s | 86,396 | 0.5739 | 0.5957 | 0.0372 | 30.67 |
| 10s | 8,639 | 0.7116 | 0.7244 | 0.0054 | 3.81 |
| 30s | 2,879 | 0.7042 | 0.7317 | -0.0040 | 0.90 |

**Discussion.** The contemporaneous relationship is strong and stable. R-squared
rises from 0.57 at one second to 0.72 at ten, and the out-of-sample figure is
slightly higher than the in-sample figure at every bucket length, so the fitted
coefficients transfer to data they were not estimated on. The rise with bucket
length is a measurement effect rather than a change in the relationship itself.
Longer buckets contain more events, the noise in each partly cancels, and what is
left is the systematic part. The gain flattens between ten and thirty seconds.

The predictive regression behaves differently. Out-of-sample R-squared falls from
0.037 at one second to 0.005 at ten and to -0.004 at thirty, where the fitted line
does slightly worse than predicting the test block's mean. The t-statistic follows
the same path, from 30.7 to 3.8 to 0.9.

The one second result needs care. A t-statistic of 30.7 across 86,396 buckets means
the coefficient is not zero, and that much is secure. But the same regression
explains 3.7% of the variation in the next second's price change. The relationship
is statistically real and economically small, which are separate questions that a
significance test alone does not settle. The fall across bucket lengths suggests
the information in order flow is short lived: what exists at one second has mostly
gone by ten and is absent by thirty.

### Cost comparison

| Bucket | Hit rate | Gross (ticks) | Cost (ticks) | Net (ticks) |
|---|---:|---:|---:|---:|
| 1s | 0.530 | 3.87 | 1.04 | 2.83 |
| 10s | 0.560 | 11.21 | 1.09 | 10.12 |
| 30s | 0.537 | 10.07 | 1.10 | 8.97 |

**Discussion.** Net of the round trip spread the strategy is positive at all three
bucket lengths, which was not the expected result. The gross figures are consistent
with the reported R-squared: an eleven tick edge at ten seconds implies a
next-bucket standard deviation of about 190 ticks, which is roughly $19 on Bitcoin
at $70,000, or 48% annualised volatility. So the numbers agree with each other
rather than pointing to an error.

The thirty second row is worth reading closely. Out-of-sample R-squared is negative,
so the fitted line is a worse point forecast than the test mean, yet the hit rate is
0.537 and the gross edge is positive. Both can hold at once. R-squared penalises
errors in magnitude, and a sign strategy does not use magnitude. The coefficient is
too steep, predicting large moves where the realised moves are small, which destroys
R-squared while leaving the direction weakly informative. Dismissing the signal on
R-squared alone would give the wrong answer about its sign content.

The cost model is optimistic, and the gap between it and a live strategy is where
the real answer sits. It assumes the trade executes at the observed spread with no
market impact, no delay between observing the bucket close and transacting, no queue
position and no partial fills. It also ignores that the market makers being traded
against see the same order flow. What the result shows is that the signal is real
and the spread alone does not remove it, which moves the question from whether a
signal exists to whether it survives execution.

### Depth quintiles

| Quintile | Mean depth | Slope | Slope x depth | Buckets |
|---|---:|---:|---:|---:|
| 0 | 3.156 | 1.114 | 3.517 | 1,728 |
| 1 | 4.080 | 0.948 | 3.867 | 1,728 |
| 2 | 4.735 | 0.779 | 3.686 | 1,727 |
| 3 | 5.465 | 0.722 | 3.946 | 1,728 |
| 4 | 8.126 | 0.624 | 5.071 | 1,728 |

**Discussion.** The slope falls as depth rises, from 1.114 in the thinnest quintile
to 0.624 in the thickest, without reversing anywhere. That is the direction the
mechanism predicts, since a given imbalance clears more of a thin book than a thick
one and so moves the price further.

The size of the effect does not match the paper's claim. Under exact one over depth
scaling the product of slope and depth would be constant. It holds across the first
four quintiles, from 3.52 to 3.95 around a mean of 3.75, then rises to 5.07 in the
top quintile, 35% above that mean. Fitting a power law across all five points gives
a slope proportional to depth to the power -0.63 rather than -1, with an R-squared
of 0.94 on the log-log fit.

Depth scales impact systematically, then, but more weakly than one over depth on
this instrument. Mean depth only ranges from 3.2 to 8.1 across the quintiles, which
is a narrow range over which to identify an exponent, and the deviation sits in the
quintile furthest from the rest. A wider set of instruments would test this better
than one contract on one day.

## Files

    code/model.py       imbalance, bucketing, regression, depth quintiles, cost check
    code/analysis.py    data loading and the runs that produce the tables

## Running it

```bash
pip install -r requirements.txt
python code/analysis.py
```

Run from the repository root, since the data and results paths are relative to it.

## Limitations

The cost model assumes execution at the observed spread. It ignores market impact,
delay, queue position and partial fills, all of which work against the strategy,
and it assumes both legs cross rather than resting, which works in its favour.

Imbalance deeper in the book is invisible; that is to say, a large order sitting
behind the touch changes how the price responds and does not appear in this data.
The data also reports total size at each level rather than the number of orders
making it up, so a level held by one participant and one held by fifty are
identical here.

Buckets are fixed in clock time rather than in event count, so a quiet minute and a
busy one carry equal weight in the regression despite containing very different
amounts of information.

Results come from one instrument on one day, so the depth exponent in particular
rests on a narrow cross section.

The instrument is a crypto perpetual future rather than a US equity. There is no
opening or closing auction, trading runs continuously, and the funding mechanism
that keeps the contract near spot has no equity analogue. The magnitudes are not
directly comparable to the published figures.

## Reference

Cont, R., Kukanov, A. and Stoikov, S. (2014). The price impact of order book
events. *Journal of Financial Econometrics*, 12(1), 47-88.
