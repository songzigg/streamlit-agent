import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os

from data_loader import DataLoader
from backtest_engine import BacktestEngine
from strategies.ma_strategy import AdvancedMaStrategy
from strategies.macd_strategy import MacdStrategy
from strategies.bollinger_strategy import BollingerStrategy
from strategies.rsi_strategy import RsiStrategy
from strategies.turtle_strategy import TurtleStrategy
from strategies.kdj_strategy import KdjStrategy
from strategies.dual_thrust_strategy import DualThrustStrategy
from strategies.composite_strategy import CompositeStrategy
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from utils import configure_api_key

st.set_page_config(page_title="Backtest Lab Pro", page_icon="🧪", layout="wide")

st.title("🧪 Backtest Lab Pro (Refactored)")
st.caption("模块化、工程化的量化回测系统 | Backtrader × AKShare")

# Initialize modules
loader = DataLoader()

# --- Sidebar ---
with st.sidebar:
    st.header("🔍 数据选择")
    symbol = st.text_input("股票代码", "000001", help="输入A股代码")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=365*2))
    with col_d2:
        end_date = st.date_input("结束日期", datetime.now())
    
    st.divider()
    st.header("⚙️ 模式切换")
    mode = st.radio("运行模式", ["标准回测 (Single)", "参数优化 (Optimization)", "批量策略分析 (Batch)"])
    
    st.divider()
    st.header("🧠 策略选择")
    strategy_name = st.selectbox("选择策略", ["Moving Average (MA)", "MACD Trend", "Bollinger Bands", "RSI Reversion", "Turtle Trading", "KDJ Strategy", "Dual Thrust", "Custom Composite (DIY)"])
    
    # Dynamic Params
    st.divider()
    st.header("🔧 策略参数")
    
    strat_params = {}
    strat_class = None
    opt_params = {}

    if strategy_name == "Moving Average (MA)":
        strat_class = AdvancedMaStrategy
        if mode == "标准回测 (Single)":
            p_fast = st.slider("快线 (Fast SMA)", 2, 30, 5)
            p_slow = st.slider("慢线 (Slow SMA)", 10, 120, 20)
            p_stop = st.slider("止损比例 (%)", 1.0, 20.0, 5.0) / 100
            p_take = st.slider("止盈比例 (%)", 5.0, 50.0, 15.0) / 100
            use_rsi = st.checkbox("启用 RSI 过滤")
            strat_params = dict(p_fast=p_fast, p_slow=p_slow, stop_loss=p_stop, take_profit=p_take, use_rsi=use_rsi)
        else:
            opt_fast = st.multiselect("快线范围", [3, 5, 8, 10, 13], default=[5, 10])
            opt_slow = st.multiselect("慢线范围", [20, 30, 60], default=[20, 60])
            opt_params = dict(p_fast=opt_fast, p_slow=opt_slow)

    elif strategy_name == "MACD Trend":
        strat_class = MacdStrategy
        if mode == "标准回测 (Single)":
            p_fast = st.slider("Fast Period", 5, 20, 12)
            p_slow = st.slider("Slow Period", 20, 60, 26)
            p_signal = st.slider("Signal Period", 5, 15, 9)
            strat_params = dict(p_fast=p_fast, p_slow=p_slow, p_signal=p_signal)
        else:
            opt_fast = st.multiselect("Fast Range", [10, 12, 14], default=[12])
            opt_slow = st.multiselect("Slow Range", [24, 26, 28], default=[26])
            opt_params = dict(p_fast=opt_fast, p_slow=opt_slow)

    elif strategy_name == "Bollinger Bands":
        strat_class = BollingerStrategy
        if mode == "标准回测 (Single)":
            period = st.slider("Period", 10, 50, 20)
            dev = st.slider("Dev Factor", 1.0, 3.0, 2.0)
            strat_params = dict(period=period, devfactor=dev)
        else:
            opt_p = st.multiselect("Period Range", [15, 20, 25], default=[20])
            opt_dev = st.multiselect("Dev Range", [1.5, 2.0, 2.5], default=[2.0])
            opt_params = dict(period=opt_p, devfactor=opt_dev)

    elif strategy_name == "RSI Reversion":
        strat_class = RsiStrategy
        if mode == "标准回测 (Single)":
            period = st.slider("RSI Period", 5, 30, 14)
            low = st.slider("Low (Buy)", 10, 40, 30)
            high = st.slider("High (Sell)", 60, 90, 70)
            strat_params = dict(period=period, low=low, high=high)
        else:
            opt_p = st.multiselect("Period Range", [7, 14, 21], default=[14])
            opt_low = st.multiselect("Low Range", [20, 30, 40], default=[30])
            opt_params = dict(period=opt_p, low=opt_low)

    elif strategy_name == "Turtle Trading":
        strat_class = TurtleStrategy
        if mode == "标准回测 (Single)":
            p_in = st.slider("Entry Period (Breakout)", 10, 60, 20)
            p_out = st.slider("Exit Period", 5, 30, 10)
            p_trailing = st.slider("Trailing Stop (%)", 0.0, 20.0, 0.0, help="0 means disabled") / 100
            strat_params = dict(entry_period=p_in, exit_period=p_out, trailing_stop_pct=p_trailing)
        else:
            opt_in = st.multiselect("Entry Range", [20, 55], default=[20, 55])
            opt_out = st.multiselect("Exit Range", [10, 20], default=[10, 20])
            opt_params = dict(entry_period=opt_in, exit_period=opt_out)

    elif strategy_name == "KDJ Strategy":
        strat_class = KdjStrategy
        if mode == "标准回测 (Single)":
            p_period = st.slider("Period (N)", 5, 30, 9)
            strat_params = dict(period=p_period)
        else:
            opt_p = st.multiselect("Period Range", [9, 14, 18], default=[9])
            opt_params = dict(period=opt_p)

    elif strategy_name == "Dual Thrust":
        strat_class = DualThrustStrategy
        if mode == "标准回测 (Single)":
            p_n = st.slider("Days (N)", 1, 10, 5)
            p_k1 = st.slider("K1 (Long)", 0.1, 1.0, 0.5)
            p_k2 = st.slider("K2 (Short)", 0.1, 1.0, 0.5)
            strat_params = dict(period=p_n, k1=p_k1, k2=p_k2)
        else:
            opt_n = st.multiselect("Days Range", [2, 4, 5], default=[5])
            opt_k = st.multiselect("K Range", [0.5, 0.7], default=[0.5])
            opt_params = dict(period=opt_n, k1=opt_k, k2=opt_k)

    elif strategy_name == "Custom Composite (DIY)":
        strat_class = CompositeStrategy
        if mode == "标准回测 (Single)":
            st.info("🔧 组装你的策略逻辑 (多选主信号 → AND 共振)")
            
            # Signal Multi-select
            sig_options = ["MA", "MACD", "Bollinger", "RSI", "Turtle", "KDJ", "Dual Thrust"]
            selected_sigs = st.multiselect("1. 选择主信号 (可多选)", sig_options, default=["KDJ"])
            
            c1, c2 = st.columns(2)
            with c1:
                use_trend = st.checkbox("2. 开启均线趋势过滤", value=True, help="只有站在 60 日线上方才交易")
            with c2:
                use_vol = st.checkbox("3. 开启成交量确认", value=False, help="只有放量才交易")

            strat_params = dict(
                use_ma="MA" in selected_sigs,
                use_macd="MACD" in selected_sigs,
                use_bollinger="Bollinger" in selected_sigs,
                use_rsi="RSI" in selected_sigs,
                use_turtle="Turtle" in selected_sigs,
                use_kdj="KDJ" in selected_sigs,
                use_dual_thrust="Dual Thrust" in selected_sigs,
                use_trend_filter=use_trend,
                use_vol_filter=use_vol
            )
        else:
            st.warning("组合策略目前仅支持单次回测模式，不支持参数优化。")
            strat_class = None # Disable optimization for DIY for now to avoid UI complexity

    elif mode == "批量策略分析 (Batch)":
        st.info("🚀 批量模式下将使用所有 7 个内置策略的默认参数进行对比分析。")

    st.divider()
    st.header("💰 账户设置")
    initial_cash = st.number_input("初始资金", 10000, 1000000, 100000)
    pos_size_pct = st.slider("仓位控制 (Position Size %)", 10, 100, 95, help="每次交易使用的资金比例")
    commission = st.number_input("佣金率 (%)", 0.0, 1.0, 0.1) / 100

