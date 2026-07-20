"""
7-Stock Momentum Breakout Strategy (India) — with Telegram delivery
====================================================================

Same logic as the original Momentum.ipynb notebook:
  1. Market Regime check   -> Nifty 50 Supertrend (ATR 14, Mult 2)
  2. Momentum Ranking       -> Top 20 Nifty 500 stocks by 1-month return
  3. Price Breakout Filter  -> Close > highest high of last 50 days
  4. Volatility Filter      -> 14-day ATR < 5% of Close
  5. Final Shortlist        -> Top NUM_STOCKS by momentum score
  6. Telegram Delivery      -> Sends the final shortlist (or defensive-mode
                               notice) to your Telegram bot.

Run:
    python momentum_strategy.py

Environment variables required (see README.md for setup):
    TELEGRAM_BOT_TOKEN   - token for @sigma_sigma_stock_bot (from @BotFather)
    TELEGRAM_CHAT_ID     - your personal or group chat id
"""

import io
import os
import sys
from datetime import datetime

import numpy as np
import pandas as pd
import pandas_ta as ta
import requests
import yfinance as yf

# ---------------------------------------------------------------------------
# USER CONFIGURATION
# ---------------------------------------------------------------------------
CAPITAL = 100_000        # Total capital: ₹1,00,000
NUM_STOCKS = 7            # Target number of stocks in final portfolio
ALLOCATION_PER_STOCK = CAPITAL / NUM_STOCKS

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

