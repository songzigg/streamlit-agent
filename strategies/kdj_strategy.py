import backtrader as bt
from .basic_strategy import BaseStrategy

class KdjStrategy(BaseStrategy):
    """
    KDJ Strategy (Stochastic Oscillator)
    - Short-term swing trading strategy popular in A-shares.
    - Buy: J line < 0 (Oversold) OR K crosses above D (Golden Cross) in oversold zone.
    - Sell: J line > 100 (Overbought) OR K crosses below D (Death Cross) in overbought zone.
    """
    params = dict(
        period=9,
        period_dfast=3,
        period_dslow=3,
    )

    def __init__(self):
        super().__init__()
        
        # Use Stochastic Oscillator which is similar to KDJ
        # percK = K, percD = D
        # We need to manually calculate J = 3*K - 2*D
        self.stoch = bt.ind.Stochastic(
            self.data,
            period=self.p.period,
            period_dfast=self.p.period_dfast,
            period_dslow=self.p.period_dslow
        )
        
        # Calculate J line
        self.k = self.stoch.percK
        self.d = self.stoch.percD
        self.j = 3.0 * self.k - 2.0 * self.d

    def next(self):
        # Entry Logic
        if not self.position:
            # Condition 1: J < 0 (Deep Oversold)
            cond_j_buy = self.j[0] < 0
            
            # Condition 2: Golden Cross (K > D) while K < 20
            cond_cross_buy = (self.k[-1] < self.d[-1]) and (self.k[0] > self.d[0]) and (self.k[0] < 20)
            
            if cond_j_buy or cond_cross_buy:
                self.log('BUY CREATE (KDJ), %.2f' % self.data.close[0])
                self.order = self.buy()
        
        # Exit Logic
        else:
            # Condition 1: J > 100 (Deep Overbought)
            cond_j_sell = self.j[0] > 100
            
            # Condition 2: Death Cross (K < D) while K > 80
            cond_cross_sell = (self.k[-1] > self.d[-1]) and (self.k[0] < self.d[0]) and (self.k[0] > 80)
            
            if cond_j_sell or cond_cross_sell:
                self.log('SELL CREATE (KDJ), %.2f' % self.data.close[0])
                self.order = self.close()
