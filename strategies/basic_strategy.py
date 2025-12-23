import backtrader as bt

class BaseStrategy(bt.Strategy):
    """
    Base strategy class with common logging and notification utilities.
    """
    params = dict(
        verbose=False,
    )

    def __init__(self):
        super().__init__()
        self.order = None
        self.log_data = []
        self.trade_history = [] # For plotting markers: (datetime, price, type)

    def log(self, txt, dt=None):
        """ Logging function for this strategy """
        dt = dt or self.datas[0].datetime.date(0)
        msg = f"{dt.isoformat()}, {txt}"
        self.log_data.append(msg)
        if self.p.verbose:
            print(msg)

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        if order.status in [order.Completed]:
            dt = self.datas[0].datetime.datetime(0)
            if order.isbuy():
                self.log(
                    'BUY EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                    (order.executed.price,
                     order.executed.value,
                     order.executed.comm))
                self.buyprice = order.executed.price
                self.buycomm = order.executed.comm
                self.trade_history.append({'dt': dt, 'price': order.executed.price, 'type': 'buy'})
            else:  # Sell
                self.log('SELL EXECUTED, Price: %.2f, Cost: %.2f, Comm %.2f' %
                         (order.executed.price,
                          order.executed.value,
                          order.executed.comm))
                self.trade_history.append({'dt': dt, 'price': order.executed.price, 'type': 'sell'})

            self.bar_executed = len(self)

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            self.log('Order Canceled/Margin/Rejected')

        self.order = None

    def notify_trade(self, trade):
        if not trade.isclosed:
            return

        self.log('OPERATION PROFIT, GROSS %.2f, NET %.2f' %
                 (trade.pnl, trade.pnlcomm))