# ---------------------------------------------------------------------------
# NIFTY 500 CONSTITUENTS (static list)
# ---------------------------------------------------------------------------
# NSE's servers block automated requests from cloud/CI IPs (GitHub Actions
# included), so instead of fetching this list at runtime, it's embedded here
# directly. Sourced from NSE's official ind_nifty500list.csv (July 2026).
#
# NOTE: NSE rebalances this index twice a year (cut-off dates: 31 Jan and
# 31 Jul). Refresh this list periodically by downloading the latest CSV from
# NSE (https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-500)
# and regenerating this list.
NIFTY_500_SYMBOLS = [
    "360ONE", "3MINDIA", "ABB", "ACC", "ACMESOLAR", "AIAENG", "APLAPOLLO", "AUBANK",
    "AWL", "AADHARHFC", "AARTIIND", "AAVAS", "ABBOTINDIA", "ACE", "ACUTAAS", "ADANIENSOL",
    "ADANIENT", "ADANIGREEN", "ADANIPORTS", "ADANIPOWER", "ATGL", "ABCAPITAL", "ABFRL", "ABLBL",
    "ABREL", "ABSLAMC", "CPPLUS", "AEGISLOG", "AEGISVOPAK", "AFCONS", "AFFLE", "AJANTPHARM",
    "ALKEM", "ABDL", "ARE&M", "AMBER", "AMBUJACEM", "ANANDRATHI", "ANANTRAJ", "ANGELONE",
    "ANTHEM", "ANURAS", "APARINDS", "APOLLOHOSP", "APOLLOTYRE", "APTUS", "ASAHIINDIA", "ASHOKLEY",
    "ASIANPAINT", "ASTERDM", "ASTRAL", "ATHERENERG", "ATUL", "AUROPHARMA", "AIIL", "DMART",
    "AXISBANK", "BEML", "BLS", "BSE", "BAJAJ-AUTO", "BAJFINANCE", "BAJAJFINSV", "BAJAJHLDNG",
    "BAJAJHFL", "BALKRISIND", "BALRAMCHIN", "BANDHANBNK", "BANKBARODA", "BANKINDIA", "MAHABANK", "BATAINDIA",
    "BAYERCROP", "BELRISE", "BERGEPAINT", "BDL", "BEL", "BHARATFORG", "BHEL", "BPCL",
    "BHARTIARTL", "BHARTIHEXA", "BIKAJI", "GROWW", "BIOCON", "BSOFT", "BLUEDART", "BLUEJET",
    "BLUESTARCO", "BBTC", "BOSCHLTD", "FIRSTCRY", "BRIGADE", "BRITANNIA", "MAPMYINDIA", "CCL",
    "CESC", "CGPOWER", "CIEINDIA", "CRISIL", "CANFINHOME", "CANBK", "CANHLIFE", "CAPLIPOINT",
    "CGCL", "CARBORUNIV", "CARTRADE", "CASTROLIND", "CEATLTD", "CEMPRO", "CENTRALBK", "CDSL",
    "CHALET", "CHAMBLFERT", "CHENNPETRO", "CHOICEIN", "CHOLAHLDNG", "CHOLAFIN", "CIPLA", "CUB",
    "CLEAN", "COALINDIA", "COCHINSHIP", "COFORGE", "COHANCE", "COLPAL", "CAMS", "CONCORDBIO",
    "CONCOR", "COROMANDEL", "CRAFTSMAN", "CREDITACC", "CROMPTON", "CUMMINSIND", "CYIENT", "DCMSHRIRAM",
    "DLF", "DOMS", "DABUR", "DALBHARAT", "DATAPATTNS", "DEEPAKFERT", "DEEPAKNTR", "DELHIVERY",
    "DEVYANI", "DIVISLAB", "DIXON", "LALPATHLAB", "DRREDDY", "EIDPARRY", "EIHOTEL", "EICHERMOT",
    "ELECON", "ELGIEQUIP", "EMAMILTD", "EMCURE", "EMMVEE", "ENDURANCE", "ENGINERSIN", "ERIS",
    "ESCORTS", "ETERNAL", "EXIDEIND", "NYKAA", "FEDERALBNK", "FACT", "FINCABLES", "FSL",
    "FIVESTAR", "FORCEMOT", "FORTIS", "GAIL", "GVT&D", "GMRAIRPORT", "GABRIEL", "GALLANTT",
    "GRSE", "GICRE", "GILLETTE", "GLAND", "GLAXO", "GLENMARK", "MEDANTA", "GODIGIT",
    "GPIL", "GODFRYPHLP", "GODREJCP", "GODREJIND", "GODREJPROP", "GRANULES", "GRAPHITE", "GRASIM",
    "GRAVITA", "GESHIP", "FLUOROCHEM", "GMDCLTD", "HEG", "HBLENGINE", "HCLTECH", "HDBFS",
    "HDFCAMC", "HDFCBANK", "HDFCLIFE", "HFCL", "HAVELLS", "HEROMOTOCO", "HEXT", "HSCL",
    "HINDALCO", "HAL", "HINDCOPPER", "HINDPETRO", "HINDUNILVR", "HINDZINC", "POWERINDIA", "HOMEFIRST",
    "HONASA", "HONAUT", "HUDCO", "HYUNDAI", "ICICIBANK", "ICICIGI", "ICICIAMC", "ICICIPRULI",
    "IDBI", "IDFCFIRSTB", "IFCI", "IIFL", "IRB", "IRCON", "ITCHOTELS", "ITC",
    "ITI", "INDGN", "INDIACEM", "INDIAMART", "INDIANB", "IEX", "INDHOTEL", "IOC",
    "IOB", "IRCTC", "IRFC", "IREDA", "IGL", "INDUSTOWER", "INDUSINDBK", "NAUKRI",
    "INFY", "INOXWIND", "INTELLECT", "INDIGO", "IGIL", "IKS", "IPCALAB", "JKCEMENT",
    "JBMA", "JKTYRE", "JMFINANCIL", "JSWCEMENT", "JSWDULUX", "JSWENERGY", "JSWINFRA", "JSWSTEEL",
    "JAINREC", "JPPOWER", "J&KBANK", "JINDALSAW", "JSL", "JINDALSTEL", "JIOFIN", "JUBLFOOD",
    "JUBLINGREA", "JUBLPHARMA", "JWL", "JYOTICNC", "KPRMILL", "KEI", "KPITTECH", "KAJARIACER",
    "KPIL", "KALYANKJIL", "KARURVYSYA", "KAYNES", "KEC", "KFINTECH", "KIRLOSENG", "KOTAKBANK",
    "KIMS", "LTF", "LTTS", "LGEINDIA", "LICHSGFIN", "LTFOODS", "LTM", "LT",
    "LATENTVIEW", "LAURUSLABS", "THELEELA", "LEMONTREE", "LENSKART", "LICI", "LINDEINDIA", "LLOYDSME",
    "LODHA", "LUPIN", "MMTC", "MRF", "MGL", "M&MFIN", "M&M", "MANAPPURAM",
    "MRPL", "MANKIND", "MARICO", "MARUTI", "MFSL", "MAXHEALTH", "MAZDOCK", "MEESHO",
    "MINDACORP", "MSUMI", "MOTILALOFS", "MPHASIS", "MCX", "MUTHOOTFIN", "NATCOPHARM", "NBCC",
    "NCC", "NHPC", "NLCINDIA", "NMDC", "NSLNISP", "NTPCGREEN", "NTPC", "NH",
    "NATIONALUM", "NAVA", "NAVINFLUOR", "NESTLEIND", "NETWEB", "NEULANDLAB", "NEWGEN", "NAM-INDIA",
    "NIVABUPA", "NUVAMA", "NUVOCO", "OBEROIRLTY", "ONGC", "OIL", "OLAELEC", "OLECTRA",
    "PAYTM", "ONESOURCE", "OFSS", "POLICYBZR", "PCBL", "PGEL", "PIIND", "PNBHOUSING",
    "PTCIL", "PVRINOX", "PAGEIND", "PARADEEP", "PATANJALI", "PERSISTENT", "PETRONET", "PFIZER",
    "PHOENIXLTD", "PWL", "PIDILITIND", "PINELABS", "PIRAMALFIN", "PPLPHARMA", "POLYMED", "POLYCAB",
    "POONAWALLA", "PFC", "POWERGRID", "PREMIERENE", "PRESTIGE", "PFOCUS", "PNB", "RRKABEL",
    "RBLBANK", "RECLTD", "RHIM", "RITES", "RADICO", "RVNL", "RAILTEL", "RAINBOW",
    "RKFORGE", "REDINGTON", "RELIANCE", "RPOWER", "SBFC", "SBICARD", "SBILIFE", "SJVN",
    "SRF", "SAGILITY", "SAILIFE", "SAMMAANCAP", "MOTHERSON", "SAPPHIRE", "SARDAEN", "SAREGAMA",
    "SCHAEFFLER", "SCHNEIDER", "SCI", "SHREECEM", "SHRIRAMFIN", "SHYAMMETL", "ENRIN", "SIEMENS",
    "SIGNATURE", "SOBHA", "SOLARINDS", "SONACOMS", "SONATSOFTW", "STARHEALTH", "SBIN", "SAIL",
    "SUMICHEM", "SUNPHARMA", "SUNTV", "SUNDARMFIN", "SUPREMEIND", "SPLPETRO", "SUZLON", "SWANCORP",
    "SWIGGY", "SYNGENE", "SYRMA", "TBOTEK", "TVSMOTOR", "TATACAP", "TATACHEM", "TATACOMM",
    "TCS", "TATACONSUM", "TATAELXSI", "TATAINVEST", "TMCV", "TMPV", "TATAPOWER", "TATASTEEL",
    "TATATECH", "TTML", "TECHM", "TECHNOE", "TEGA", "TEJASNET", "TENNIND", "NIACL",
    "RAMCOCEM", "THERMAX", "TIMKEN", "TITAGARH", "TITAN", "TORNTPHARM", "TORNTPOWER", "TARIL",
    "TRAVELFOOD", "TRENT", "TRIDENT", "TRITURBINE", "TIINDIA", "UCOBANK", "UNOMINDA", "UPL",
    "UTIAMC", "ULTRACEMCO", "UNIONBANK", "UBL", "UNITDSPR", "URBANCO", "USHAMART", "VTL",
    "VBL", "VEDL", "VIJAYA", "VMM", "IDEA", "VOLTAS", "WAAREEENER", "WELCORP",
    "WELSPUNLIV", "WHIRLPOOL", "WIPRO", "WOCKPHARMA", "YESBANK", "ZFCVINDIA", "ZEEL", "ZENTEC",
    "ZENSARTECH", "ZYDUSLIFE", "ZYDUSWELL", "ECLERX",
]


