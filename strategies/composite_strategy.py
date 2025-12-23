import backtrader as bt
from .basic_strategy import BaseStrategy

class CompositeStrategy(BaseStrategy):
    """
    Composite Strategy (DIY) - Multi-Signal Confluence
    - Allows combining MULTIPLE signals with AND logic.
    - All enabled signals must agree for entry.
    - Supports all 7 strategies: MA, MACD, Bollinger, RSI, Turtle, KDJ, Dual Thrust.
    """
    params = dict(
        # Signal Enables (Tuple of booleans, order: MA, MACD, Bollinger, RSI, Turtle, KDJ, DualThrust)
        # Default: Only KDJ is enabled
        use_ma=False,
        use_macd=False,
        use_bollinger=False,
        use_rsi=False,
        use_turtle=False,
        use_kdj=True,
        use_dual_thrust=False,
        
        # Filters
        use_trend_filter=True,
        trend_period=60,
        use_vol_filter=False,
        vol_period=20,
        
        # --- Individual Indicator Params (Defaults) ---
        # MA
        ma_fast=5, ma_slow=20, ma_stop_loss=0.05, ma_take_profit=0.15,
        # MACD
        macd_fast=12, macd_slow=26, macd_signal=9,
        # Bollinger
        boll_period=20, boll_dev=2.0,
        # RSI
        rsi_period=14, rsi_low=30, rsi_high=70,
        # Turtle
        turtle_in=20, turtle_out=10,
        # KDJ
        kdj_period=9,
        # Dual Thrust
        dt_period=5, dt_k1=0.5, dt_k2=0.5,
    )

    def __init__(self):
        super().__init__()
        
        # --- Filters ---
        if self.p.use_trend_filter:
            self.trend_sma = bt.ind.SMA(self.data.close, period=self.p.trend_period)
        if self.p.use_vol_filter:
            self.vol_sma = bt.ind.SMA(self.data.volume, period=self.p.vol_period)

        # --- All Signal Indicators (Always compute to avoid dynamic issues) ---
        
        # 1. MA
        self.sma_fast = bt.ind.SMA(period=self.p.ma_fast)
        self.sma_slow = bt.ind.SMA(period=self.p.ma_slow)
        self.ma_cross = bt.ind.CrossOver(self.sma_fast, self.sma_slow)
        self.ma_vol_sma = bt.ind.SMA(self.data.volume, period=20)
        
        # 2. MACD
        self.macd = bt.ind.MACD(self.data.close, 
                                period_me1=self.p.macd_fast, 
                                period_me2=self.p.macd_slow, 
                                period_signal=self.p.macd_signal)
        self.macd_cross = bt.ind.CrossOver(self.macd.macd, self.macd.signal)
        
        # 3. Bollinger
        self.boll = bt.ind.BollingerBands(self.data.close, period=self.p.boll_period, devfactor=self.p.boll_dev)
        
        # 4. RSI
        self.rsi = bt.ind.RSI(self.data.close, period=self.p.rsi_period)
        
        # 5. Turtle
        self.donchian_high = bt.ind.Highest(self.data.high(-1), period=self.p.turtle_in)
        self.donchian_low = bt.ind.Lowest(self.data.low(-1), period=self.p.turtle_out)
        
        # 6. KDJ
        self.stoch = bt.ind.Stochastic(self.data, period=self.p.kdj_period)
        self.k = self.stoch.percK
        self.d = self.stoch.percD
        self.j = 3.0 * self.k - 2.0 * self.d
        
        # 7. Dual Thrust
        self.dt_hh = bt.ind.Highest(self.data.high(-1), period=self.p.dt_period)
        self.dt_lc = bt.ind.Lowest(self.data.close(-1), period=self.p.dt_period)
        self.dt_hc = bt.ind.Highest(self.data.close(-1), period=self.p.dt_period)
        self.dt_ll = bt.ind.Lowest(self.data.low(-1), period=self.p.dt_period)


    def next(self):
        # ---------------------------
        # 1. Check Filters
        # ---------------------------
        can_trade = True
        if self.p.use_trend_filter:
            if self.data.close[0] < self.trend_sma[0]:
                can_trade = False
        if self.p.use_vol_filter:
            if self.data.volume[0] <= self.vol_sma[0]:
                can_trade = False

        # ---------------------------
        # 2. Collect Individual Signals (True if condition met)
        # ---------------------------
        signals = {}
        
        # MA: Cross + Volume > Avg
        signals['ma'] = (self.ma_cross > 0) and (self.data.volume[0] > self.ma_vol_sma[0])
        
        # MACD: Cross + MACD > 0
        signals['macd'] = (self.macd_cross > 0) and (self.macd.macd[0] > 0)
        
        # Bollinger: Close < Lower Band
        signals['bollinger'] = self.data.close[0] < self.boll.lines.bot[0]
        
        # RSI: RSI < low
        signals['rsi'] = self.rsi[0] < self.p.rsi_low
        
        # Turtle: Close > Donchian High
        signals['turtle'] = self.data.close[0] > self.donchian_high[0]
        
        # KDJ: J < 0 OR K crosses D from below
        kdj_j_buy = self.j[0] < 0
        kdj_cross_buy = (self.k[-1] < self.d[-1]) and (self.k[0] > self.d[0]) and (self.k[0] < 20)
        signals['kdj'] = kdj_j_buy or kdj_cross_buy
        
        # Dual Thrust
        range_1 = self.dt_hh[0] - self.dt_lc[0]
        range_2 = self.dt_hc[0] - self.dt_ll[0]
        dt_range = max(range_1, range_2)
        dt_buy_trigger = self.data.open[0] + self.p.dt_k1 * dt_range
        signals['dual_thrust'] = self.data.close[0] > dt_buy_trigger

        # ---------------------------
        # 3. AND Logic for Enabled Signals
        # ---------------------------
        enabled_signals = []
        if self.p.use_ma: enabled_signals.append(signals['ma'])
        if self.p.use_macd: enabled_signals.append(signals['macd'])
        if self.p.use_bollinger: enabled_signals.append(signals['bollinger'])
        if self.p.use_rsi: enabled_signals.append(signals['rsi'])
        if self.p.use_turtle: enabled_signals.append(signals['turtle'])
        if self.p.use_kdj: enabled_signals.append(signals['kdj'])
        if self.p.use_dual_thrust: enabled_signals.append(signals['dual_thrust'])
        
        # Entry: ALL enabled signals must be True
        entry_signal = len(enabled_signals) > 0 and all(enabled_signals)

        # Execute BUY
        if not self.position:
            if can_trade and entry_signal:
                self.log(f'BUY CREATE (Composite), %.2f' % self.data.close[0])
                self.order = self.buy()

        # ---------------------------
        # 4. Exit Logic (Simple: OR of any inverse condition)
        # ---------------------------
        else:
            exit_signals = []
            if self.p.use_ma:
                exit_signals.append(self.ma_cross < 0)
            if self.p.use_macd:
                exit_signals.append(self.macd_cross < 0)
            if self.p.use_bollinger:
                exit_signals.append(self.data.close[0] > self.boll.lines.top[0])
            if self.p.use_rsi:
                exit_signals.append(self.rsi[0] > self.p.rsi_high)
            if self.p.use_turtle:
                exit_signals.append(self.data.close[0] < self.donchian_low[0])
            if self.p.use_kdj:
                kdj_j_sell = self.j[0] > 100
                kdj_cross_sell = (self.k[-1] > self.d[-1]) and (self.k[0] < self.d[0]) and (self.k[0] > 80)
                exit_signals.append(kdj_j_sell or kdj_cross_sell)
            if self.p.use_dual_thrust:
                dt_sell_trigger = self.data.open[0] - self.p.dt_k2 * dt_range
                exit_signals.append(self.data.close[0] < dt_sell_trigger)
            
            # Exit if ANY enabled exit condition is met (OR logic)
            if any(exit_signals):
                self.log(f'SELL CREATE (Composite), %.2f' % self.data.close[0])
                self.order = self.close()
