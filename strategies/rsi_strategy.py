import backtrader as bt
from .basic_strategy import BaseStrategy

class RsiStrategy(BaseStrategy):
    """
    RSI Strategy (Mean Reversion)
    - Buy: RSI < Low Threshold (Oversold)
    - Close: RSI > High Threshold (Overbought)
    """
    params = dict(
        period=14,
        low=30,
        high=70
    )

    def __init__(self):
        super().__init__()
        
        self.rsi = bt.ind.RSI(
            self.data.close,
            period=self.p.period
        )

    def next(self):
        if not self.position:
            # Entry: Oversold
            if self.rsi[0] < self.p.low:
                self.log('BUY CREATE (RSI), %.2f' % self.data.close[0])
                self.order = self.buy()
        
        else:
            # Exit: Overbought
            if self.rsi[0] > self.p.high:
                self.log('SELL CREATE (RSI), %.2f' % self.data.close[0])
                self.order = self.close()