# ---------------------------------------------------------------------------
# 1. MARKET REGIME CHECK (The Master Switch)
# ---------------------------------------------------------------------------
def check_market_regime():
    print("Checking Nifty 50 Supertrend (ATR 14, Mult 2)...")
    nifty = yf.download("^NSEI", period="1y", interval="1d", progress=False)

    if nifty.empty:
        print("Error: Could not download Nifty 50 data. Market regime check failed.")
        return "ERROR"

    if isinstance(nifty.columns, pd.MultiIndex):
        nifty.columns = nifty.columns.droplevel(1)

    st = ta.supertrend(nifty["High"], nifty["Low"], nifty["Close"], length=14, multiplier=2)

    if st is None or st.empty:
        print("Error: Could not calculate Supertrend. Market regime check failed.")
        return "ERROR"

    direction_col = [col for col in st.columns if "SUPERTd" in col and "14_2" in col]
    if not direction_col:
        print("Error: Supertrend direction column not found in pandas_ta output.")
        return "ERROR"

    current_direction = st[direction_col[0]].iloc[-1]
    status = "BUY" if current_direction == 1 else "SELL"
    print(f"MARKET REGIME: {status}")
    return status


# ---------------------------------------------------------------------------
# 2. MOMENTUM RANKING ENGINE
# ---------------------------------------------------------------------------
def get_nifty500_tickers():
    print(f"Using embedded Nifty 500 list ({len(NIFTY_500_SYMBOLS)} symbols).")
    yf_tickers = [symbol + ".NS" for symbol in NIFTY_500_SYMBOLS]
    return yf_tickers


