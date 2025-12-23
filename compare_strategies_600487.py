import sys
import os
import pandas as pd
from datetime import datetime
import backtrader as bt

# Add root to path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_loader import DataLoader
from backtest_engine import BacktestEngine
from strategies.ma_strategy import AdvancedMaStrategy
from strategies.macd_strategy import MacdStrategy
from strategies.bollinger_strategy import BollingerStrategy
from strategies.rsi_strategy import RsiStrategy
from strategies.turtle_strategy import TurtleStrategy

def run_comparison():
    symbol = "600487"
    start_date = "2024-01-01"
    end_date = "2025-12-23"
    initial_cash = 100000.0
    
    print(f"Loading data for {symbol} from {start_date} to {end_date}...")
    loader = DataLoader()
    df = loader.get_stock_data(symbol, start_date, end_date)
    
    if df is None or df.empty:
        print("Error: No data found.")
        return

    engine = BacktestEngine(initial_cash=initial_cash)
    
    strategies = [
        ("Moving Average", AdvancedMaStrategy, {}),
        ("Turtle Trading", TurtleStrategy, {'trailing_stop_pct': 0.05}), # Enable Trailing Stop
        ("MACD Trend", MacdStrategy, {}),
        ("Bollinger Bands", BollingerStrategy, {}),
        ("RSI Reversion", RsiStrategy, {})
    ]
    
    results = []
    
    print("-" * 60)
    print(f"{'Strategy':<20} | {'Return':<10} | {'Sharpe':<10} | {'Drawdown':<10}")
    print("-" * 60)
    
    for name, strat_cls, params in strategies:
        try:
            # Run with 95% Position Sizing
            res = engine.run(strat_cls, df, pos_size=0.95, **params)
            
            strat_obj = res['strat']
            
            # Extract Metrics
            security_value = res['final_value']
            total_return = (security_value - initial_cash) / initial_cash * 100
            
            # Analyzers extraction (safer method)
            sharpe = strat_obj.analyzers.sharpe.get_analysis().get('sharperatio', 0)
            if sharpe is None: sharpe = 0
            
            drawdown = strat_obj.analyzers.drawdown.get_analysis().max.drawdown
            
            results.append({
                "Strategy": name,
                "Final Value": security_value,
                "Return (%)": total_return,
                "Sharpe": sharpe,
                "Max Drawdown (%)": drawdown
            })
            
            print(f"{name:<20} | {total_return:>9.2f}% | {sharpe:>9.4f}  | {drawdown:>9.2f}%")
            
        except Exception as e:
            print(f"Error running {name}: {e}")

    # Save Report
    res_df = pd.DataFrame(results).sort_values(by="Return (%)", ascending=False)
    
    md_report = f"# Strategy Analysis: {symbol}\n\n"
    md_report += f"**Period**: {start_date} to {end_date}\n"
    md_report += f"**Initial Cash**: ¥{initial_cash:,.2f}\n\n"
    md_report += res_df.to_markdown(index=False, floatfmt=".2f")
    
    output_path = "analysis_report_600487.md"
    with open(output_path, "w") as f:
        f.write(md_report)
    
    print(f"\nReport saved to {output_path}")

if __name__ == "__main__":
    run_comparison()
