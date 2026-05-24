"""
Performance analysis utilities. Computes ROI, max drawdown, Sharpe ratio, and formats logs.
"""
import pandas as pd
import numpy as np
from tabulate import tabulate

def calculate_performance_metrics(equity_curve: list, timestamps: list, trade_log: list, initial_capital: float) -> dict:
    """
    Computes professional portfolio performance metrics.
    """
    if not equity_curve:
        return {}
        
    df_equity = pd.DataFrame({"equity": equity_curve}, index=timestamps)
    df_equity["returns"] = df_equity["equity"].pct_change()
    
    # 1. Basic ROI
    final_equity = equity_curve[-1]
    total_profit = final_equity - initial_capital
    roi_pct = (total_profit / initial_capital) * 100
    
    # 2. Maximum Drawdown (Peak to Trough decline)
    rolling_peak = df_equity["equity"].cummax()
    drawdowns = (df_equity["equity"] - rolling_peak) / rolling_peak
    max_drawdown = drawdowns.min() * 100  # in %
    
    # 3. Annualized Return (CAGR)
    # Assumes 252 trading days in a standard year
    num_days = len(df_equity)
    years = num_days / 252.0 if num_days > 0 else 0
    if years > 0 and final_equity > 0:
        cagr = ((final_equity / initial_capital) ** (1 / years) - 1) * 100
    else:
        cagr = 0.0
        
    # 4. Sharpe Ratio (assuming 6% annual risk-free rate in India)
    rf_daily = 0.06 / 252
    daily_returns = df_equity["returns"].dropna()
    excess_returns = daily_returns - rf_daily
    if len(daily_returns) > 1 and daily_returns.std() > 0:
        daily_sharpe = excess_returns.mean() / daily_returns.std()
        annualized_sharpe = daily_sharpe * np.sqrt(252)
    else:
        annualized_sharpe = 0.0
        
    # 5. Trade Analysis
    num_trades = len(trade_log)
    buy_trades = [t for t in trade_log if t["action"] == "BUY"]
    sell_trades = [t for t in trade_log if t["action"] == "SELL"]
    
    # Total Transaction costs
    total_fees = sum([t["total_fees"] for t in trade_log])
    stt_paid = sum([t["charges"]["stt"] for t in trade_log])
    brokerage_paid = sum([t["charges"]["brokerage"] for t in trade_log])
    other_taxes = total_fees - brokerage_paid - stt_paid
    
    metrics = {
        "initial_capital": initial_capital,
        "final_equity": final_equity,
        "total_profit": total_profit,
        "roi_pct": roi_pct,
        "cagr": cagr,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": annualized_sharpe,
        "num_trades": num_trades,
        "buy_trades_count": len(buy_trades),
        "sell_trades_count": len(sell_trades),
        "total_fees": total_fees,
        "stt_paid": stt_paid,
        "brokerage_paid": brokerage_paid,
        "other_taxes": other_taxes
    }
    return metrics


def print_performance_report(metrics: dict):
    """
    Renders the metrics to a clean, formatted terminal output.
    """
    if not metrics:
        print("No simulation data to report.")
        return
        
    summary_data = [
        ["Initial Capital", f"Rs. {metrics['initial_capital']:,.2f}"],
        ["Final Portfolio Value", f"Rs. {metrics['final_equity']:,.2f}"],
        ["Net Profit/Loss", f"Rs. {metrics['total_profit']:,.2f}"],
        ["Total Return (ROI)", f"{metrics['roi_pct']:.2f}%"],
        ["Annualized Return (CAGR)", f"{metrics['cagr']:.2f}%"],
        ["Maximum Drawdown", f"{metrics['max_drawdown']:.2f}%"],
        ["Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}"],
    ]
    
    trade_data = [
        ["Total Executed Orders", metrics['num_trades']],
        ["  Buy Orders", metrics['buy_trades_count']],
        ["  Sell Orders", metrics['sell_trades_count']],
        ["Total Taxes & Charges", f"Rs. {metrics['total_fees']:,.2f}"],
        ["  STT Paid", f"Rs. {metrics['stt_paid']:,.2f}"],
        ["  Brokerage Paid", f"Rs. {metrics['brokerage_paid']:,.2f}"],
        ["  GST, Exchange, Stamp Duty", f"Rs. {metrics['other_taxes']:,.2f}"],
    ]
    
    print("\n" + "="*50)
    print("         NSE/BSE SANDBOX PORTFOLIO REPORT")
    print("="*50)
    print(tabulate(summary_data, headers=["Metric", "Value"], tablefmt="grid"))
    print("\n" + "="*50)
    print("               TRADE & TAX STATS")
    print("="*50)
    print(tabulate(trade_data, headers=["Parameter", "Value"], tablefmt="grid"))
    print("\n" + "="*50)


