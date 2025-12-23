import backtrader as bt
from .basic_strategy import BaseStrategy

class AdvancedMaStrategy(BaseStrategy):
    """
    Advanced Moving Average Crossover Strategy with:
    1. Volume filter (Volume must be above average).
    2. Dynamic Stop Loss and Take Profit.
    3. RSI filter (optional).
    """
    params = dict(
        p_fast=5,
        p_slow=20,
        p_vol=20,
        stop_loss=0.05,    # 5% stop loss
        take_profit=0.15,   # 15% take profit
        rsi_period=14,
        rsi_low=30,
        rsi_high=70,
        use_rsi=False,
    )

    def __init__(self):
        super().__init__()
        
        # Add Technical Indicators
        self.sma_fast = bt.ind.SMA(period=self.p.p_fast)
        self.sma_slow = bt.ind.SMA(period=self.p.p_slow)
        self.crossover = bt.ind.CrossOver(self.sma_fast, self.sma_slow)
        
        # Volume Indicator
        self.sma_vol = bt.ind.SMA(self.data.volume, period=self.p.p_vol)
        
        # RSI Indicator
        if self.p.use_rsi:
            self.rsi = bt.ind.RSI(period=self.p.rsi_period)

    def next(self):
        # We are not in the market
        if not self.position:
            # Entry conditions
            condition_cross = self.crossover > 0
            condition_vol = self.data.volume[0] > self.sma_vol[0]
            condition_rsi = True
            if self.p.use_rsi:
                condition_rsi = self.rsi[0] > self.p.rsi_low
            
            if condition_cross and condition_vol and condition_rsi:
                self.log('BUY CREATE, %.2f' % self.data.close[0])
                self.order = self.buy()
        
        # We are in the market
        else:
            # Exit condition 1: Crossover Down
            if self.crossover < 0:
                self.log('SELL CREATE (Cross), %.2f' % self.data.close[0])
                self.order = self.close()
            
            # Exit condition 2: Stop Loss
            elif self.data.close[0] < self.buyprice * (1.0 - self.p.stop_loss):
                self.log('SELL CREATE (Stop Loss), %.2f' % self.data.close[0])
                self.order = self.close()
                
            # Exit condition 3: Take Profit
            elif self.data.close[0] > self.buyprice * (1.0 + self.p.take_profit):
                self.log('SELL CREATE (Take Profit), %.2f' % self.data.close[0])
                self.order = self.close()
