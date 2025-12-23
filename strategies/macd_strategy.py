import backtrader as bt
from .basic_strategy import BaseStrategy

class MacdStrategy(BaseStrategy):
    """
    MACD Strategy
    - Buy: DIF crosses above DEA (Golden Cross) AND MACD Histogram > 0
    - Close: DIF crosses below DEA (Death Cross)
    """
    params = dict(
        p_fast=12,
        p_slow=26,
        p_signal=9
    )

    def __init__(self):
        super().__init__()
        
        self.macd = bt.ind.MACD(
            self.data.close,
            period_me1=self.p.p_fast,
            period_me2=self.p.p_slow,
            period_signal=self.p.p_signal
        )
        
        # CrossOver: macd.macd (DIF) vs macd.signal (DEA)
        self.crossover = bt.ind.CrossOver(self.macd.macd, self.macd.signal)

    def next(self):
        if not self.position:
            # Entry: Golden Cross
            if self.crossover > 0 and self.macd.macd[0] > 0:
                self.log('BUY CREATE (MACD), %.2f' % self.data.close[0])
                self.order = self.buy()
        
        else:
            # Exit: Death Cross
            if self.crossover < 0:
                self.log('SELL CREATE (MACD), %.2f' % self.data.close[0])
                self.order = self.close()