def print_trade_log_table(trade_log: list, limit: int = 15):
    """
    Prints a beautiful table summarizing individual trades.
    """
    if not trade_log:
        print("No trades executed during this run.")
        return
        
    headers = ["Timestamp", "Symbol", "Action", "Qty", "Gross Price", "Net Capital Impact"]
    rows = []
    
    for t in trade_log[-limit:]:
        rows.append([
            str(t["timestamp"])[:10],
            t["symbol"],
            t["action"],
            t["qty"],
            f"Rs. {t['gross_price']:,.2f}",
            f"Rs. {t['net_capital_impact']:,.2f}"
        ])
        
    print(f"\nLast {min(limit, len(trade_log))} Executed Trades Log:")
    print(tabulate(rows, headers=headers, tablefmt="simple"))


def print_yearly_report(equity_curve: list, timestamps: list, deposit_log: list, trade_log: list, initial_capital: float):
    """
    Prints a beautiful year-by-year report, comparing injected capital vs portfolio value.
    """
    if not equity_curve:
        print("No data available for yearly reporting.")
        return
        
    df = pd.DataFrame({"equity": equity_curve}, index=timestamps)
    years = sorted(list(df.index.year.unique()))
    
    headers = ["Year", "Injected Capital", "Year-End Value", "Net Profit/Loss", "ROI (%)", "Taxes Paid"]
    rows = []
    
    # Track cumulative deposits to know the base at the end of each year
    cum_injected = initial_capital
    
    for year in years:
        df_year = df[df.index.year == year]
        if df_year.empty:
            continue
            
        # Year-end portfolio value
        year_end_value = df_year["equity"].iloc[-1]
        
        # Calculate capital injected during this specific year
        year_deposits = sum([d["amount"] for d in deposit_log if d["timestamp"] is not None and hasattr(d["timestamp"], "year") and d["timestamp"].year == year])
        
        # Accumulate injected capital
        if year == years[0]:
            cum_injected = initial_capital + year_deposits
        else:
            cum_injected += year_deposits
            
        # Net Profit/Loss for this year's end cumulative base
        net_pl = year_end_value - cum_injected
        roi = (net_pl / cum_injected) * 100 if cum_injected > 0 else 0.0
        
        # Calculate taxes paid during this specific year
        year_taxes = 0.0
        for t in trade_log:
            ts = t["timestamp"]
            if ts == "N/A" or ts is None:
                continue
            ts_year = None
            if hasattr(ts, "year"):
                ts_year = ts.year
            else:
                try:
                    ts_year = pd.Timestamp(ts).year
                except:
                    if str(year) in str(ts):
                        ts_year = year
            if ts_year == year:
                year_taxes += t["total_fees"]
                
        rows.append([
            year,
            f"Rs. {cum_injected:,.2f}",
            f"Rs. {year_end_value:,.2f}",
            f"Rs. {net_pl:,.2f}",
            f"{roi:.2f}%",
            f"Rs. {year_taxes:,.2f}"
        ])
        
    print("\n" + "="*75)
    print("                     YEAR-BY-YEAR PERFORMANCE REPORT")
    print("="*75)
    print(tabulate(rows, headers=headers, tablefmt="grid"))
    print("="*75 + "\n")


