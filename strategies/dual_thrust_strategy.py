import backtrader as bt
from .basic_strategy import BaseStrategy

class DualThrustStrategy(BaseStrategy):
    """
    Dual Thrust Strategy
    - A famous range breakout strategy.
    - Logic:
       Range = Max(HH-LC, HC-LL) based on previous N days.
       Buy Trigger = Open + K1 * Range
       Sell Trigger = Open - K2 * Range
    """
    params = dict(
        period=5,   # N days to calculate range
        k1=0.5,     # Long trigger coefficient
        k2=0.5,     # Short trigger coefficient (used for verify exit in long-only)
    )

    def __init__(self):
        super().__init__()
        
        # Calculate N-day High, Low, Close
        # Note: We need previous N days data, so we use start=-1
        self.highest_high = bt.ind.Highest(self.data.high(-1), period=self.p.period)
        self.lowest_close = bt.ind.Lowest(self.data.close(-1), period=self.p.period)
        self.highest_close = bt.ind.Highest(self.data.close(-1), period=self.p.period)
        self.lowest_low = bt.ind.Lowest(self.data.low(-1), period=self.p.period)
    
    def next(self):
        # Calculate Range
        range_1 = self.highest_high[0] - self.lowest_close[0]
        range_2 = self.highest_close[0] - self.lowest_low[0]
        
        # Current Range
        current_range = max(range_1, range_2)
        
        # Buy/Sell Thresholds based on Today's Open
        buy_trigger = self.data.open[0] + self.p.k1 * current_range
        sell_trigger = self.data.open[0] - self.p.k2 * current_range
        
        # Entry Logic
        if not self.position:
            if self.data.close[0] > buy_trigger:
                self.log('BUY CREATE (Dual Thrust), %.2f' % self.data.close[0])
                self.order = self.buy()
        
        # Exit Logic
        # Dual Thrust is typically a reversal strategy (long/short), but here for A-share (Long Only)
        # We sell when price hits the "Short Trigger" level
        else:
            if self.data.close[0] < sell_trigger:
                self.log('SELL CREATE (Dual Thrust), %.2f' % self.data.close[0])
                self.order = self.close()
