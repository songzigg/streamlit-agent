import backtrader as bt
from .basic_strategy import BaseStrategy

class BollingerStrategy(BaseStrategy):
    """
    Bollinger Bands Strategy (Mean Reversion)
    - Buy: Price touches/closes below Lower Band (Oversold)
    - Close: Price touches/closes above Upper Band (Overbought)
    """
    params = dict(
        period=20,
        devfactor=2.0
    )

    def __init__(self):
        super().__init__()
        
        self.boll = bt.ind.BollingerBands(
            self.data.close,
            period=self.p.period,
            devfactor=self.p.devfactor
        )

    def next(self):
        if not self.position:
            # Buy if close is below lower band
            if self.data.close[0] < self.boll.lines.bot[0]:
                self.log('BUY CREATE (Boll), %.2f' % self.data.close[0])
                self.order = self.buy()
        
        else:
            # Sell if close is above upper band
            if self.data.close[0] > self.boll.lines.top[0]:
                self.log('SELL CREATE (Boll), %.2f' % self.data.close[0])
                self.order = self.close()
