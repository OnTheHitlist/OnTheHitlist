"""
Simulation backtest and paper-trading orchestrator engine.
"""
from broker import MockBroker
import pandas as pd
import logging

class SimulationEngine:
    def __init__(self, broker: MockBroker, data_dict: dict, timeline: list):
        """
        Arguments:
        - broker: MockBroker instance.
        - data_dict: Dict of {symbol: DataFrame} containing full historical data.
        - timeline: Chronologically sorted list of datetime timestamps.
        """
        self.broker = broker
        self.data_dict = data_dict
        self.timeline = timeline
        self.equity_curve = []
        self.equity_timestamps = []
        
    def run(self, strategy_class, monthly_injection: float = 0.0, **strategy_kwargs) -> tuple:
        """
        Runs the simulation loop step-by-step.
        On each step, we provide the strategy with only data *up to the current timestamp*
        to ensure zero lookahead bias.
        """
        logging.info("Initializing simulation engine...")
        strategy = strategy_class(self.broker, **strategy_kwargs)
        
        logging.info(f"Starting simulation across {len(self.timeline)} timeline points...")
        
        last_month = None
        
        for index, timestamp in enumerate(self.timeline):
            current_prices = {}
            data_history_slice = {}
            
            # Construct the available data slice for this timestamp
            for symbol, df in self.data_dict.items():
                if timestamp in df.index:
                    # Find integer location of this timestamp
                    loc = df.index.get_loc(timestamp)
                    # Create slice from beginning to current timestamp (inclusive)
                    data_history_slice[symbol] = df.iloc[:loc + 1]
                    current_prices[symbol] = float(df.loc[timestamp, "Close"])
                else:
                    # If symbol doesn't have a bar at this timestamp, look at last available bar
                    # (handles differences in exchange trading days or delayed listings)
                    past_df = df[df.index < timestamp]
                    if not past_df.empty:
                        data_history_slice[symbol] = past_df
                        current_prices[symbol] = float(past_df.iloc[-1]["Close"])
            
            # Monthly Cash Injection logic: triggers on calendar month crossover
            if last_month is not None and timestamp.month != last_month and monthly_injection > 0:
                self.broker.add_cash(monthly_injection, timestamp)
            last_month = timestamp.month
            
            # Only trigger strategy if we have prices for the active symbols at this tick
            if current_prices:
                strategy.on_bar(timestamp, current_prices, data_history_slice)
                
                # Record portfolio equity at this step
                port_val = self.broker.get_portfolio_value(current_prices)
                self.equity_curve.append(port_val)
                self.equity_timestamps.append(timestamp)
                
        logging.info("Simulation completed.")
        return self.equity_curve, self.equity_timestamps

