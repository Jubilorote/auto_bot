import ccxt
import pandas as pd
import time
from multiprocessing.pool import ThreadPool as Pool
import numpy as np

class PerpBybit():
    def __init__(self, apiKey=None, secret=None):
        bybit_auth_object = {
            "apiKey": apiKey,
            "secret": secret,
            'options': {
                'defaultType': 'swap',
            }
        }
        if bybit_auth_object['secret'] == None:
            self._auth = False
            self._session = ccxt.bybit()
        else:
            self._auth = True
            self._session = ccxt.bybit(bybit_auth_object)
        self.market = self._session.load_markets()

    def authentication_required(fn):
        """Annotation for methods that require auth."""
        def wrapped(self, *args, **kwargs): #!!!!!!!!!
            if not self._auth:
                # print("You must be authenticated to use this method", fn)
                raise Exception("You must be authenticated to use this method")
            else:
                return fn(self, *args, **kwargs)#!!!! *kwargs
        return wrapped

    def get_last_historical(self, symbol, timeframe, limit):
        result = pd.DataFrame(data=self._session.fetch_ohlcv(
            symbol, timeframe, None, limit=limit))
        result = result.rename(
            columns={0: 'timestamp', 1: 'open', 2: 'high', 3: 'low', 4: 'close', 5: 'volume'})
        result = result.set_index(result['timestamp'])
        result.index = pd.to_datetime(result.index, unit='ms')
        del result['timestamp']
        return result


    def get_more_last_historical_async(self, symbol, timeframe, limit):
        max_threads = 4
        pool_size = round(limit/100)  # your "parallelness"

        # define worker function before a Pool is instantiated
        full_result = []
        def worker(i):

            try:
                return self._session.fetch_ohlcv(
                symbol, timeframe, round(time.time() * 1000) - (i*1000*60*60), limit=100)
            except Exception as err:
                raise Exception("Error on last historical on " + symbol + ": " + str(err))

        pool = Pool(max_threads)

        full_result = pool.map(worker,range(limit, 0, -100))
        full_result = np.array(full_result).reshape(-1,6)
        result = pd.DataFrame(data=full_result)
        result = result.rename(
            columns={0: 'timestamp', 1: 'open', 2: 'high', 3: 'low', 4: 'close', 5: 'volume'})
        result = result.set_index(result['timestamp'])
        result.index = pd.to_datetime(result.index, unit='ms')
        del result['timestamp']
        return result.sort_index()

    @authentication_required
    def get_usdt_equity(self):
        try:
            usdt_equity = self._session.fetch_balance({'coin':'USDT' })["info"]['result']['list'][0]['equity']

        except BaseException as err:
            raise Exception("An error occured", err)
        try:
            return usdt_equity
        except:
            return 0

    @authentication_required
    def get_open_position(self,symbol=None):
        #print("ohoho",self._session.fetch_positions(symbol))
        try:
            positions = self._session.fetch_positions(symbol)
            #print('hello', positions)
            truePositions = []
            for position in positions:
                if float(position['contractSize']) > 0:
                    truePositions.append(position)
            return truePositions
        except BaseException as err:
            raise TypeError("An error occured in get_open_position", err)

    def convert_amount_to_precision(self, symbol, amount):
        return self._session.amount_to_precision(symbol, amount)

    @authentication_required
    def place_market_order(self, symbol, side, amount, reduce=False):
        try:
            return self._session.create_order(
                symbol,
                'market',
                side,
                self.convert_amount_to_precision(symbol, amount),
                None,
                params = {'reduce_only': reduce},
            )
        except BaseException as err:
            raise Exception(err)

    @authentication_required
    def place_market_stop_loss(self, symbol, side, amount, trigger_price, reduce=False):

        try:
            return self._session.create_order(
                symbol,
                'market',
                side,
                self.convert_amount_to_precision(symbol, amount),
                self.convert_price_to_precision(symbol, trigger_price),
                params = {
                    'stop_loss': self.convert_price_to_precision(symbol, trigger_price),  # your stop price
                    "triggerType": "market_price",
                    "reduce_only": reduce
                },
            )
        except BaseException as err:
            raise Exception(err)

    def convert_price_to_precision(self, symbol, price):
        return self._session.price_to_precision(symbol, price)
