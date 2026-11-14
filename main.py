# btc-cent-forecast-01 entry (Python 3.13, standard library only, no network).
#
# Task: forecast BTC's US-dollar price 240 minutes after a checkpoint, given
# the 4,320 one-minute closes of the 72 hours leading up to that checkpoint.
#
# Rationale: a 4-hour-ahead price is close to a random walk, so the honest
# middle estimate (the conditional median) sits near the last price. But the
# pool price carries microstructure noise -- one large trade can spike a
# single minute's close -- and a mild pull back toward its recent level.
# The forecast therefore blends three robust levels into one weighted mean:
#   55%   the last close,
#   22.5% the median of the last 45 closes (a spike-proof "current price"),
#   22.5% an exponentially weighted mean with a 240-minute half-life (the
#         slower level the price tends to drift back toward).
# No trend is extrapolated. On the kit's practice history, extrapolating the
# last 1-4h slope made the error worse, so the forecast never chases momentum.
#
# Backtest on the kit's 6 practice cases (330 causal pseudo-checkpoints):
#   this blend: 43,384 cents MAE on the 60-min grid, 38,117 on the 4h grid,
#   vs persistence baseline 45,117 / 40,950 (about 4-6% better).
# On the five real practice checkpoints (p00-p04, one sustained downtrend)
# the blend scores 50,110 cents vs persistence's 47,055.
#
# The shrink weight (0.45 of the forecast pulled off the last price) is a
# deliberate middle ground: a heavier pull (0.60) scored a little better on
# the pseudo-case grids but worse on the five real practice checkpoints,
# which sit in one sustained downtrend. The final's twelve checkpoints are
# unseen prices in unknown regimes, so the middle weight hedges that risk.
# (The 0.45 pull is the sum of the two non-last weights, 0.225 + 0.225.)
#
# Usage: python3 main.py -- it reads $MAKEFUN_INPUT_DIR (else /input) and
# writes one /output/<id>.out per /input/<id>.in, each holding
# {"forecasts": [{"case": <id>, "price": <n>}]}.

import json
import math
import os
import sys
from pathlib import Path

INPUT_DIR = Path(os.getenv("MAKEFUN_INPUT_DIR", "/input"))
OUTPUT_DIR = Path(os.getenv("MAKEFUN_OUTPUT_DIR", "/output"))

# Blend weights: they sum to 1.0, so the forecast is a weighted average of
# the three levels and stays on the price scale of the inputs. The median
# weight is named for the window it belongs to (45 closes, not 60).
W_LAST = 0.55
W_MED60 = 0.225
W_EWMA240 = 0.225
EWMA_HALFLIFE_MIN = 240.0
MED_WINDOW = 45


def ewma(values, halflife):
    alpha = 1.0 - 0.5 ** (1.0 / halflife)
    running = values[0]
    for v in values[1:]:
        running = alpha * v + (1.0 - alpha) * running
    return running


def median(values):
    s = sorted(values)
    n = len(s)
    mid = n // 2
    if n % 2:
        return s[mid]
    return (s[mid - 1] + s[mid]) / 2.0


def forecast(prices):
    last = prices[-1]
    med45 = median(prices[-MED_WINDOW:])
    slow_level = ewma(prices, EWMA_HALFLIFE_MIN)
    guess = W_LAST * last + W_MED60 * med45 + W_EWMA240 * slow_level
    if not math.isfinite(guess) or not 0.0 < guess < 10_000_000.0:
        guess = last
    return round(guess, 2)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    inputs = sorted(INPUT_DIR.glob("*.in"))
    for src in inputs:
        data = json.loads(src.read_text(encoding="utf-8"))
        markets = data.get("markets") or []
        prices = markets[0].get("prices") if markets else None
        if not prices:
            print(f"warning: skipping {src.name}: no prices", file=sys.stderr)
            continue
        price = forecast(prices)
        payload = {"forecasts": [{"case": data["case"], "price": price}]}
        dst = OUTPUT_DIR / (src.stem + ".out")
        dst.write_text(json.dumps(payload), encoding="utf-8")
        print(f"wrote {dst} case={data['case']} price={price}")


if __name__ == "__main__":
    main()
