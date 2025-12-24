import akshare as ak
import pandas as pd
import os
import streamlit as st

class DataLoader:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

    @st.cache_data
    def get_stock_name(_self, symbol):
        """Fetch stock name for a given symbol."""
        try:
            df = ak.stock_zh_a_spot_em()
            # Find the row with matching symbol
            match = df[df['代码'] == symbol]
            if not match.empty:
                return match['名称'].values[0]
            return "未知"
        except Exception:
            return "未知"

    def get_stock_data(self, symbol, start_date, end_date, use_cache=True):
        """
        Fetch stock data from AKShare and return a formatted DataFrame.
        """
        cache_path = os.path.join(self.data_dir, f"{symbol}_{start_date}_{end_date}.csv")
        
        if use_cache and os.path.exists(cache_path):
            df = pd.read_csv(cache_path, index_col=0, parse_dates=True)
            return df

        try:
            # Fetch from AKShare
            df = ak.stock_zh_a_hist(
                symbol=symbol, 
                period="daily", 
                start_date=start_date.replace("-", ""), 
                end_date=end_date.replace("-", ""), 
                adjust="qfq"
            )
            
            if df.empty:
                return pd.DataFrame()

            # Format for Backtrader
            # Columns: 日期, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
            df = df[['日期', '开盘', '最高', '最低', '收盘', '成交量']]
            df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            df.sort_index(inplace=True)

            # Save to cache
            if use_cache:
                df.to_csv(cache_path)
            
            return df
            
        except Exception as e:
            st.error(f"Error fetching data for {symbol}: {e}")
            return pd.DataFrame()

    def get_realtime_quotes(self, symbol):
        """Fetch real-time spot price and change for A-share."""
        try:
            df = ak.stock_zh_a_spot_em()
            match = df[df['代码'] == symbol]
            if not match.empty:
                return {
                    'price': float(match['最新价'].values[0]),
                    'change_pct': float(match['涨跌幅'].values[0]),
                    'high': float(match['最高'].values[0]),
                    'low': float(match['最低'].values[0]),
                    'volume': float(match['成交量'].values[0]),
                    'name': match['名称'].values[0]
                }
            return None
        except Exception:
            return None

    def get_intraday_data(self, symbol, period="1"):
        """Fetch intraday minute-level data from AKShare."""
        try:
            # Using stock_zh_a_hist_min_em for intraday
            df = ak.stock_zh_a_hist_min_em(
                symbol=symbol,
                period=period,
                adjust="qfq"
            )
            if df.empty:
                return pd.DataFrame()
            
            # Format: 时间, 开盘, 收盘, 最高, 最低, 成交量, 成交额, 振幅, 涨跌幅, 涨跌额, 换手率
            df = df[['时间', '开盘', '最高', '最低', '收盘', '成交量']]
            df.columns = ['datetime', 'open', 'high', 'low', 'close', 'volume']
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            df.sort_index(inplace=True)
            return df
        except Exception as e:
            st.error(f"Error fetching intraday data: {e}")
            return pd.DataFrame()
