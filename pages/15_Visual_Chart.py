import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from data_loader import DataLoader
from visualizer import plot_interactive_chart

st.set_page_config(page_title="Visual Chart Pro", page_icon="📈", layout="wide")

st.title("📈 交互式可视化图表 (Visual Chart Pro)")
st.caption("基于 Plotly 的动态看盘系统 | 支持缩放、均线叠加、自选管理")

# Initialize modules
loader = DataLoader()

# --- Sidebar: Stock Management ---
with st.sidebar:
    st.header("🎯 自选股管理")
    
    # Simple persistence using session state for now
    if "watchlist" not in st.session_state:
        st.session_state.watchlist = ["000973", "600522", "600105", "000547","300045","000938","600487","600498"]
    
    new_symbol = st.text_input("添加股票代码", placeholder="例如: 600036")
    if st.button("➕ 添加到自选"):
        if new_symbol and new_symbol not in st.session_state.watchlist:
            st.session_state.watchlist.append(new_symbol)
            st.rerun()
            
    st.divider()
    selected_symbol = st.selectbox("选择要分析的股票", options=st.session_state.watchlist)
    
    if st.button("🗑️ 从自选移除", type="secondary"):
        if selected_symbol in st.session_state.watchlist:
            st.session_state.watchlist.remove(selected_symbol)
            st.rerun()

    st.divider()
    st.header("⚙️ 图表设置")
    mode = st.radio("显示模式", ["历史日线", "实时分时"], index=0)
    
    if mode == "历史日线":
        lookback_years = st.slider("数据时间范围 (年)", 1, 10, 2)
        refresh_rate = None
    else:
        lookback_years = None
        refresh_rate = st.slider("自动刷新频率 (秒)", 10, 60, 30)
        st.info("💡 实时分时模式下将自动刷新行情")

# --- Main Logic ---

if selected_symbol and mode == "历史日线":
    # Historical Mode - No Auto-refresh
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * lookback_years)
    
    df = loader.get_stock_data(
        selected_symbol, 
        start_date.strftime("%Y-%m-%d"), 
        end_date.strftime("%Y-%m-%d"),
        use_cache=True
    )
    stock_name = loader.get_stock_name(selected_symbol)
    
    if not df.empty:
        # Metrics for historical
        curr_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2] if len(df) > 1 else curr_price
        chg = curr_price - prev_price
        chg_pct = (chg / prev_price) * 100
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("当前价格", f"¥{curr_price:.2f}", f"{chg_pct:.2f}%")
        col2.metric("最高价 (期间)", f"¥{df['high'].max():.2f}")
        col3.metric("最低价 (期间)", f"¥{df['low'].min():.2f}")
        col4.metric("平均成交量", f"{int(df['volume'].mean()):,}")

        st.divider()
        fig = plot_interactive_chart(df, symbol=f"{stock_name} ({selected_symbol})")
        st.plotly_chart(fig, use_container_width=True)
        
        with st.expander("🔍 查看原始数据预览"):
            st.dataframe(df.sort_index(ascending=False), use_container_width=True)
    else:
        st.error(f"未能获取 {selected_symbol} 的历史数据。")

elif selected_symbol and mode == "实时分时":
    # Real-time Mode - With Auto-refresh (Silent background updates)
    @st.fragment(run_every=refresh_rate)
    def realtime_display():
        quotes = loader.get_realtime_quotes(selected_symbol)
        
        if quotes:
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("当前实时价", f"¥{quotes['price']:.2f}", f"{quotes['change_pct']:.2f}%")
            col2.metric("今日最高", f"¥{quotes['high']:.2f}")
            col3.metric("今日最低", f"¥{quotes['low']:.2f}")
            col4.metric("今日成交量", f"{int(quotes['volume']):,}")
            
            # Silent data loading - no spinner for seamless UX
            df_min = loader.get_intraday_data(selected_symbol)
            if not df_min.empty:
                st.divider()
                fig = plot_interactive_chart(df_min, symbol=f"{quotes['name']} ({selected_symbol}) [分时]")
                st.plotly_chart(fig, use_container_width=True)
                
                with st.expander("🔍 查看分时数据"):
                    st.dataframe(df_min.sort_index(ascending=False), use_container_width=True)
            else:
                st.warning("暂无分时图数据，请确认是否处于交易时间。")
        else:
            st.error("未能获取实时报价。")
    
    realtime_display()

else:
    st.info("👈 请在左侧选择或添加股票代码以开始分析。")