# --- Main Execution ---

if st.button("🚀 启动任务", use_container_width=True):
    # 1. Load Data
    with st.spinner("📥 正在同步市场数据..."):
        df = loader.get_stock_data(symbol, str(start_date), str(end_date))
    
    if df.empty:
        st.error("数据加载失败，请检查代码或网络。")
        st.stop()
    
    st.success(f"成功加载 {len(df)} 条历史蜡烛图数据")
    
    engine = BacktestEngine(initial_cash=initial_cash, commission=commission)
    
    if mode == "批量策略分析 (Batch)":
        # 2. Run Batch Analysis
        strategies_to_test = [
            ("MA 交叉", AdvancedMaStrategy, {}),
            ("MACD 趋势", MacdStrategy, {}),
            ("布林带回归", BollingerStrategy, {}),
            ("RSI 反转", RsiStrategy, {}),
            ("海龟交易", TurtleStrategy, {}),
            ("KDJ 信号", KdjStrategy, {}),
            ("Dual Thrust", DualThrustStrategy, {})
        ]
        
        results = []
        with st.spinner("🕵️ 正在进行全策略扫描..."):
            for name, cls, params in strategies_to_test:
                try:
                    res = engine.run(cls, df, pos_size=pos_size_pct/100, **params)
                    strat_obj = res['strat']
                    sharpe = strat_obj.analyzers.sharpe.get_analysis().get('sharperatio', 0) or 0
                    max_dd = strat_obj.analyzers.drawdown.get_analysis().max.drawdown
                    ret_pct = ((res['final_value'] - initial_cash) / initial_cash) * 100
                    
                    results.append({
                        "策略": name,
                        "累计收益 %": f"{ret_pct:.2f}%",
                        "夏普比率": f"{sharpe:.2f}",
                        "最大回撤 %": f"{max_dd:.2f}%",
                        "期末价值": f"¥{res['final_value']:,.2f}",
                        "_ret": ret_pct # for AI
                    })
                except Exception as e:
                    st.warning(f"策略 {name} 运行失败: {e}")
        
        # Display Results
        res_df = pd.DataFrame(results)
        st.subheader("📋 全策略表现对比")
        st.table(res_df.drop(columns=['_ret']))
        
        # AI Analysis
        deepseek_api_key = configure_api_key()
        if deepseek_api_key:
            with st.spinner("🤖 AI 正在深度剖析结果..."):
                try:
                    llm = ChatOpenAI(
                        model='deepseek-chat',
                        openai_api_key=deepseek_api_key,
                        openai_api_base='https://api.deepseek.com/v1',
                        max_tokens=1000
                    )
                    
                    prompt = ChatPromptTemplate.from_template("""
                    你是一位资深的量化策略分析师。请分析以下针对股票代码 {symbol} 的多种量化策略回测结果。
                    
                    回测数据如下：
                    {results_table}
                    
                    请提供以下分析：
                    1. 表现最好的策略是什么？它的优势在于捕捉了什么样的行情特征？
                    2. 考虑到收益率、回撤和风险比（夏普），你最推荐哪一个策略？
                    3. 基于数据，你对该股票目前的投资建议是什么（仅供参考）？
                    4. 建议用户如何针对目前的行情微调参数？
                    
                    请使用 Markdown 格式输出，语言简洁专业。
                    """)
                    
                    chain = prompt | llm
                    ai_response = chain.invoke({
                        "symbol": symbol,
                        "results_table": res_df.to_markdown()
                    })
                    
                    st.divider()
                    st.header("🤖 AI 策略诊断报告")
                    st.markdown(ai_response.content)
                    
                    # Report Download
                    st.divider()
                    full_report = f"# {symbol} 批量回测分析报告\n\n## 策略对比\n\n{res_df.to_markdown()}\n\n## AI 诊断\n\n{ai_response.content}"
                    st.download_button("📥 下载完整 AI 分析报告", data=full_report, file_name=f"AI_Analysis_{symbol}.md")
                except Exception as ex:
                    st.error(f"AI 分析生成失败: {ex}")
        else:
            st.warning("未配置 DeepSeek API Key，无法生成 AI 诊断报告。")

    elif mode == "标准回测 (Single)":
        # 2. Run Single Backtest
        with st.spinner("🧠 引擎运行中..."):
            res = engine.run(
                strat_class, 
                df, 
                pos_size=pos_size_pct/100,
                **strat_params
            )
        
        # 3. Display Result Dashboard
        st.divider()
        st.header("📊 策略表现看板")
        
        f_val = res['final_value']
        pnl = f_val - initial_cash
        pnl_pct = (pnl / initial_cash) * 100
        
        # Analytics Metrics
        strat = res['strat']
        sharpe = strat.analyzers.sharpe.get_analysis().get('sharperatio', 0) or 0
        max_dd = strat.analyzers.drawdown.get_analysis().max.drawdown
        trade_stats = strat.analyzers.trade.get_analysis()
        
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("期末净值", f"¥{f_val:,.2f}")
        c2.metric("累计收益", f"{pnl_pct:.2f}%", f"¥{pnl:,.2f}")
        c3.metric("夏普比率", f"{sharpe:.2f}")
        c4.metric("最大回撤", f"{max_dd:.2f}%")
        
        # Equity Curve Visualization
        st.subheader("📈 资金权益曲线")
        equity_curve = res.get('equity_curve')
        if equity_curve is not None and not equity_curve.empty:
            st.line_chart(equity_curve)
        else:
            st.info("No equity data available.")
        
        # Tabs for details
        tab_log, tab_trades, tab_data = st.tabs(["📜 交易日志", "📈 交易统计", "🔍 数据预览"])
        
        with tab_log:
            if strat.log_data:
                st.text_area("Cerebro Logs", "\n".join(strat.log_data), height=400)
            else:
                st.info("所选周期内未发生交易。")
        
        with tab_trades:
            if trade_stats:
                st.subheader("交易明细分析")
                tt = trade_stats.total.total
                if tt > 0:
                    tw = trade_stats.won.total
                    tl = trade_stats.lost.total
                    st.write(f"**总交易:** {tt} | **盈利:** {tw} | **亏损:** {tl} | **胜率:** {(tw/tt*100):.2f}%")
                    st.write(f"**平均盈亏:** ¥{trade_stats.pnl.net.average:.2f}")
                else:
                    st.write("没有已完成的交易。")
            
        with tab_data:
            st.dataframe(df, use_container_width=True)
            
        # Results Export
        st.divider()
        csv = pd.DataFrame(strat.log_data, columns=["Log Entry"]).to_csv().encode('utf-8')
        st.download_button("📥 下载详细回测报告 (CSV)", data=csv, file_name=f"report_{symbol}.csv")

    else:
        # 2. Run Optimization
        with st.spinner(f"🧬 正在进行多维参数优化..."):
            opt_df = engine.optimize(
                strat_class, 
                df, 
                pos_size=pos_size_pct/100,
                **opt_params
            )
        
        st.divider()
        st.header("🏆 优化结果对比")
        
        # Format the result table
        col_to_show = list(opt_params.keys()) + ['final_value', 'sharpe', 'max_drawdown']
        
        # Extract individual params from the dict column
        for k in opt_params.keys():
            opt_df[k] = opt_df['params'].apply(lambda x: x.get(k))
        
        display_df = opt_df[col_to_show].sort_values(by='final_value', ascending=False)
        st.dataframe(display_df.style.highlight_max(axis=0, subset=['final_value', 'sharpe']), use_container_width=True)
        
        st.subheader("💡 寻找最优解")
        if not display_df.empty:
            best = display_df.iloc[0]
            st.success(f"最优组合回报: ¥{best['final_value']:,.2f} | Sharpe: {best['sharpe']:.2f}")

else:
    # Empty State
    st.info("👆 请在侧边栏选择参数并点击 '启动任务'")
    st.image("https://backtrader.com/images/logo.png", width=100)
    st.markdown("""
    ### 升级点说明
    - **模块化**: 核心逻辑从 UI 剥离，代码更整洁。
    - **进阶策略**: 加入了成交量过滤和止盈止损。
    - **参数优化**: 支持多维网格搜索，自动寻找最优周期。
    - **持久化**: 自动缓存拉取过的数据，减少二次加载时间。
    """)
