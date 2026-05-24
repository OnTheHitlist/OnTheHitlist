"""
Market data provider using yfinance. Fetches, caches, and formats NSE/BSE stock data.
"""
import os
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DataProvider:
    def __init__(self, cache_dir: str = ".cache"):
        self.cache_dir = cache_dir
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
    def _resolve_ticker(self, symbol: str, exchange: str = "NSE") -> str:
        """
        Appends the appropriate suffix for Indian exchanges (.NS for NSE, .BO for BSE).
        """
        symbol = symbol.strip().upper()
        if symbol.endswith(".NS") or symbol.endswith(".BO"):
            return symbol
            
        if exchange.upper() == "NSE":
            return f"{symbol}.NS"
        elif exchange.upper() == "BSE":
            return f"{symbol}.BO"
        else:
            raise ValueError(f"Unknown exchange: {exchange}. Use 'NSE' or 'BSE'.")

    def fetch_historical_data(self, symbol: str, start_date: str, end_date: str, interval: str = "1d", exchange: str = "NSE") -> pd.DataFrame:
        """
        Fetches historical data from yfinance. Caches locally in a CSV file to minimize external requests.
        """
        ticker = self._resolve_ticker(symbol, exchange)
        cache_filename = f"{ticker}_{interval}_{start_date}_{end_date}.csv"
        cache_path = os.path.join(self.cache_dir, cache_filename)
        
        # Load from cache if it exists
        if os.path.exists(cache_path):
            logging.info(f"Loading cached data for {ticker} from {cache_path}")
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            return df
            
        logging.info(f"Downloading historical data for {ticker} from {start_date} to {end_date} (interval: {interval})...")
        try:
            # yfinance download
            df = yf.download(ticker, start=start_date, end=end_date, interval=interval, progress=False)
            
            if df.empty:
                logging.warning(f"No data returned for ticker {ticker}.")
                return pd.DataFrame()
                
            # Handle multi-index columns if returned by yf.download
            if isinstance(df.columns, pd.MultiIndex):
                # Flatten the MultiIndex to single level, keeping just the attribute (e.g. 'Close')
                df.columns = df.columns.get_level_values(0)
                
            # Cache the file
            df.to_csv(cache_path)
            logging.info(f"Cached data for {ticker} into {cache_path}")
            return df
            
        except Exception as e:
            logging.error(f"Failed to fetch data for {ticker}: {str(e)}")
            return pd.DataFrame()

    def get_streaming_feed(self, symbols: list, start_date: str, end_date: str, interval: str = "1d", exchange: str = "NSE") -> tuple:
        """
        Returns a sorted timeline of all historical ticks across multiple stocks to simulate a unified market feed.
        Outputs:
        - data_dict: {symbol: DataFrame}
        - timeline: list of datetime timestamps sorted chronologically
        """
        data_dict = {}
        all_timestamps = set()
        
        for symbol in symbols:
            df = self.fetch_historical_data(symbol, start_date, end_date, interval, exchange)
            if not df.empty:
                data_dict[symbol] = df
                all_timestamps.update(df.index)
                
        sorted_timeline = sorted(list(all_timestamps))
        return data_dict, sorted_timeline
