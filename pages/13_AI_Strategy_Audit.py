import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from data_loader import DataLoader
from backtest_engine import BacktestEngine
from utils import configure_api_key

# Import all strategies
from strategies.ma_strategy import AdvancedMaStrategy
from strategies.macd_strategy import MacdStrategy
from strategies.bollinger_strategy import BollingerStrategy
from strategies.rsi_strategy import RsiStrategy
from strategies.turtle_strategy import TurtleStrategy
from strategies.kdj_strategy import KdjStrategy
from strategies.dual_thrust_strategy import DualThrustStrategy

st.set_page_config(page_title="AI Strategy Audit", page_icon="🕵️", layout="wide")

st.title("🕵️ AI 策略诊断专家 (AI Strategy Audit)")
st.caption("全策略自动化扫描 + DeepSeek AI 深度诊股报告")

# Initialize modules
loader = DataLoader()

# --- Sidebar ---
with st.sidebar:
    st.header("🔍 目标选择")
    symbol = st.text_input("股票代码", "600519", help="输入A股代码")
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        start_date = st.date_input("开始日期", datetime.now() - timedelta(days=365*2))
    with col_d2:
        end_date = st.date_input("结束日期", datetime.now())
    
    st.divider()
    st.header("💰 账户设置")
    initial_cash = st.number_input("初始资金", 10000, 1000000, 100000)
    pos_size_pct = st.slider("仓位控制 (%)", 10, 100, 95)
    commission = st.number_input("佣金率 (%)", 0.0, 1.0, 0.1) / 100

# --- Main App ---
st.info("""
**工作原理**：
1. 本引擎会使用 **7 种核心量化策略** 的默认参数对该股票进行回测。
2. 汇总各策略的回报率、回撤、胜率及夏普比率。
3. 将数据提交给 **DeepSeek AI** 进行深度剖析，生成最终的投资建议报告。
""")

if st.button("🚀 开启全维度诊断", use_container_width=True):
    # 1. Load Data
    with st.spinner("📥 正在抓取市场历史数据..."):
        df = loader.get_stock_data(symbol, str(start_date), str(end_date))
    
    if df.empty:
        st.error("数据加载失败。")
        st.stop()
    
    engine = BacktestEngine(initial_cash=initial_cash, commission=commission)
    
    # 2. Define Strategies
    strategies_to_test = [
        ("MA 交叉", AdvancedMaStrategy, {}),
        ("MACD 趋势", MacdStrategy, {}),
        ("布ging带回归", BollingerStrategy, {}),
        ("RSI 反转", RsiStrategy, {}),
        ("海龟交易", TurtleStrategy, {}),
        ("KDJ 信号", KdjStrategy, {}),
        ("Dual Thrust", DualThrustStrategy, {})
    ]
    
    # 3. Batch Backtest
    results = []
    progress_bar = st.progress(0)
    for i, (name, cls, params) in enumerate(strategies_to_test):
        with st.status(f"正在运行策略: {name}...", expanded=False):
            try:
                res = engine.run(cls, df, pos_size=pos_size_pct/100, **params)
                strat_obj = res['strat']
                sharpe = strat_obj.analyzers.sharpe.get_analysis().get('sharperatio', 0) or 0
                max_dd = strat_obj.analyzers.drawdown.get_analysis().max.drawdown
                ret_pct = ((res['final_value'] - initial_cash) / initial_cash) * 100
                
                results.append({
                    "策略名称": name,
                    "累计收益 %": f"{ret_pct:.2f}%",
                    "夏普比率": f"{sharpe:.2f}",
                    "最大回撤 %": f"{max_dd:.2f}%",
                    "期末价值": f"¥{res['final_value']:,.2f}",
                    "_raw_ret": ret_pct
                })
            except Exception as e:
                st.warning(f"{name} 运行中遇到小插曲: {e}")
        progress_bar.progress((i + 1) / len(strategies_to_test))

    # 4. Display Summary Table
    res_df = pd.DataFrame(results)
    st.divider()
    st.subheader("📊 扫描结果汇总")
    st.dataframe(res_df.drop(columns=['_raw_ret']), use_container_width=True)

    # 5. Manual AI Analysis Button
    st.divider()
    api_key = configure_api_key()
    if api_key:
        if st.button("🤖 生成 AI 策略诊断报告", use_container_width=True):
            with st.spinner("🤖 AI 正在对上述数据进行深度建模与逻辑推理..."):
                try:
                    llm = ChatOpenAI(
                        model='deepseek-chat',
                        openai_api_key=api_key,
                        openai_api_base='https://api.deepseek.com/v1',
                        max_tokens=1500
                    )
                    
                    prompt = ChatPromptTemplate.from_template("""
                    你是一位资深的量化策略分析师。请分析以下针对股票代码 {symbol} 的多种量化策略回测结果。
                    
                    回测数据汇总：
                    {results_table}
                    
                    请提供深入的专业诊断方案：
                    1. **冠军解读**：识别表现最好的策略，从指标原理和该时间段的股价形态（趋势/震荡）解释其胜出的原因。
                    2. **风险评估**：重点分析最大回撤，识别哪些策略在这种行情下表现得过于脆弱。
                    3. **资产配置建议**：如果你是投资经理，你会如何通过整合这些信号来操作这只股票？
                    4. **参数优化建议**：针对当前发现的缺陷，建议调优哪些具体参数？
                    5. **总结性评分**：给这只股票基于目前各策略的响应情况打分（1-10分）。
                    
                    请严格使用 Markdown 格式，语言风格要求极简、犀利且极具专业性。
                    """)
                    
                    chain = prompt | llm
                    ai_response = chain.invoke({
                        "symbol": symbol,
                        "results_table": res_df.to_markdown()
                    })
                    
                    st.divider()
                    st.header("🧠 AI 策略诊断报告 (诊断书)")
                    st.markdown(ai_response.content)
                    
                    # Downloadable MD
                    full_md = f"# {symbol} 策略诊断报告\n\n## 1. 回测数据概览\n\n{res_df.to_markdown()}\n\n## 2. AI 深度诊断结论\n\n{ai_response.content}"
                    st.download_button("📥 下载完整诊断报告 (.md)", data=full_md, file_name=f"AI_Audit_{symbol}.md")
                    
                except Exception as ex:
                    st.error(f"AI 生成过程中发生异常: {ex}")
    else:
        st.warning("⚠️ 检测到未配置 DeepSeek API Key，无法激活 AI 诊断模块。请在侧边栏配置。")

else:
    st.info("👈 在左侧设置好回测参数，点击下方按钮开始‘会诊’。")
