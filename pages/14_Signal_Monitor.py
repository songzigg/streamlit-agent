import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from data_loader import DataLoader
from backtest_engine import BacktestEngine
from utils import configure_api_key

# Import strategies
from strategies.ma_strategy import AdvancedMaStrategy
from strategies.macd_strategy import MacdStrategy
from strategies.bollinger_strategy import BollingerStrategy
from strategies.rsi_strategy import RsiStrategy
from strategies.turtle_strategy import TurtleStrategy
from strategies.kdj_strategy import KdjStrategy
from strategies.dual_thrust_strategy import DualThrustStrategy

st.set_page_config(page_title="Signal Monitor", page_icon="📡", layout="wide")

st.title("📡 实时信号监控大屏 (Signal Monitor)")
st.caption("基于回测通过的最佳策略，监控当前市场买卖点。")

# Initialize modules
loader = DataLoader()

# --- Sidebar ---
with st.sidebar:
    st.header("🎯 监控配置")
    symbols_raw = st.text_area("股票池 (代码逗号分隔)", "000973,600522,600105,000547,300045,000938,600487,600498", help="输入A股代码，用逗号或换行分隔")
    
    st.divider()
    
    # Define available strategies
    strat_map = {
        "MA": AdvancedMaStrategy,
        "MACD": MacdStrategy,
        "Boll": BollingerStrategy,
        "RSI": RsiStrategy,
        "Turtle": TurtleStrategy,
        "KDJ": KdjStrategy,
        "DualThrust": DualThrustStrategy
    }
    
    all_strat_names = list(strat_map.keys())
    
    select_all = st.checkbox("全选所有策略", value=False)
    
    selected_strategies = st.multiselect(
        "选择监控策略 (多选)", 
        options=all_strat_names,
        default=all_strat_names if select_all else ["KDJ", "RSI", "MACD"]
    )

    st.divider()
    st.header("⚙️ 扫描深度")
    lookback_days = st.slider("历史回顾天数 (用于计算指标)", 30, 200, 100)
    pos_size = st.slider("模拟仓位 (%)", 10, 100, 95) / 100

def get_signal_info(res):
    """Analyze backtest result to find the latest signal and a numeric score."""
    strat = res['strat']
    latest_logs = strat.log_data[-3:] if strat.log_data else []
    
    is_buy = any("BUY CREATE" in log for log in latest_logs)
    is_sell = any("SELL CREATE" in log for log in latest_logs)
    
    if is_buy: return "🟢 BUY", 1
    if is_sell: return "🔴 SELL", -1
    if strat.position: return "📈 HOLD", 0
    return "⚪ WAIT", 0

# --- Main App ---

target_symbols = [s.strip() for s in symbols_raw.replace('\n', ',').split(',') if s.strip()]

# Initialize session state for persistent results
if "scan_results" not in st.session_state:
    st.session_state.scan_results = None
if "last_target_symbols" not in st.session_state:
    st.session_state.last_target_symbols = []

if st.button("🔍 开始多策略实时扫描", use_container_width=True):
    if not target_symbols:
        st.warning("股票池为空。")
        st.stop()
    if not selected_strategies:
        st.warning("请至少选择一个策略。")
        st.stop()
        
    engine = BacktestEngine(initial_cash=100000)
    
    results = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=lookback_days)
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    total_steps = len(target_symbols) * len(selected_strategies)
    step_count = 0
    
    for i, symbol in enumerate(target_symbols):
        stock_name = loader.get_stock_name(symbol)
        row_data = {"代码": symbol, "名称": stock_name}
        total_score = 0
        total_ret = 0
        
        try:
            # 1. Fetch recent data (once per symbol)
            # Signal monitor should ideally fetch fresh data, so use_cache=False or short cache
            df = loader.get_stock_data(symbol, start_date.strftime("%Y-%m-%d"), end_date.strftime("%Y-%m-%d"), use_cache=False)
            
            if df.empty:
                for s_name in selected_strategies:
                    row_data[s_name] = "❌ 无数据"
                row_data["当前价格"] = "-"
                row_data["综合评分"] = 0
            else:
                curr_price = df['close'].iloc[-1]
                row_data["当前价格"] = f"¥{curr_price:.2f}"
                
                # 2. Run backtest for each selected strategy
                row_data["df"] = df
                row_data["strat_data"] = True
                for s_name in selected_strategies:
                    step_count += 1
                    status_text.text(f"⏳ 正在分析: {symbol} - {s_name} ({step_count}/{total_steps})")
                    
                    strat_cls = strat_map[s_name]
                    res = engine.run(strat_cls, df, pos_size=pos_size)
                    
                    signal_label, score = get_signal_info(res)
                    row_data[s_name] = signal_label
                    row_data[f"strat_{s_name}"] = res['strat']
                    total_score += score
                    
                    # Track average recent return
                    ret_pct = ((res['final_value'] - 100000) / 100000) * 100
                    total_ret += ret_pct
                    
                    progress_bar.progress(step_count / total_steps)
                
                row_data["综合评分"] = total_score
                row_data["平均收益率 (%)"] = f"{total_ret / len(selected_strategies):.2f}%"
                
        except Exception as e:
            row_data["错误"] = str(e)[:20]
            
        results.append(row_data)

    status_text.text("✅ 扫描完成!")
    # Save to session state
    st.session_state.scan_results = results
    st.session_state.last_target_symbols = target_symbols
    st.session_state.selected_strategies = selected_strategies

