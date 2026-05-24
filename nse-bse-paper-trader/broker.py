"""
Mock Broker sandbox to simulate holdings, trade execution, slippage, and detailed transaction costs.
"""
import logging
from config import calculate_delivery_charges, DEFAULT_SLIPPAGE_PCT

class MockBroker:
    def __init__(self, starting_capital: float = 1000000.0, slippage_pct: float = DEFAULT_SLIPPAGE_PCT):
        self.cash = starting_capital
        self.initial_capital = starting_capital
        self.slippage_pct = slippage_pct
        self.holdings = {}  # {symbol: {"qty": int, "avg_price": float}}
        self.trade_log = []  # List of executed trades
        self.deposit_log = []  # List of deposits: [{"timestamp": ts, "amount": amt}]
        
    def add_cash(self, amount: float, timestamp=None):
        """
        Injects additional cash into the broker account (used to simulate periodic savings).
        """
        self.cash += amount
        self.initial_capital += amount
        self.deposit_log.append({"timestamp": timestamp, "amount": amount})
        logging.info(f"BROKER: Cash Injected: Rs. {amount:,.2f} at {timestamp or 'N/A'}. New Cash Balance: Rs. {self.cash:,.2f}. Total Injected Capital: Rs. {self.initial_capital:,.2f}")


        
    def get_portfolio_value(self, current_prices: dict) -> float:
        """
        Returns total portfolio equity: Cash + Current Value of all active stock holdings.
        """
        holdings_value = 0.0
        for symbol, holding in self.holdings.items():
            qty = holding["qty"]
            # Fall back to average price if current price is not provided
            current_price = current_prices.get(symbol, holding["avg_price"])
            holdings_value += qty * current_price
        return self.cash + holdings_value

    def place_order(self, symbol: str, action: str, qty: int, market_price: float, timestamp=None) -> dict:
        """
        Simulates order execution with slippage and exact Indian transaction tax calculations.
        """
        action = action.upper()
        if action not in ["BUY", "SELL"]:
            return {"status": "FAILED", "reason": "Invalid action. Use BUY or SELL."}
            
        if qty <= 0:
            return {"status": "FAILED", "reason": "Quantity must be greater than zero."}

        # Apply Slippage
        # Buy orders execute slightly higher than market price, Sell orders slightly lower
        if action == "BUY":
            execution_price = market_price * (1 + self.slippage_pct)
        else:
            execution_price = market_price * (1 - self.slippage_pct)
            
        # Calculate Taxes and Charges
        charges_breakdown = calculate_delivery_charges(qty, execution_price, action)
        total_charges = charges_breakdown["total_charges"]
        gross_value = qty * execution_price

        if action == "BUY":
            total_required_cost = gross_value + total_charges
            if self.cash < total_required_cost:
                return {
                    "status": "FAILED",
                    "reason": f"Insufficient funds. Required: ₹{total_required_cost:,.2f}, Available: ₹{self.cash:,.2f}"
                }
                
            # Deduct capital
            self.cash -= total_required_cost
            
            # Update Holdings
            if symbol in self.holdings:
                current_qty = self.holdings[symbol]["qty"]
                current_avg = self.holdings[symbol]["avg_price"]
                new_qty = current_qty + qty
                # Calculate new average buy price
                new_avg = ((current_qty * current_avg) + (qty * execution_price)) / new_qty
                self.holdings[symbol] = {"qty": new_qty, "avg_price": new_avg}
            else:
                self.holdings[symbol] = {"qty": qty, "avg_price": execution_price}

        elif action == "SELL":
            if symbol not in self.holdings or self.holdings[symbol]["qty"] < qty:
                available_qty = self.holdings[symbol]["qty"] if symbol in self.holdings else 0
                return {
                    "status": "FAILED",
                    "reason": f"Insufficient shares. Required to Sell: {qty}, Available in holdings: {available_qty}"
                }
                
            # Add to capital (gross value minus transaction fees)
            net_proceeds = gross_value - total_charges
            self.cash += net_proceeds
            
            # Update Holdings
            self.holdings[symbol]["qty"] -= qty
            if self.holdings[symbol]["qty"] == 0:
                del self.holdings[symbol]

        # Log Trade
        trade_entry = {
            "timestamp": timestamp or "N/A",
            "symbol": symbol,
            "action": action,
            "qty": qty,
            "gross_price": market_price,
            "execution_price": execution_price,
            "gross_value": gross_value,
            "charges": charges_breakdown,
            "total_fees": total_charges,
            "net_capital_impact": -total_required_cost if action == "BUY" else net_proceeds
        }
        self.trade_log.append(trade_entry)
        
        logging.info(
            f"Executed {action} order for {qty} shares of {symbol} at execution price ₹{execution_price:.2f}. "
            f"Fees: ₹{total_charges:.2f}."
        )
        return {"status": "SUCCESS", "trade": trade_entry}
