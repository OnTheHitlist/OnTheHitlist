"""
NSE/BSE Paper Trading sandbox CLI execution entry point.
"""
import argparse
from datetime import datetime, timedelta
import logging
import matplotlib.pyplot as plt
import os
import pandas as pd

from config import STARTING_CAPITAL, DEFAULT_WATCHLIST
from data_provider import DataProvider
from broker import MockBroker
from engine import SimulationEngine
from strategies import SMACrossoverStrategy, PeriodicSIPStrategy, TrendPullbackStrategy, MultiAssetRebalanceStrategy
from utils import calculate_performance_metrics, print_performance_report, print_trade_log_table, print_yearly_report

# Predefined ETFs for rebalancing
ETF_WATCHLIST = ["NIFTYBEES", "GOLDBEES", "LIQUIDBEES"]

def parse_args():
    parser = argparse.ArgumentParser(description="NSE/BSE Paper Trading Simulator")
    parser.add_argument(
        "--strategy",
        type=str,
        default="trend",
        choices=["sma", "sip", "trend", "rebalance"],
        help="Strategy to run: 'sma', 'sip', 'trend' (EMA + RSI), or 'rebalance' (Multi-Asset ETF)"
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=20000.0,
        help="Starting virtual capital in INR (default: Rs. 20,000.00)"
    )
    parser.add_argument(
        "--monthly-injection",
        type=float,
        default=20000.0,
        help="Monthly capital savings injected into the broker in INR (default: Rs. 20,000.00)"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        default="2015-01-01",
        help="Start date for simulation YYYY-MM-DD (default: 2015-01-01 for Pre-COVID 5 years)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        default="2026-05-23",
        help="End date for simulation YYYY-MM-DD (default: 2026-05-23)"
    )
    parser.add_argument(
        "--watchlist",
        type=str,
        default="",
        help="Comma-separated stock symbols (e.g. RELIANCE,TCS,INFY). Defaults based on strategy."
    )
    return parser.parse_args()

def main():
    args = parse_args()
    
    # Auto-select watchlists if not specified
    if args.watchlist:
        symbols = [s.strip().upper() for s in args.watchlist.split(",") if s.strip()]
    else:
        if args.strategy == "rebalance":
            symbols = ETF_WATCHLIST
        else:
            symbols = DEFAULT_WATCHLIST
            
    # 1. Fetch market data
    data_provider = DataProvider()
    data_dict, timeline = data_provider.get_streaming_feed(
        symbols=symbols,
        start_date=args.start_date,
        end_date=args.end_date
    )
    
    if not timeline or not data_dict:
        logging.error("No market data fetched. Exiting.")
        return
        
    # 2. Setup broker and engine
    broker = MockBroker(starting_capital=args.capital)
    engine = SimulationEngine(broker, data_dict, timeline)
    
    # 3. Select strategy
    if args.strategy == "sma":
        strategy_class = SMACrossoverStrategy
        kwargs = {"fast_period": 20, "slow_period": 50, "allocation_pct": 0.20}
        logging.info("Running SMA Crossover Strategy (Fast: 20, Slow: 50, Allocation: 20% per trade)")
    elif args.strategy == "sip":
        strategy_class = PeriodicSIPStrategy
        kwargs = {"sip_amount_per_stock": 2000.0, "frequency_bars": 20}
        logging.info("Running Periodic SIP Strategy (Rs. 2,000 per stock every 20 trading days)")
    elif args.strategy == "trend":
        strategy_class = TrendPullbackStrategy
        kwargs = {"ema_period": 200, "rsi_period": 14, "allocation_pct": 0.20, "stop_loss_pct": 0.06, "take_profit_pct": 0.15}
        logging.info("Running Trend-Following Pullback Strategy (EMA 200 + RSI 14, SL: 6%, TP: 15%)")
    elif args.strategy == "rebalance":
        strategy_class = MultiAssetRebalanceStrategy
        kwargs = {"weights": {"NIFTYBEES": 0.60, "GOLDBEES": 0.30, "LIQUIDBEES": 0.10}, "rebalance_frequency": 20}
        logging.info("Running Multi-Asset ETF Rebalancing Strategy (60% Nifty, 30% Gold, 10% Cash)")
    else:
        logging.error("Unknown strategy selection.")
        return
        
    # 4. Run simulation with monthly capital injections
    equity_curve, timestamps = engine.run(strategy_class, monthly_injection=args.monthly_injection, **kwargs)
    
    # 5. Process results
    metrics = calculate_performance_metrics(equity_curve, timestamps, broker.trade_log, args.capital)
    
    # 6. Display Reports
    print_performance_report(metrics)
    print_yearly_report(equity_curve, timestamps, broker.deposit_log, broker.trade_log, args.capital)
    print_trade_log_table(broker.trade_log, limit=20)
    
    # 7. Plot Equity Curve
    try:
        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, equity_curve, label="Paper Trader Portfolio Equity", color="#00C805", linewidth=2.0)
        
        # Calculate and plot cumulative capital injected curve over time
        injected_curve = []
        for t in timestamps:
            year_deps = sum([d["amount"] for d in broker.deposit_log if d["timestamp"] is not None and d["timestamp"] <= t])
            injected_curve.append(args.capital + year_deps)
            
        plt.plot(timestamps, injected_curve, label="Total Capital Injected", color="blue", linestyle="--", alpha=0.7)
        
        plt.title(f"NSE/BSE Paper Trader Equity Curve - {args.strategy.upper()} Strategy", fontsize=14, fontweight="bold")
        plt.xlabel("Timeline Date", fontsize=12)
        plt.ylabel("Portfolio Value (INR)", fontsize=12)
        plt.grid(True, linestyle=":", alpha=0.6)
        plt.legend(loc="upper left")
        
        # Save plot
        plot_filename = f"equity_curve_{args.strategy}.png"
        plt.savefig(plot_filename, dpi=300, bbox_inches="tight")
        logging.info(f"Equity curve chart saved to: {os.path.abspath(plot_filename)}")
        plt.close()
    except Exception as e:
        logging.warning(f"Could not generate equity curve plot: {str(e)}")

if __name__ == "__main__":
    main()
