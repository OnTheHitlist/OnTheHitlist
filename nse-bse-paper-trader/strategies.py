"""
Investment and trading strategies library.
"""
import pandas as pd
import numpy as np
from broker import MockBroker
import logging

class BaseStrategy:
    def __init__(self, broker: MockBroker):
        self.broker = broker
        
    def on_bar(self, timestamp, current_prices: dict, data_history: dict):
        """
        Callback executed on every historical bar or real-time tick.
        Arguments:
        - timestamp: The current bar's timestamp.
        - current_prices: Dictionary of {symbol: float} for the current bar's close price.
        - data_history: Dictionary of {symbol: DataFrame} containing data up to the current bar (inclusive).
        """
        raise NotImplementedError("Strategies must implement the on_bar method.")


class SMACrossoverStrategy(BaseStrategy):
    """
    Simple Moving Average Crossover Strategy.
    - Buys when fast SMA crosses above slow SMA (Bullish Crossover / Golden Cross).
    - Sells when fast SMA crosses below slow SMA (Bearish Crossover / Death Cross).
    """
    def __init__(self, broker: MockBroker, fast_period: int = 20, slow_period: int = 50, allocation_pct: float = 0.20):
        super().__init__(broker)
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.allocation_pct = allocation_pct  # Max % of current portfolio value to invest per stock trade
        
    def on_bar(self, timestamp, current_prices: dict, data_history: dict):
        portfolio_value = self.broker.get_portfolio_value(current_prices)
        
        for symbol, df in data_history.items():
            # Ensure we have enough data points to compute SMAs
            if len(df) < self.slow_period:
                continue
                
            close_prices = df['Close']
            
            # Calculate fast and slow moving averages
            fast_sma = close_prices.rolling(window=self.fast_period).mean().iloc[-1]
            slow_sma = close_prices.rolling(window=self.slow_period).mean().iloc[-1]
            
            # Previous moving averages (to check for crossover)
            prev_fast_sma = close_prices.rolling(window=self.fast_period).mean().iloc[-2]
            prev_slow_sma = close_prices.rolling(window=self.slow_period).mean().iloc[-2]
            
            current_price = current_prices[symbol]
            is_holding = symbol in self.broker.holdings
            
            # Golden Cross: Fast SMA crosses above Slow SMA -> BUY
            if prev_fast_sma <= prev_slow_sma and fast_sma > slow_sma:
                if not is_holding:
                    # Allocate target capital based on portfolio value
                    target_capital = portfolio_value * self.allocation_pct
                    qty_to_buy = int(target_capital // current_price)
                    
                    if qty_to_buy > 0:
                        logging.info(f"STRATEGY: Bullish crossover on {symbol}. Fast SMA ({fast_sma:.2f}) > Slow SMA ({slow_sma:.2f}). Triggering BUY.")
                        self.broker.place_order(symbol, "BUY", qty_to_buy, current_price, timestamp)
            
            # Death Cross: Fast SMA crosses below Slow SMA -> SELL
            elif prev_fast_sma >= prev_slow_sma and fast_sma < slow_sma:
                if is_holding:
                    qty_held = self.broker.holdings[symbol]["qty"]
                    logging.info(f"STRATEGY: Bearish crossover on {symbol}. Fast SMA ({fast_sma:.2f}) < Slow SMA ({slow_sma:.2f}). Triggering SELL.")
                    self.broker.place_order(symbol, "SELL", qty_held, current_price, timestamp)


class PeriodicSIPStrategy(BaseStrategy):
    """
    Dollar-Cost-Averaging / Systematic Investment Plan (SIP) Strategy.
    Invests a fixed amount (in INR) in watchlisted stocks periodically.
    """
    def __init__(self, broker: MockBroker, sip_amount_per_stock: float = 10000.0, frequency_bars: int = 20):
        super().__init__(broker)
        self.sip_amount_per_stock = sip_amount_per_stock
        self.frequency_bars = frequency_bars
        self.bar_counter = 0
        
    def on_bar(self, timestamp, current_prices: dict, data_history: dict):
        self.bar_counter += 1
        
        # Trigger buy orders at periodic intervals (e.g., every 20 trading days/bars)
        if self.bar_counter % self.frequency_bars == 1:
            logging.info(f"STRATEGY: SIP trigger day. Deploying Rs. {self.sip_amount_per_stock:,.2f} in each watchlist stock.")
            for symbol, current_price in current_prices.items():
                qty_to_buy = int(self.sip_amount_per_stock // current_price)
                if qty_to_buy > 0:
                    self.broker.place_order(symbol, "BUY", qty_to_buy, current_price, timestamp)


class TrendPullbackStrategy(BaseStrategy):
    """
    EMA 200 + RSI 14 Trend-Following Pullback Strategy.
    - Only buy if price > EMA 200 (Long term uptrend).
    - Buy when RSI 14 < 40 (Oversold pullback).
    - Sell when RSI 14 >= 70 (Overbought).
    - Sell on Stop-Loss of 6% or Take-Profit of 15% from average buy price.
    """
    def __init__(self, broker: MockBroker, ema_period: int = 200, rsi_period: int = 14, 
                 allocation_pct: float = 0.20, stop_loss_pct: float = 0.06, take_profit_pct: float = 0.15):
        super().__init__(broker)
        self.ema_period = ema_period
        self.rsi_period = rsi_period
        self.allocation_pct = allocation_pct
        self.stop_loss_pct = stop_loss_pct
        self.take_profit_pct = take_profit_pct
        
    def _calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        if len(prices) < period + 1:
            return 50.0
        delta = prices.diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        
        avg_gain = gain.rolling(window=period).mean().iloc[-1]
        avg_loss = loss.rolling(window=period).mean().iloc[-1]
        
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def on_bar(self, timestamp, current_prices: dict, data_history: dict):
        portfolio_value = self.broker.get_portfolio_value(current_prices)
        
        for symbol, df in data_history.items():
            if len(df) < self.ema_period:
                continue
                
            close_prices = df['Close']
            current_price = current_prices[symbol]
            
            # Calculate EMA 200 and RSI 14
            ema_200 = close_prices.ewm(span=self.ema_period, adjust=False).mean().iloc[-1]
            rsi_14 = self._calculate_rsi(close_prices, self.rsi_period)
            
            is_holding = symbol in self.broker.holdings
            
            if is_holding:
                holding = self.broker.holdings[symbol]
                qty = holding["qty"]
                avg_price = holding["avg_price"]
                
                # Check Stop-Loss
                if current_price <= avg_price * (1 - self.stop_loss_pct):
                    logging.info(f"STRATEGY: Stop-Loss triggered for {symbol} at Rs. {current_price:.2f} (Bought at Rs. {avg_price:.2f}, -6%).")
                    self.broker.place_order(symbol, "SELL", qty, current_price, timestamp)
                # Check Take-Profit
                elif current_price >= avg_price * (1 + self.take_profit_pct):
                    logging.info(f"STRATEGY: Take-Profit triggered for {symbol} at Rs. {current_price:.2f} (Bought at Rs. {avg_price:.2f}, +15%).")
                    self.broker.place_order(symbol, "SELL", qty, current_price, timestamp)
                # Check Overbought exit
                elif rsi_14 >= 70:
                    logging.info(f"STRATEGY: Overbought RSI ({rsi_14:.2f} >= 70) exit triggered for {symbol} at Rs. {current_price:.2f}.")
                    self.broker.place_order(symbol, "SELL", qty, current_price, timestamp)
                    
            else:
                # Buy Signal: Price above EMA 200 (Uptrend) and RSI < 40 (Oversold Pullback)
                if current_price > ema_200 and rsi_14 < 40:
                    # Allocate based on portfolio percentage, but ensure we respect cash limits
                    target_capital = min(self.broker.cash, max(10000.0, portfolio_value * self.allocation_pct))
                    qty_to_buy = int(target_capital // current_price)
                    
                    if qty_to_buy > 0:
                        logging.info(f"STRATEGY: Pullback buy signal on {symbol}. Price (Rs. {current_price:.2f}) > EMA 200 (Rs. {ema_200:.2f}) and RSI 14 ({rsi_14:.2f} < 40). Triggering BUY.")
                        self.broker.place_order(symbol, "BUY", qty_to_buy, current_price, timestamp)


class MultiAssetRebalanceStrategy(BaseStrategy):
    """
    Multi-Asset Defensive Rebalancing Strategy.
    - Allocates 60% to Nifty ETF (NIFTYBEES.NS), 30% to Gold ETF (GOLDBEES.NS), 10% to Liquid ETF (LIQUIDBEES.NS).
    - Rebalances dynamically every 20 bars (approx. 1 month) to keep targets.
    - Sells overperforming assets first, then buys underperforming assets.
    """
    def __init__(self, broker: MockBroker, weights: dict = None, rebalance_frequency: int = 20):
        super().__init__(broker)
        self.weights = weights or {
            "NIFTYBEES": 0.60,
            "GOLDBEES": 0.30,
            "LIQUIDBEES": 0.10
        }
        self.rebalance_frequency = rebalance_frequency
        self.bar_counter = 0
        
    def on_bar(self, timestamp, current_prices: dict, data_history: dict):
        self.bar_counter += 1
        
        # Rebalance every 20 bars (monthly)
        if self.bar_counter % self.rebalance_frequency != 1:
            return
            
        portfolio_value = self.broker.get_portfolio_value(current_prices)
        logging.info(f"STRATEGY: Rebalance trigger day. Portfolio Equity: Rs. {portfolio_value:,.2f}")
        
        sell_orders = []
        buy_orders = []
        
        # Calculate deviation and build order queue
        for symbol, current_price in current_prices.items():
            # Match standard watchlist symbols to ETF weights keys (strip suffixes if any)
            clean_symbol = symbol.replace(".NS", "").replace(".BO", "")
            if clean_symbol not in self.weights:
                continue
                
            target_weight = self.weights[clean_symbol]
            target_value = portfolio_value * target_weight
            
            qty_held = self.broker.holdings.get(symbol, {}).get("qty", 0)
            current_value = qty_held * current_price
            
            target_qty = int(target_value // current_price)
            qty_diff = target_qty - qty_held
            
            if qty_diff < 0:
                sell_orders.append((symbol, abs(qty_diff), current_price))
            elif qty_diff > 0:
                buy_orders.append((symbol, qty_diff, current_price))
                
        # 1. Execute SELL orders first (to release cash)
        for symbol, qty, price in sell_orders:
            logging.info(f"REBALANCE: Selling overperforming asset {symbol} (Qty: {qty})")
            self.broker.place_order(symbol, "SELL", qty, price, timestamp)
            
        # 2. Execute BUY orders second
        for symbol, qty, price in buy_orders:
            # Recalculate max buyable in case of cash limits
            max_buyable = int(self.broker.cash // (price * (1 + self.broker.slippage_pct)))
            qty_to_buy = min(qty, max_buyable)
            if qty_to_buy > 0:
                logging.info(f"REBALANCE: Buying underperforming asset {symbol} (Qty: {qty_to_buy})")
                self.broker.place_order(symbol, "BUY", qty_to_buy, price, timestamp)

