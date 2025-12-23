import backtrader as bt
from .basic_strategy import BaseStrategy

class TurtleStrategy(BaseStrategy):
    """
    Turtle Trading Strategy (Donchian Channel Breakout)
    - Entry: Long when price breaks above the highest high of the last N1 days.
    - Exit: Close when price falls below the lowest low of the last N2 days.
    """

    params = dict(
        entry_period=20,
        exit_period=10,
        trailing_stop_pct=0.0, # 0.0 = disabled
    )

    def __init__(self):
        super().__init__()
        
        # Upper channel for Entry (Highest High of last N1 days)
        # We check high(-1) to avoid look-ahead bias if using today's high
        self.donchian_high = bt.ind.Highest(self.data.high(-1), period=self.p.entry_period)
        
        # Lower channel for Exit (Lowest Low of last N2 days)
        self.donchian_low = bt.ind.Lowest(self.data.low(-1), period=self.p.exit_period)
        
        # Trailing stop state
        self.highest_since_entry = 0.0

    def next(self):
        # Entry Logic
        if not self.position:
            if self.data.close[0] > self.donchian_high[0]:
                self.log('BUY CREATE (Turtle Breakout), %.2f' % self.data.close[0])
                self.order = self.buy()
                self.highest_since_entry = self.data.close[0]
        
        # Exit Logic
        else:
            # Update Price High
            if self.data.close[0] > self.highest_since_entry:
                self.highest_since_entry = self.data.close[0]

            # 1. Normal Donchian Exit
            if self.data.close[0] < self.donchian_low[0]:
                self.log('SELL CREATE (Turtle Exit), %.2f' % self.data.close[0])
                self.order = self.close()
            
            # 2. Trailing Stop Exit (if enabled)
            elif self.p.trailing_stop_pct > 0:
                stop_price = self.highest_since_entry * (1.0 - self.p.trailing_stop_pct)
                if self.data.close[0] < stop_price:
                    self.log('SELL CREATE (Trailing Stop), %.2f' % self.data.close[0])
                    self.order = self.close()
