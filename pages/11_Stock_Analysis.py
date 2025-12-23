import streamlit as st
import pandas as pd
import akshare as ak
import json
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from utils import configure_api_key, configure_serper_api_key
from langchain_community.utilities import GoogleSerperAPIWrapper

st.set_page_config(page_title="Stock Analysis (AKShare)", page_icon="🇨🇳", layout="wide")

# --- Configuration ---
deepseek_api_key = configure_api_key()
serper_api_key = configure_serper_api_key()

# --- Helper Functions ---

@st.cache_data(ttl=60)
def get_a_share_spot():
    """Fetch real-time spot data for ALL A-shares (for PE/PB/Turnover)."""
    try:
        # returns huge dataframe
        df = ak.stock_zh_a_spot_em()
        return df
    except Exception as e:
        st.error(f"AKShare Spot Data Error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_individual_spot(symbol):
    """Fallback fetch for a single stock's real-time quote."""
    try:
        df = ak.stock_individual_info_em(symbol=symbol)
        # Process individual info into a format similar to spot_df if needed
        # but easier to just use it as a dictionary
        return df
    except Exception as e:
        st.error(f"AKShare Individual Data Error: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_daily_data(symbol):
    try:
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", adjust="qfq")
        df.rename(columns={'日期': 'date', '开盘': 'open', '收盘': 'close', '最高': 'high', '最低': 'low', '成交量': 'volume', '涨跌幅': 'pct_chg'}, inplace=True)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=60)
def get_intraday_data(symbol):
    try:
        df = ak.stock_zh_a_minute(symbol=symbol, period="5", adjust="qfq")
        df.rename(columns={'day': 'date', 'open': 'open', 'high': 'high', 'low': 'low', 'close': 'close', 'volume': 'volume'}, inplace=True)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_financials(symbol):
    try:
        df = ak.stock_financial_abstract(symbol=symbol)
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_holders(symbol):
    try:
        df = ak.stock_share_10_top_em(symbol=symbol)
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_capital_flow(symbol):
    """Fetch historical capital flow (Main Force)."""
    try:
        # returns date, net inflow, net inflow percent, etc.
        df = ak.stock_individual_fund_flow(stock=symbol, market="sh" if symbol.startswith("6") else "sz")
        # AKShare API handles market inferencing usually, but requires symbol
        # stock_individual_fund_flow returns: 日期, 收盘价, 涨跌幅, 主力净流入-净额...
        # If market param is needed, we guess
        return df
    except:
        # Fallback without market arg if needed or just try simple
        try:
             df = ak.stock_individual_fund_flow(stock=symbol)
             return df
        except:
             return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_news(symbol):
    try:
        df = ak.stock_news_em(symbol=symbol)
        return df
    except:
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def get_serper_news(symbol, name):
    try:
        search = GoogleSerperAPIWrapper(serper_api_key=serper_api_key, type="news")
        query = f"{name} {symbol} 股票 财经 新闻"
        results = search.results(query)
        # Serper news results are in 'news' key
        return results.get('news', [])
    except Exception as e:
        st.sidebar.error(f"Serper Search Error: {e}")
        return []

# --- UI Logic ---

st.title("🇨🇳 A股五维全景扫描 (5-Dim Scanner)")
st.caption("DeepSeek × AKShare | 估值-技术-资金-基本面-情绪 | 五维战法")

col_search, col_conf = st.columns([2, 1])
with col_search:
    symbol_input = st.text_input("输入代码 (e.g. 600519)", "600519", help="仅支持A股代码")
    if st.button("🚀 启动五维诊断", key="search_btn"):
        st.session_state.ak_symbol = symbol_input
        st.rerun()

if "ak_symbol" in st.session_state:
    symbol = st.session_state.ak_symbol
    
    # 1. Fetch Spot Data (Global Filter for Dimensions 1 & 2)
    with st.spinner("🚀 正在扫描行情数据..."):
        spot_df = get_a_share_spot()
        
    # Find our stock
    target_row = None
    if not spot_df.empty:
        mask = spot_df['代码'] == symbol
        if mask.any():
            target_row = spot_df[mask].iloc[0]
            # Standardize column names if needed
            # spot_em typical columns: 代码, 名称, 最新价, 涨跌幅, 市盈率-动态, 市净率, 总市值, 换手率, 量比, 振幅
        else:
            st.warning(f"全量行情中未涉及 {symbol}，尝试拉取单股数据...")
    
    if target_row is None:
        # Fallback to individual info
        indiv_df = get_individual_spot(symbol)
        if not indiv_df.empty:
            # indiv_df is usually: item, value
            data_dict = dict(zip(indiv_df['item'], indiv_df['value']))
            # Map indiv info to what target_row expects
            target_row = {
                '代码': symbol,
                '名称': data_dict.get('股票简称', '-'),
                '最新价': data_dict.get('最新价', 0),
                '涨跌幅': data_dict.get('涨跌幅', 0),
                '市盈率-动态': data_dict.get('市盈率-动态', '-'),
                '市净率': data_dict.get('市净率', '-'),
                '总市值': data_dict.get('总市值', '-'),
                '换手率': data_dict.get('换手率', '-'),
                '量比': data_dict.get('量比', '-'),
                '振幅': data_dict.get('振幅', '-')
            }
        else:
            st.error("无法连接实时行情服务 (全量与单股均失败)")
            st.stop()

    # Extract 5-Dim Metrics
    name = target_row['名称']
    price = target_row['最新价']
    chg_pct = target_row['涨跌幅']
    
    # Valuation Info
    pe_ttm = target_row.get('市盈率-动态', '-')
    pb = target_row.get('市净率', '-')
    mkt_cap = target_row.get('总市值', '-')
    
    # Tech Info
    turnover = target_row.get('换手率', '-')
    volume_ratio = target_row.get('量比', '-') # New
    amplitude = target_row.get('振幅', '-')
    
    # Header Display
    st.divider()
    
    h1, h2 = st.columns([2, 3])
    with h1:
        color = "red" if float(chg_pct) > 0 else "green"
        st.markdown(f"## {name} ({symbol})")
        st.markdown(f"# ¥{price} <span style='color:{color}'>{chg_pct}%</span>", unsafe_allow_html=True)
        st.caption(f"五维诊断生成时间: {datetime.now().strftime('%H:%M:%S')}")
    
    with h2:
        # 5-Dim Snapshot
        c1, c2, c3 = st.columns(3)
        c1.metric("⚖️ 估值 (PE-TTM)", pe_ttm, f"PB: {pb}")
        c2.metric("📈 异动 (量比)", volume_ratio, f"换手: {turnover}%")
        c3.metric("🌊 波动 (振幅)", f"{amplitude}%")

    # --- Config Sidebar ---
    st.sidebar.header("⚙️ 诊断设置")
    timeframe = st.sidebar.radio("K线周期", ["日线 (Daily)", "5分钟 (Intraday)"])
    tech_indicators = st.sidebar.multiselect("叠加指标", ["MA (均线)", "RSI", "MACD", "BOLL"], default=["MA (均线)", "RSI"])

    # --- Fetching Deep Data ---
    with st.spinner("🔍 正在拉取 资金流向 & 深度财务..."):
        if timeframe == "日线 (Daily)":
            hist_df = get_daily_data(symbol)
        else:
            hist_df = get_intraday_data(symbol)
            
        fin_df = get_financials(symbol)
        holders_df = get_holders(symbol)
        flow_df = get_capital_flow(symbol)
        news_df = get_news(symbol)
        serper_news = get_serper_news(symbol, name)

    # --- 5-Dim Tabs ---
    tab_tc, tab_vf, tab_se, tab_ai = st.tabs(["📈 技术 & 资金 (Tech/Cap)", "🏢 基本面 & 估值 (Fund/Val)", "📰 情绪 & 概念 (Sent)", "🤖 AI 五维评分 (Report)"])
    
    # 1. Tech & Capital
    with tab_tc:
        st.subheader(f"📈 走势与主力资金 ({timeframe})")
        
        col_chart, col_flow = st.columns([3, 1])
        
        with col_chart:
            if not hist_df.empty:
                c_data = hist_df[['close']].copy()
                if "MA (均线)" in tech_indicators:
                    c_data['MA5'] = c_data['close'].rolling(5).mean()
                    c_data['MA20'] = c_data['close'].rolling(20).mean()
                if "BOLL" in tech_indicators:
                    r = c_data['close'].rolling(20)
                    c_data['UP'] = r.mean() + 2*r.std()
                    c_data['LOW'] = r.mean() - 2*r.std()
                st.line_chart(c_data)
                
                # RSI
                if "RSI" in tech_indicators:
                    st.caption("RSI (14)")
                    delta = hist_df['close'].diff()
                    up, down = delta.copy(), delta.copy()
                    up[up < 0] = 0
                    down[down > 0] = 0
                    rs = up.rolling(14).mean() / down.abs().rolling(14).mean()
                    rsi = 100 - 100 / (1 + rs)
                    st.line_chart(rsi)
            else:
                st.write("暂无行情数据")
        
        with col_flow:
            st.markdown("#### 💸 主力资金 (近5日)")
            if not flow_df.empty:
                # flow_df columns: 日期, 主力净流入-净额...
                # Rename for chart
                try:
                    f_chart = flow_df.head(5).copy() # usually sorted desc? check Akshare
                    # AKShare fund flow usually sorted by date asc or desc. assuming date is col '日期'
                    # Standardizing
                    if '日期' in f_chart.columns:
                        f_chart['date'] = pd.to_datetime(f_chart['日期'])
                        f_chart.set_index('date', inplace=True)
                    
                    if '主力净流入-净额' in f_chart.columns:
                        # Convert to 10k or M
                        # Data might be raw float/str
                        # Let's clean
                        def clean_float(x):
                            try: return float(x)
                            except: return 0.0
                        
                        f_chart['NetFlow'] = f_chart['主力净流入-净额'].apply(clean_float)
                        st.bar_chart(f_chart['NetFlow'])
                        
                        last_flow = f_chart.iloc[-1]['NetFlow']
                        color_f = "red" if last_flow > 0 else "green"
                        st.metric("最新主力净流入", f"{last_flow/10000:.2f}万", delta_color="inverse")
                except Exception as e:
                    st.error(f"资金数据解析错误: {e}")
            else:
                st.info("暂无主力资金数据")

    # 2. Fund & Valuation
    with tab_vf:
        st.subheader("🏢 公司基本面透视")
        # Key Ratios Row
        k1, k2, k3 = st.columns(3)
        k1.metric("总市值", f"{float(mkt_cap)/100000000:.2f}亿" if mkt_cap != '-' else '-')
        k2.metric("市盈率 TTM", pe_ttm)
        k3.metric("市净率 PB", pb)
        
        st.divider()
        
        kf1, kf2 = st.columns(2)
        with kf1:
            st.markdown("#### 💰 财务摘要 (Abstract)")
            if not fin_df.empty:
               st.dataframe(fin_df.head(5))
            else:
               st.write("无数据")
        
        with kf2:
            st.markdown("#### 👥 机构/大股东持仓")
            if not holders_df.empty:
                st.dataframe(holders_df.head(10))
            else:
                st.write("无数据")

    # 3. Sentiment
    with tab_se:
        st.subheader("📰 市场情绪 & 概念")
        
        # Two columns for news sources
        col_ak, col_serp = st.columns(2)
        
        with col_ak:
            st.markdown(f"#### 🏛️ 东方财富 (AKShare)")
            if not news_df.empty:
                for idx, row in news_df.head(10).iterrows():
                    title = row.get('新闻标题', '无标题')
                    date = row.get('发布时间', '-')
                    url = row.get('文章链接', '#')
                    st.markdown(f"- [{title}]({url}) ` {date} `")
            else:
                st.info("暂无 AKShare 舆情")

        with col_serp:
            st.markdown(f"#### 🌎 全网搜索 (Serper.dev)")
            if serper_news:
                for item in serper_news[:10]:
                    title = item.get('title', '无标题')
                    date = item.get('date', '-')
                    url = item.get('link', '#')
                    source = item.get('source', 'Unknown')
                    st.markdown(f"- [{title}]({url})")
                    st.caption(f"来源: {source} | 时间: {date}")
            else:
                st.info("暂无 Serper 搜索结果")

    # 4. AI 5-Dim Report
    with tab_ai:
        st.subheader("🤖 DeepSeek 五维雷达诊断")
        if st.button("🧠 生成五维深度研报"):
            with st.spinner("DeepSeek 正在进行五维综合评分..."):
                # Context
                dim_tech = f"Price: {price}, Chg: {chg_pct}%, Turnover: {turnover}%, VolRatio: {volume_ratio}, Amp: {amplitude}%"
                dim_cap = flow_df.head(5).to_markdown() if not flow_df.empty else "No Flow Data"
                dim_val = f"PE-TTM: {pe_ttm}, PB: {pb}, MktCap: {mkt_cap}"
                dim_fund = fin_df.head(3).to_markdown() if not fin_df.empty else "No Fund Data"
                dim_ak_news = news_df.head(3).to_markdown() if not news_df.empty else "No AKShare News"
                dim_serp_news = str(serper_news[:3]) if serper_news else "No Serper News"
                dim_sent = f"AKShare: {dim_ak_news}\nSerper: {dim_serp_news}"
                
                prompt = ChatPromptTemplate.from_template("""
                你是一位专业的A股基金经理。请基于以下【五维数据】对 {name} ({symbol}) 进行深度复盘，并给出评分（0-10分）。
                
                五维数据输入:
                1. ⚖️ [估值]: {val}
                2. 📈 [技术]: {tech}
                3. 💸 [资金]: {cap} (主力净流入 trend)
                4. 🏢 [基本面]: {fund} (财务 & 股东)
                5. 🔥 [情绪]: {sent} (舆情)
                
                请输出Markdown报告:
                ### 1. 五维评分雷达
                *   ⚖️ 估值: ?/10 (评语)
                *   📈 技术: ?/10 (评语)
                *   💸 资金: ?/10 (评语)
                *   🏢 基本面: ?/10 (评语)
                *   🔥 情绪: ?/10 (评语)
                
                ### 2. 核心逻辑推演
                (结合主力资金流向、技术形态和基本面，分析主力的意图)
                
                ### 3. 操作建议
                (给出明确的 短线/中线 建议: 买入/持有/减仓/观望)
                
                风格: 犀利、客观、机构视角。
                """)
                
                llm = ChatOpenAI(
                    model_name="deepseek-chat",
                    openai_api_key=deepseek_api_key,
                    openai_api_base="https://api.deepseek.com",
                    temperature=0.7
                )
                
                chain = prompt | llm
                resp = chain.invoke({
                    "name": name,
                    "symbol": symbol,
                    "val": dim_val,
                    "tech": dim_tech,
                    "cap": dim_cap,
                    "fund": dim_fund,
                    "sent": dim_sent
                })
                
                st.markdown(resp.content)
