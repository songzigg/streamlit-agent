import backtrader as bt
import pandas as pd

class BacktestEngine:
    def __init__(self, initial_cash=100000.0, commission=0.001):
        self.initial_cash = initial_cash
        self.commission = commission

    def _configure_cerebro(self, cerebro, pos_size):
        cerebro.broker.setcash(self.initial_cash)
        cerebro.broker.setcommission(commission=self.commission)
        
        # Position Sizing
        # If pos_size is between 0 and 1, treat as percent
        # If pos_size > 1, treat as fixed stake (not implemented here for simplicity, forcing percent for now)
        if pos_size > 0:
            cerebro.addsizer(bt.sizers.PercentSizer, percents=pos_size*100)

    def run(self, strategy_class, data_df, pos_size=0.95, **kwargs):
        """
        Run a single backtest.
        """
        cerebro = bt.Cerebro()
        cerebro.addstrategy(strategy_class, **kwargs)
        
        # Add Data
        data = bt.feeds.PandasData(dataname=data_df)
        cerebro.adddata(data)
        
        # Set Broker
        # Set Broker & Sizer
        self._configure_cerebro(cerebro, pos_size)
        
        # Add Analyzers
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trade')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        
        results = cerebro.run()
        strat = results[0]
        
        return {
            'final_value': cerebro.broker.getvalue(),
            'strat': strat,
            'cerebro': cerebro,
            'equity_curve': self._get_equity_curve(strat)
        }

    def _get_equity_curve(self, strat):
        """Extract the equity curve (datetime, value) from the strategy."""
        try:
            # The default observer for value is usually at index 0 or named 'broker'
            # Let's try to find the Value observer
            # bt.observers.Broker contains cash and value
            
            # Helper to extract data from observer line
            equity_data = strat.observers.broker.lines.value.array
            
            # We need the datetimes corresponding to these values
            # Strategy datetime is an array of floats
            # We can reconstruct it from the data feed
            
            # Easier approach: TimeReturn analyzer usually gives returns, but for Value curve:
            # Let's iterate over the data feed's datetime and pick the observer's value
            
            dates = []
            values = []
            
            # The length of the strategy should match the number of processed bars
            for i in range(len(strat)):
                # Get date from the first data feed
                d = strat.datas[0].datetime.date(i)
                # value from broker observer
                v = strat.observers.broker.lines.value[i]
                dates.append(d)
                values.append(v)
            
            return pd.Series(data=values, index=dates)
        except Exception as e:
            # Fallback or empty if something goes wrong
            print(f"Error extracting equity curve: {e}")
            return pd.Series()

    def optimize(self, strategy_class, data_df, pos_size=0.95, **kwargs):
        """
        Run parameter optimization.
        kwargs should contains iterables for parameters to optimize.
        """
        cerebro = bt.Cerebro(optreturn=False) # We need full results for analysis
        cerebro.optstrategy(strategy_class, **kwargs)
        
        data = bt.feeds.PandasData(dataname=data_df)
        cerebro.adddata(data)
        
        self._configure_cerebro(cerebro, pos_size)
        
        # For optimization, we usually want simpler metrics to compare
        cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        
        opt_results = cerebro.run()
        
        final_results = []
        for run in opt_results:
            for strat in run:
                res = {
                    'params': strat.params.__dict__,
                    'final_value': strat.broker.getvalue(),
                    'sharpe': strat.analyzers.sharpe.get_analysis().get('sharperatio', 0),
                    'max_drawdown': strat.analyzers.drawdown.get_analysis().max.drawdown,
                    'total_return': strat.analyzers.returns.get_analysis().get('rtot', 0)
                }
                final_results.append(res)
        
        return pd.DataFrame(final_results)
