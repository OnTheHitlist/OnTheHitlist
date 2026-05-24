"""
Global configurations and transaction tax logic for the NSE/BSE Paper Trading sandbox.
"""
import os

# Starting Virtual Capital in INR
STARTING_CAPITAL = 1000000.0  # ₹10,000,000 (10 Lakhs)

# Default Watchlist of highly liquid NSE Stocks
DEFAULT_WATCHLIST = ["RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "SBIN", "BHARTIARTL", "ITC"]

# Slippage factor (0.05% price impact simulated on order execution)
DEFAULT_SLIPPAGE_PCT = 0.0005

# Tax and Charges calculation functions based on Indian regulatory standards (Retail Delivery - CNC)
def calculate_delivery_charges(qty: int, price: float, action: str) -> dict:
    """
    Calculates detailed breakdown of taxes and charges for Equity Delivery (CNC) in India.
    Based on standard retail discount broker structures (like Zerodha/AngelOne).
    
    Taxes details:
    - Brokerage: Zero (Free for delivery)
    - STT (Securities Transaction Tax): 0.1% on both buy and sell sides
    - Exchange Transaction Charges (NSE): 0.00343% of total turnover
    - SEBI Turnover Fee: 0.0001% of total turnover (₹10 per crore)
    - Stamp Duty: 0.015% on BUY only (not applicable on SELL)
    - GST: 18% of (Brokerage + Exchange Transaction Charges + SEBI Fee)
    """
    turnover = qty * price
    action = action.upper()
    
    # 1. Brokerage (Zero for delivery)
    brokerage = 0.0
    
    # 2. STT (0.1% on buy and sell)
    stt = turnover * 0.001
    
    # 3. Exchange Transaction Charges (NSE standard: 0.00343%)
    exchange_charges = turnover * 0.0000343
    
    # 4. SEBI Turnover Fee (0.0001%)
    sebi_charges = turnover * 0.000001
    
    # 5. Stamp Duty (0.015% on buy only)
    stamp_duty = (turnover * 0.00015) if action == "BUY" else 0.0
    
    # 6. GST (18% on Brokerage + Exchange charges + SEBI charges)
    gst = (brokerage + exchange_charges + sebi_charges) * 0.18
    
    total_charges = brokerage + stt + exchange_charges + sebi_charges + stamp_duty + gst
    
    return {
        "turnover": turnover,
        "brokerage": brokerage,
        "stt": stt,
        "exchange_charges": exchange_charges,
        "sebi_charges": sebi_charges,
        "stamp_duty": stamp_duty,
        "gst": gst,
        "total_charges": total_charges
    }