def calculate_momentum_scores(tickers):
    print("Downloading historical data and calculating momentum scores (1-month returns only)...")
    momentum_data = []
    end_date = datetime.now()
    start_date = end_date - pd.DateOffset(months=2)

    for ticker in tickers:
        try:
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            if df.empty or len(df) < 21:
                continue

            latest_close = df["Close"].iloc[-1]

            returns_1m = (df["Close"].iloc[-1] / df["Close"].iloc[-21]) - 1
            momentum_score = returns_1m

            if not np.isnan(momentum_score):
                momentum_data.append(
                    {
                        "Ticker": ticker,
                        "1M_Return": returns_1m,
                        "Momentum_Score": momentum_score,
                        "Latest_Close": latest_close,
                    }
                )
        except Exception as e:
            print(f"Error processing {ticker}: {e}")

    momentum_df = pd.DataFrame(momentum_data)
    if momentum_df.empty:
        print("No stocks passed initial data checks.")
        return pd.DataFrame()

    momentum_df = momentum_df.sort_values(by="Momentum_Score", ascending=False).head(20)
    print(f"Top 20 stocks shortlisted based on 1-month momentum: {len(momentum_df)} stocks.")
    return momentum_df


# ---------------------------------------------------------------------------
# 3. HIGH-QUALITY SELECTION FILTERS
# ---------------------------------------------------------------------------
def apply_price_breakout_filter(momentum_df):
    print("Applying Price Breakout Filter (Current Close > Highest High of last 50 days)...")
    filtered_stocks = []
    for _, row in momentum_df.iterrows():
        ticker = row["Ticker"]
        try:
            end_date = datetime.now()
            start_date = end_date - pd.DateOffset(months=3)
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            if df.empty or len(df) < 50:
                continue

            current_close = df["Close"].iloc[-1]
            highest_high_50d = df["High"].iloc[-50:-1].max()

            if current_close > highest_high_50d:
                stock_data = row.to_dict()
                stock_data["Highest_High_50d"] = highest_high_50d
                filtered_stocks.append(stock_data)
            else:
                print(
                    f"Skipping {ticker}: No 50-day price breakout. "
                    f"(Close: {current_close:.2f}, 50d High: {highest_high_50d:.2f})"
                )
        except Exception as e:
            print(f"Error applying breakout filter to {ticker}: {e}")

    return pd.DataFrame(filtered_stocks)