# --- Display Logic (Persists outside button click) ---
if st.session_state.scan_results is not None:
    results = st.session_state.scan_results
    last_target_symbols = st.session_state.last_target_symbols
    active_strategies = st.session_state.selected_strategies
    
    # Display Result Table
    res_df = pd.DataFrame(results)
    st.divider()
    st.subheader(f"📊 多策略实时监控看板")
    
    # Sort by consensus score
    if "综合评分" in res_df.columns:
        res_df = res_df.sort_values(by="综合评分", ascending=False)
    
    # Display columns: Code, Name, Price, [Strategies], Score, Return
    display_cols = ["代码", "名称", "当前价格"] + active_strategies + ["综合评分", "平均收益率 (%)"]
    # Filter to only existing columns
    display_cols = [c for c in display_cols if c in res_df.columns]

    # Style the table
    def style_signals(val):
        if not isinstance(val, str): return ''
        if "BUY" in val: return 'background-color: rgba(0, 255, 0, 0.2); font-weight: bold'
        if "SELL" in val: return 'background-color: rgba(255, 0, 0, 0.2); font-weight: bold'
        if "HOLD" in val: return 'background-color: rgba(0, 0, 255, 0.1)'
        return ''

    st.dataframe(
        res_df[display_cols].style.applymap(style_signals, subset=[c for c in active_strategies if c in res_df.columns]),
        use_container_width=True
    )

    # --- Detailed Visuals ---
    st.divider()
    st.subheader("🔍 单股多策略共振详图")
    # Store complete results in a dict for easy access
    detailed_results = {r['代码']: r for r in results}
    
    # Filter target symbols to those that actually have results
    avail_symbols = [s for s in last_target_symbols if s in detailed_results]
    
    selected_stock = st.selectbox("选择股票查看详细信号复现图", options=avail_symbols)
    
    if selected_stock and selected_stock in detailed_results:
        target_res = detailed_results[selected_stock]
        if "strat_data" in target_res:
            from visualizer import plot_trading_chart
            
            with st.spinner(f"正在分析 {selected_stock} 的技术共振..."):
                # Combine trade history from ALL strategies
                all_trades = []
                for sname in active_strategies:
                    if f"strat_{sname}" in target_res:
                        s_obj = target_res[f"strat_{sname}"]
                        all_trades.extend(getattr(s_obj, 'trade_history', []))
                
                df_obj = target_res["df"]
                # Passing None to strategy to avoid messy indicators in summary view
                fig = plot_trading_chart(df_obj, all_trades, strategy=None)
                st.pyplot(fig)
        else:
            st.info("该股票暂无详细回测数据。")

    # AI Analysis
    api_key = configure_api_key()
    if api_key:
        if st.button("🤖 生成 AI 策略共振分析报告"):
            with st.spinner("AI 正在深度分析中..."):
                try:
                    llm = ChatOpenAI(
                        model='deepseek-chat',
                        openai_api_key=api_key,
                        openai_api_base='https://api.deepseek.com/v1'
                    )
                    
                    prompt = ChatPromptTemplate.from_template("""
                    你是一位专业的量化交易员。你刚才对关注股票池进行了多策略实时监控，以下是综合结果：
                    
                    策略组合：{strategies}
                    监控矩阵：
                    {results_table}
                    
                    请基于多策略共振情况给出行动建议：
                    1. **强共振挖掘**：哪些股票在多个策略下同时发出了 BUY 信号？这种共振意味着什么？
                    2. **策略分歧处理**：如果某只股票在策略 A 是 BUY，但在策略 B 是 SELL，你建议如何操作？
                    3. **综合评分最高者分析**：针对“综合评分”最高的几只股票，分析其潜在的趋势强度。
                    4. **风险预警**：基于多策略结果，当前市场是否存在普遍的回撤风险或虚假信号？
                    5. **实战指导**：如何根据这些信号进行仓位分配？
                    
                    请使用专业、简洁且利于实战的语言。
                    """)
                    
                    chain = prompt | llm
                    ai_resp = chain.invoke({
                        "strategies": ", ".join(active_strategies),
                        "results_table": res_df.to_markdown()
                    })
                    
                    st.divider()
                    st.header("🤖 AI 策略共振分析报告")
                    st.markdown(ai_resp.content)
                except Exception as e:
                    st.info(f"AI 建议模块暂不可用: {e}")
else:
    st.info("👈 请在左侧选择监控策略并输入股票代码，点击按钮开始多维度实时分析。")
    st.warning("注：综合评分基于策略共识（BUY=+1, SELL=-1）。评分越高，代表多策略一致看多。")

