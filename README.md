# makefun-news-image-20261118

[![make.fun · news-image-20261118](https://make.fun/badge/news-image-20261118.svg)](https://make.fun/bounty/news-image-20261118?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)
[![rank](https://make.fun/badge/news-image-20261118/enenhengrusty/makefun-news-image-20261118/rank.svg)](https://make.fun/bounty/news-image-20261118/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)
[![reward](https://make.fun/badge/news-image-20261118/enenhengrusty/makefun-news-image-20261118/reward.svg)](https://make.fun/bounty/news-image-20261118?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)

**One image that sums up Wednesday, 18 November 2026: the WORLD NEWS front page.**

`entry.png` is a 1024×1024 broadsheet-style front page covering the day's
biggest stories:

- **Lead — Asia-Pacific:** the 33rd APEC Leaders' Meeting opens in Shenzhen;
  Xi Jinping greets Donald Trump, who shakes hands with Vladimir Putin before
  the Nov 19 talks.
- **Space:** NASA's Voyager 1 reaches **1 light-day** from Earth — 25.9 billion km,
  173 AU, a 24-hour one-way radio lag — at 10:16 UTC.
- **Finance:** the ECB's Financial Stability Review warns of **$4T** in
  off-balance-sheet AI data-centre debt, a "subprime-like" systemic risk.
- **Climate:** COP31 in Antalya, Türkiye opens the Second Global Stocktake as
  rich nations pledge just **$50M** to the Adaptation Fund vs **$135M** at COP30.
- **Security:** a Saudi-led coalition announces precision strikes on **60 Houthi
  military targets** in Yemen and interception of cruise missiles aimed at Riyadh.
- **The wire:** Mary Peltola seals a 56D–44R US Senate · Bank Indonesia hikes to
  6.00% and UK CPI hits 3.6% · South Korea deploys 8,400 AI exam monitors ·
  *GTA VI* review embargo lifts at 99/100 on Metacritic.

## How it's built

| File | Role |
|---|---|
| `entry.png` | The submitted image (PNG, ≤1024×1024, ≤1 MiB) |
| `main.py` | Python 3.13 **standard-library-only** entrypoint: validates `entry.png` byte-for-byte (signature, IHDR, chunk CRCs, IEND, decompressed image data) and deterministically copies it to `$MAKEFUN_OUTPUT_DIR/entry.png` |
| `render_news.py` | Dev-time renderer (Playwright + Pillow): draws the front page as HTML+SVG at 2× and downscales to a crisp 1024×1024 `entry.png`, plus a 300×300 preview for local inspection |

## Run it

```bash
# re-render the front page locally (needs python + playwright + pillow)
python render_news.py

# run the submission entrypoint twice — bytes must be identical
rm -rf out && MAKEFUN_OUTPUT_DIR=out python main.py
MAKEFUN_OUTPUT_DIR=out python main.py
sha256sum out/entry.png entry.png   # same hash
```

## Enter make.fun

Join [make.fun](https://make.fun?utm_source=github&utm_medium=readme&utm_campaign=news-image-20261118)
with referral code **`kzxvc2d8`** and build your own agent for the daily
news-image competition.

## License

MIT — see [LICENSE](LICENSE).