def apply_volatility_filter(df_to_filter):
    print("Applying Volatility Filter (14-day ATR < 5% of Close)...")
    volatility_filtered_stocks = []
    for _, row in df_to_filter.iterrows():
        ticker = row["Ticker"]
        try:
            end_date = datetime.now()
            start_date = end_date - pd.DateOffset(months=1)
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)

            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.droplevel(1)

            if df.empty or len(df) < 14:
                continue

            required_cols = ["High", "Low", "Close"]
            for col in required_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            df.dropna(subset=required_cols, inplace=True)
            if df.empty or len(df) < 14:
                continue

            df.ta.atr(append=True, length=14)
            atr_cols = [c for c in df.columns if c.upper().startswith("ATR") and "14" in c]

            if not atr_cols:
                continue
            atr_col_name = atr_cols[0]

            latest_atr = df[atr_col_name].iloc[-1]
            current_close = df["Close"].iloc[-1]

            if pd.isna(latest_atr) or current_close == 0:
                continue

            volatility_percentage = (latest_atr / current_close) * 100

            if volatility_percentage < 5:
                stock_data = row.to_dict()
                stock_data["ATR_14"] = latest_atr
                stock_data["Volatility_Pct"] = volatility_percentage
                volatility_filtered_stocks.append(stock_data)
            else:
                print(
                    f"Skipping {ticker}: Volatility ({volatility_percentage:.2f}%) >= 5%."
                )
        except Exception as e:
            print(f"Error applying volatility filter to {ticker}: {e}")

    return pd.DataFrame(volatility_filtered_stocks)


# ---------------------------------------------------------------------------
# 4. FINAL SHORTLIST + POSITION SIZING
# ---------------------------------------------------------------------------
def build_final_shortlist(volatility_filtered_df):
    if volatility_filtered_df.empty:
        return pd.DataFrame()

    final_df = volatility_filtered_df.sort_values(
        by="Momentum_Score", ascending=False
    ).head(NUM_STOCKS).copy()

    final_df["Shares_To_Buy"] = (ALLOCATION_PER_STOCK / final_df["Latest_Close"]).apply(
        lambda x: int(x)
    )
    final_df["Capital_Deployed"] = final_df["Shares_To_Buy"] * final_df["Latest_Close"]
    return final_df


# ---------------------------------------------------------------------------
# 5. TELEGRAM DELIVERY
# ---------------------------------------------------------------------------
def send_telegram_message(message: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("\n[!] TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set — printing message instead:\n")
        print(message)
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, data=payload, timeout=15)
        resp.raise_for_status()
        print("Telegram message sent successfully.")
    except requests.exceptions.RequestException as e:
        print(f"Error sending Telegram message: {e}")
        print(f"Response: {getattr(e.response, 'text', '')}")


def format_defensive_message():
    return (
        "*⚠️ DEFENSIVE MODE ACTIVE*\n"
        "Nifty 50 Supertrend regime: *SELL*\n\n"
        "Recommended action: move funds to\n"
        "• 40% Gold\n"
        "• 40% Debt\n"
        "• 20% Cash\n\n"
        f"_Checked at {datetime.now().strftime('%Y-%m-%d %H:%M')}_"
    )


def format_unfiltered_message(momentum_df, market_status):
    """Message 1: top momentum stocks BEFORE breakout/volatility filters."""
    regime_note = "⚠️ Regime: SELL (defensive)" if market_status == "SELL" else "✅ Regime: BUY"
    ranked = momentum_df.sort_values(by="Momentum_Score", ascending=False).reset_index(drop=True)
    lines = [
        "*📊 Momentum Scan — WITHOUT Filters*",
        f"_{regime_note}_",
        f"_Top {len(ranked)} stocks by 1-month momentum_",
        "",
    ]
    for i, row in ranked.iterrows():
        lines.append(
            f"{i + 1}. *{row['Ticker']}* — "
            f"{row['Momentum_Score'] * 100:.2f}% | ₹{row['Latest_Close']:.2f}"
        )
    lines.append("")
    lines.append(f"_Generated at {datetime.now().strftime('%Y-%m-%d %H:%M')}_")
    return "\n".join(lines)


