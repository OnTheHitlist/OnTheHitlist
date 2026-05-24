# NSE/BSE Sandboxed Paper Trading & Backtesting Agent

A modular, high-performance Python framework for backtesting and paper-trading stocks and Exchange Traded Funds (ETFs) listed on the National Stock Exchange (NSE) and Bombay Stock Exchange (BSE) of India. 

The system simulates a virtual broker that enforces strict **zero lookahead bias**, applies price slippage, and calculates **exact Indian stock market transaction costs** (including STT, GST, SEBI charges, stamp duty, and brokerage) under a realistic monthly savings flow budget.

---

## 🚀 Key Features

*   **Zero Lookahead Bias Engine**: Coordinates multi-ticker time-series feeds step-by-step, ensuring strategy models can only inspect data up to the current simulated tick.
*   **Realistic Indian Tax Simulator**: Integrates real CDSL/broker charge calculations:
    *   Zero brokerage for Equity Delivery (CNC).
    *   0.1% Securities Transaction Tax (STT) on buys and sells.
    *   NSE Transaction Charges (0.00343%).
    *   18% GST on exchange/SEBI fees.
    *   Stamp duty (0.015% on buys).
*   **Monthly Savings Accumulator Flow**: Simulates standard retail micro-investing. Starts with a custom capital amount (e.g., Rs. 20,000) and automatically injects a recurring monthly savings amount (e.g., Rs. 20,000) to compound the portfolio.
*   **Buy-Side Rebalancing (Optimization for Small Portfolios)**: To prevent flat Depository Participant (DP) sale charges (approx. Rs. 16 per company per sell day) from eating up small portfolios, the system supports *Buy-Side-Only Rebalancing*, directing new monthly savings exclusively to underperforming assets instead of selling overperforming ones.
*   **Long-Term Backtests**: Supports multiple market regimes, including Pre-COVID compounding (2015-2019), the 2020 COVID crash, and Post-COVID bull markets.
*   **Visual Equity Curves**: Automatically plots and saves portfolio equity progression overlaid with the total cash savings baseline.

---

## 📂 Project Architecture

```
nse-bse-paper-trader/
├── config.py           # Watchlists, starting capitals, and Indian tax math
├── data_provider.py    # Caching yfinance wrapper with auto-suffix resolution (.NS)
├── broker.py           # Ledger accounts, holdings management, and slippage simulation
├── strategies.py       # Trading and investing strategy library
├── engine.py           # Simulation pipeline step-by-step orchestrator
├── utils.py            # Financial performance analytics (ROI, CAGR, Max Drawdown, Sharpe)
├── run.py              # CLI entry point to configure, run, and plot
├── requirements.txt    # Required Python libraries
└── README.md           # This documentation
```

---

## 📈 Supported Investing Strategies

### 1. Trend-Following Pullback (EMA 200 + RSI 14)
Designed to minimize whipsaws in flat markets and buy the dips of strong companies:
*   **Trend Filter**: Only buys if the current price is above the **200-day Exponential Moving Average (EMA 200)**.
*   **Pullback Trigger**: Buys when the **14-day Relative Strength Index (RSI)** drops below **40** (oversold in an uptrend).
*   **Risk Shields**: Sells when the price drops **6%** below the average purchase cost (Stop-Loss) or gains **15%** (Take-Profit), or when the stock becomes overbought (RSI >= 70).

### 2. Multi-Asset Dynamic Rebalancing (Equity + Gold + Cash)
Designed for low volatility and steady capital appreciation:
*   **Target Allocation**: 60% Nifty ETF (`NIFTYBEES.NS`), 30% Gold ETF (`GOLDBEES.NS`), and 10% Cash/Liquid ETF (`LIQUIDBEES.NS`).
*   **Rebalancing Loop**: Periodically analyzes holdings and allocates new capital injections to align weights with target allocations.

### 3. Simple SMA Crossover
*   Buys on golden crosses (20-day SMA crosses above 50-day SMA).
*   Sells on death crosses (20-day SMA crosses below 50-day SMA).

### 4. Periodic Stock SIP
*   Buys a flat rupee amount of specified watchlisted stocks at regular trading intervals.

---

## ⚙️ Installation

1.  **Prerequisites**: Ensure you have Python 3.10+ and the `uv` package manager installed.
2.  **Initialize Virtual Environment**:
    ```bash
    uv venv
    .venv\Scripts\activate  # On Windows PowerShell
    ```
3.  **Install Dependencies**:
    ```bash
    uv pip install -r requirements.txt
    ```

---

## 🖥️ Usage

Run backtests and paper simulations using the CLI runner `run.py`:

```bash
# Run the Trend-Following Pullback stock strategy (long term 2015-2026)
uv run run.py --strategy trend --start-date 2015-01-01 --end-date 2026-05-23 --capital 20000 --monthly-injection 20000

# Run the Multi-Asset ETF Rebalancing strategy (long term 2015-2026)
uv run run.py --strategy rebalance --start-date 2015-01-01 --end-date 2026-05-23 --capital 20000 --monthly-injection 20000

# Run a simple SMA Crossover on a custom starting capital
uv run run.py --strategy sma --capital 100000 --monthly-injection 0
```

### Command Line Arguments:
*   `--strategy`: Select strategy (`sma`, `sip`, `trend`, `rebalance`).
*   `--capital`: Starting capital in INR (default: `20000.0`).
*   `--monthly-injection`: Monthly cash flow injection (default: `20000.0`).
*   `--start-date`: Simulation start date (default: `2015-01-01`).
*   `--end-date`: Simulation end date (default: `2026-05-23`).
*   `--watchlist`: Comma-separated tickers to override defaults.

---

## 🛡️ License & Disclaimer

**Disclaimer**: Algorithmic investing and trading carry inherent risk of capital loss. Past performance does not guarantee future results. This software is built for backtesting and paper-trading research. Always verify execution parameters in a sandbox before allocating real money.
