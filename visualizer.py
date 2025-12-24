import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

def plot_trading_chart(df, trade_history, strategy=None):
    """
    Create a technical analysis chart using Matplotlib.
    """
    import matplotlib.pyplot as plt
    import numpy as np
    
    # Use a safe style
    try:
        plt.style.use('ggplot')
    except:
        pass
        
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]}, sharex=True)
    
    # 1. Plot Price
    if not df.empty and 'close' in df.columns:
        ax1.plot(df.index, df['close'], label='Close Price', color='#1f77b4', linewidth=1.5, alpha=0.8)
    
    # 2. Plot Indicators (Optional)
    if strategy is not None:
        import backtrader as bt
        # Use a more robust way to iterate over attributes
        for attr_name in dir(strategy):
            if attr_name.startswith('_') or attr_name in ['data', 'datas', 'broker', 'stats', 'env', 'cerebro', 'p', 'params', 'setsizer', 'order', 'trade_history', 'log_data']:
                continue
            
            try:
                attr = getattr(strategy, attr_name)
                # Check if it's a Backtrader indicator or has lines
                if hasattr(attr, 'lines') and not attr_name.startswith('data'):
                    # Plot all lines in the indicator/object
                    for i in range(len(attr.lines)):
                        try:
                            line_name = ""
                            try:
                                line_name = attr.lines._getname(i)
                            except:
                                line_name = f"line{i}"
                                
                            label = f"{attr_name}" if (not line_name or line_name == 'line') else f"{attr_name}.{line_name}"
                            
                            # Safely extract line data
                            series = attr.lines[i]
                            # backtrader lines can be accessed as arrays
                            # Attempt to get the full array converted to a list of floats
                            try:
                                # get(size=...) is generally safer for finished runs
                                line_data = series.get(size=len(series))
                            except:
                                line_data = list(series.array)
                                
                            if len(line_data) > 0:
                                # Align with df.index (take the last N points where N = len(df))
                                n = len(df)
                                if len(line_data) >= n:
                                    plot_values = line_data[-n:]
                                    # Convert to numpy and handle NaNs for cleaner plotting
                                    plot_values = np.array(plot_values, dtype=float)
                                    ax1.plot(df.index, plot_values, label=label, alpha=0.6, linestyle='--')
                        except Exception:
                            continue
            except Exception:
                continue

    # 3. Plot Trade Markers
    try:
        buy_pts = [t for t in trade_history if isinstance(t, dict) and t.get('type') == 'buy']
        sell_pts = [t for t in trade_history if isinstance(t, dict) and t.get('type') == 'sell']
        
        if buy_pts:
            ax1.scatter([t['dt'] for t in buy_pts], [t['price'] for t in buy_pts], 
                        marker='^', color='green', s=100, label='BUY', zorder=5)
        if sell_pts:
            ax1.scatter([t['dt'] for t in sell_pts], [t['price'] for t in sell_pts], 
                        marker='v', color='red', s=100, label='SELL', zorder=5)
    except Exception as e:
        print(f"Error plotting trade markers: {e}")
    
    ax1.set_title("Price & Strategy Signals")
    ax1.legend(loc='best', fontsize='small', ncol=2)
    ax1.grid(True, alpha=0.3)
    
    # 4. Plot Volume
    if not df.empty and 'volume' in df.columns:
        ax2.bar(df.index, df['volume'], color='gray', alpha=0.3, label='Volume')
        ax2.set_ylabel('Volume')
    ax2.grid(True, alpha=0.3)
    
    # Use axis-specific rotation instead of plt.xticks
    for tick in ax2.get_xticklabels():
        tick.set_rotation(45)
    
    fig.tight_layout()
    
    return fig

def plot_interactive_chart(df, symbol="Stock"):
    """
    Create a professional interactive candlestick chart using Plotly.
    Includes Volume, MA indicators, and range selectors.
    """
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots
    
    # 1. Create Subplots: Price (row 1), Volume (row 2)
    fig = make_subplots(
        rows=2, cols=1, 
        shared_xaxes=True, 
        vertical_spacing=0.05, 
        row_heights=[0.7, 0.3]
    )
    
    # 2. Add Candlestick
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Candlestick',
        increasing_line_color='#ef5350', # Red for up in A-share
        decreasing_line_color='#26a69a'  # Green for down in A-share
    ), row=1, col=1)
    
    # 3. Add Moving Averages
    ma_colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
    for i, period in enumerate([5, 20, 60]):
        ma = df['close'].rolling(window=period).mean()
        fig.add_trace(go.Scatter(
            x=df.index, y=ma, 
            name=f'MA{period}',
            line=dict(width=1.5, color=ma_colors[i]),
            opacity=0.7
        ), row=1, col=1)
        
    # 4. Add Volume
    colors = ['#ef5350' if row['close'] >= row['open'] else '#26a69a' for _, row in df.iterrows()]
    fig.add_trace(go.Bar(
        x=df.index, y=df['volume'],
        name='Volume',
        marker_color=colors,
        opacity=0.5
    ), row=2, col=1)
    
    # 5. Sophisticated Layout
    fig.update_layout(
        title=f'{symbol} - 交互式可视化图表',
        template='plotly_dark',
        xaxis_rangeslider_visible=False, # Hide the bottom slider to save space
        height=700,
        margin=dict(l=50, r=50, t=50, b=50),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        )
    )
    
    # Y-axis titles
    fig.update_yaxes(title_text="Price (¥)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    # Range Selectors
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1m", step="month", stepmode="backward"),
                dict(count=6, label="6m", step="month", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(count=1, label="1y", step="year", stepmode="backward"),
                dict(step="all")
            ]),
            bgcolor='rgba(0,0,0,0)',
            activecolor='#ff7f0e'
        )
    )
    
    return fig
