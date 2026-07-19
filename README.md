# 7-Stock Momentum Breakout Strategy → Telegram Bot

Same logic as the original `Momentum.ipynb` notebook, packaged as a script that
sends the daily shortlist to your Telegram bot (`@sigma_sigma_stock_bot`).

## Strategy logic (unchanged from the notebook)

1. **Market Regime** — Nifty 50 Supertrend (ATR 14, multiplier 2). If regime
   is `SELL`, the bot sends a defensive-mode alert and stops (no stock scan).
2. **Momentum Ranking** — Downloads Nifty 500 constituents, computes 1-month
   returns, filters out stocks priced ≤ ₹100, keeps the top 20.
3. **Price Breakout Filter** — Keeps only stocks whose current close is above
   their 50-day high.
4. **Volatility Filter** — Keeps only stocks with 14-day ATR < 5% of close.
5. **Final Shortlist** — Top 7 stocks by momentum score, with share
   quantities sized against ₹1,00,000 capital (₹14,285.71/stock).
6. **Telegram Delivery** — Sends the final result (shortlist, defensive
   notice, or "no stocks passed" message) to your Telegram chat.

## 1. Create / locate your Telegram bot token

If `@sigma_sigma_stock_bot` is already registered under your account:

1. Open Telegram, message **@BotFather**.
2. Send `/mybots`, select `@sigma_sigma_stock_bot`.
3. Tap **API Token** to reveal it (or **Edit Bot → Regenerate token** if lost).

If it doesn't exist yet, message **@BotFather**, send `/newbot`, and follow
the prompts to name it `sigma_sigma_stock_bot` — BotFather gives you a token
immediately after creation.

## 2. Get your Telegram chat ID

1. Send any message (e.g. "hi") to `@sigma_sigma_stock_bot` first — bots
   can't message you until you've messaged them.
2. Visit this URL in your browser (replace `<TOKEN>`):
   `https://api.telegram.org/bot<TOKEN>/getUpdates`
3. Look for `"chat":{"id": 123456789, ...}` in the JSON response — that
   number is your `TELEGRAM_CHAT_ID`.

(For a group chat, add the bot to the group first, send a message in the
group, then repeat step 2 — group chat IDs are usually negative numbers.)

## 3. Configure secrets

### Option A — Run via GitHub Actions (recommended, fully automated)

1. Push this repo to GitHub.
2. Go to **Settings → Secrets and variables → Actions → New repository secret**.
3. Add two secrets:
   - `TELEGRAM_BOT_TOKEN` — the token from step 1
   - `TELEGRAM_CHAT_ID` — the chat id from step 2
4. The workflow in `.github/workflows/run-momentum-strategy.yml` runs
   automatically on weekdays at 4:00 PM IST, or trigger it manually from the
   **Actions** tab → **Run Momentum Strategy** → **Run workflow**.

### Option B — Run locally

```bash
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN="your-token-here"
export TELEGRAM_CHAT_ID="your-chat-id-here"
python momentum_strategy.py
```

If the environment variables aren't set, the script prints the message to
the console instead of sending it, so you can test the strategy logic
without Telegram configured.

## Files

- `momentum_strategy.py` — the full strategy + Telegram delivery
- `requirements.txt` — Python dependencies
- `.github/workflows/run-momentum-strategy.yml` — scheduled/manual runner

## Notes

- Uses `yfinance` for price data and the official NSE Nifty 500 constituent
  CSV — both are free, no API key needed.
- Adjust `CAPITAL` and `NUM_STOCKS` at the top of `momentum_strategy.py` to
  change position sizing.
- Adjust the `cron` schedule in the workflow file to change run time
  (cron times are in UTC).