def format_shortlist_message(final_df, market_status):
    """Message 2: final shortlist AFTER breakout + volatility filters."""
    regime_note = "⚠️ Regime: SELL (defensive)" if market_status == "SELL" else "✅ Regime: BUY"
    lines = [
        "*📈 Momentum Scan — WITH Filters (Breakout + Volatility)*",
        f"_{regime_note}_",
        f"_Capital: ₹{CAPITAL:,} | Allocation/stock: ₹{ALLOCATION_PER_STOCK:,.2f}_",
        "",
    ]
    for _, row in final_df.iterrows():
        lines.append(
            f"*{row['Ticker']}*\n"
            f"  Momentum (1M): {row['Momentum_Score'] * 100:.2f}%\n"
            f"  Close: ₹{row['Latest_Close']:.2f}\n"
            f"  ATR: {row['Volatility_Pct']:.2f}%\n"
            f"  Shares: {row['Shares_To_Buy']} (₹{row['Capital_Deployed']:.2f} deployed)\n"
        )
    lines.append(f"_Generated at {datetime.now().strftime('%Y-%m-%d %H:%M')}_")
    return "\n".join(lines)


def format_no_stocks_message(market_status="BUY"):
    regime_note = "⚠️ Regime: SELL (defensive)" if market_status == "SELL" else "✅ Regime: BUY"
    return (
        "*ℹ️ Momentum Scan Complete*\n"
        f"_{regime_note}_\n"
        "No stocks passed all filters today. No trades recommended.\n\n"
        f"_Checked at {datetime.now().strftime('%Y-%m-%d %H:%M')}_"
    )


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    print(f"System initialized with Capital: ₹{CAPITAL}")
    print(f"Allocation per stock: ₹{round(ALLOCATION_PER_STOCK, 2)}")

    market_status = check_market_regime()

    if market_status == "ERROR":
        print("Market regime check failed. Aborting run.")
        sys.exit(1)

    if market_status == "SELL":
        print("\n[!] DEFENSIVE MODE ACTIVE — regime is SELL, but continuing to screen stocks anyway.")

    nifty500_tickers = get_nifty500_tickers()
    if not nifty500_tickers:
        print("Nifty 500 tickers could not be fetched. Aborting run.")
        sys.exit(1)

    momentum_shortlist_df = calculate_momentum_scores(nifty500_tickers)
    if momentum_shortlist_df.empty:
        send_telegram_message(format_no_stocks_message(market_status))
        return

    print("\nTop momentum stocks (before filters):")
    print(
        momentum_shortlist_df[["Ticker", "Momentum_Score", "Latest_Close"]].to_markdown(
            index=False
        )
    )
    # Message 1: send the unfiltered top-momentum list immediately.
    send_telegram_message(format_unfiltered_message(momentum_shortlist_df, market_status))

    breakout_filtered_df = apply_price_breakout_filter(momentum_shortlist_df)
    if breakout_filtered_df.empty:
        send_telegram_message(format_no_stocks_message(market_status))
        return

    volatility_filtered_df = apply_volatility_filter(breakout_filtered_df)
    if volatility_filtered_df.empty:
        send_telegram_message(format_no_stocks_message(market_status))
        return

    final_df = build_final_shortlist(volatility_filtered_df)
    if final_df.empty:
        send_telegram_message(format_no_stocks_message(market_status))
        return

    print("\nFinal Shortlist (after filters):")
    print(
        final_df[
            ["Ticker", "Momentum_Score", "Latest_Close", "Volatility_Pct", "Shares_To_Buy"]
        ].to_markdown(index=False)
    )

    # Message 2: send the final filtered shortlist.
    send_telegram_message(format_shortlist_message(final_df, market_status))


if __name__ == "__main__":
    main()
