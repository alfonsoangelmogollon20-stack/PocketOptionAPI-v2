import time, math, asyncio, json, threading
from datetime import datetime
from pocketoptionapi.stable_api import PocketOption
import pocketoptionapi.global_value as global_value
import pandas_ta as ta
import numpy as np
import pandas as pd
import indicators as qtpylib

global_value.loglevel = 'INFO'

# Session configuration
start_counter = time.perf_counter()

### REAL SSID Format::
#ssid = """42["auth",{"session":"a:4:{s:10:\\"session_id\\";s:32:\\"aa11b2345c67d89e0f1g23456h78i9jk\\";s:10:\\"ip_address\\";s:11:\\"11.11.11.11\\";s:10:\\"user_agent\\";s:111:\\"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36\\";s:13:\\"last_activity\\";i:1234567890;}1234a5b678901cd2efghi34j5678kl90","isDemo":0,"uid":12345678,"platform":2}]"""
#demo = False

### DEMO SSID Format::
#ssid = """42["auth",{"session":"abcdefghijklm12nopqrstuvwx","isDemo":1,"uid":12345678,"platform":2}]"""
#demo = True

ssid = '42["auth",{"session":"gqep422ie95ar8uabq0q9nsdsf","isDemo":1,"uid":107695044,"platform":2,"isFastHistory":true,"isOptimized":true}]'
demo = True

min_payout = 80
period = 60
expiration = 60
api = PocketOption(ssid,demo)

# Connect to API
api.connect()


def get_payout():
    try:
        d = global_value.PayoutData
        d = json.loads(d)
        for pair in d:
            # |0| |  1  |  |  2  |  |  3  | |4 | 5 |6 | 7 | 8| 9| 10 |11| 12| 13        | 14   | | 15,                                                                                                                                                                                     |  16| 17| 18        |
            # [5, '#AAPL', 'Apple', 'stock', 2, 50, 60, 30, 3, 0, 170, 0, [], 1743724800, False, [{'time': 60}, {'time': 120}, {'time': 180}, {'time': 300}, {'time': 600}, {'time': 900}, {'time': 1800}, {'time': 2700}, {'time': 3600}, {'time': 7200}, {'time': 10800}, {'time': 14400}], -1, 60, 1743784500],
            if len(pair) == 19:
                global_value.logger('id: %s, name: %s, typ: %s, active: %s' % (str(pair[1]), str(pair[2]), str(pair[3]), str(pair[14])), "DEBUG")
                #if pair[14] == True and pair[5] >= min_payout and "_otc" not in pair[1] and pair[3] == "currency":         # Get all non OTC Currencies with min_payout
                if pair[14] == True and pair[5] >= min_payout and "_otc" in pair[1]:                                       # Get all OTC Markets with min_payout
                #if pair[14] == True and pair[3] == "cryptocurrency" and pair[5] >= min_payout and "_otc" not in pair[1]:   # Get all non OTC Cryptocurrencies
                #if pair[14] == True:                                                                                       # Get All that online
                    p = {}
                    p['id'] = pair[0]
                    p['payout'] = pair[5]
                    p['type'] = pair[3]
                    global_value.pairs[pair[1]] = p
        return True
    except:
        return False


def get_df():
    try:
        i = 0
        for pair in global_value.pairs:
            i += 1
            df = api.get_candles(pair, period)
            global_value.logger('%s (%s/%s)' % (str(pair), str(i), str(len(global_value.pairs))), "INFO")
            time.sleep(1)
        return True
    except:
        return False


def buy(amount, pair, action, expiration):
    global_value.logger('%s, %s, %s, %s' % (str(amount), str(pair), str(action), str(expiration)), "INFO")
    result = api.buy(amount=amount, active=pair, action=action, expirations=expiration)
    i = result[1]
    result = api.check_win(i)
    if result:
        global_value.logger(str(result), "INFO")


def buy2(amount, pair, action, expiration):
    global_value.logger('%s, %s, %s, %s' % (str(amount), str(pair), str(action), str(expiration)), "INFO")
    result = api.buy(amount=amount, active=pair, action=action, expirations=expiration)


def make_df(df0, history):
    df1 = pd.DataFrame(history).reset_index(drop=True)
    df1 = df1.sort_values(by='time').reset_index(drop=True)
    df1['time'] = pd.to_datetime(df1['time'], unit='s')
    df1.set_index('time', inplace=True)
    # df1.index = df1.index.floor('1s')

    df = df1['price'].resample(f'{period}s').ohlc()
    df.reset_index(inplace=True)
    df = df.loc[df['time'] < datetime.fromtimestamp(wait(False))]

    if df0 is not None:
        ts = datetime.timestamp(df.loc[0]['time'])
        for x in range(0, len(df0)):
            ts2 = datetime.timestamp(df0.loc[x]['time'])
            if ts2 < ts:
                df = df._append(df0.loc[x], ignore_index = True)
            else:
                break
        df = df.sort_values(by='time').reset_index(drop=True)
        df.set_index('time', inplace=True)
        df.reset_index(inplace=True)

    return df


def accelerator_oscillator(dataframe, fastPeriod=5, slowPeriod=34, smoothPeriod=5):
    ao = ta.SMA(dataframe["hl2"], timeperiod=fastPeriod) - ta.SMA(dataframe["hl2"], timeperiod=slowPeriod)
    ac = ta.SMA(ao, timeperiod=smoothPeriod)
    return ac


def DeMarker(dataframe, Period=14):
    dataframe['dem_high'] = dataframe['high'] - dataframe['high'].shift(1)
    dataframe['dem_low'] = dataframe['low'].shift(1) - dataframe['low']
    dataframe.loc[(dataframe['dem_high'] < 0), 'dem_high'] = 0
    dataframe.loc[(dataframe['dem_low'] < 0), 'dem_low'] = 0

    dem = ta.SMA(dataframe['dem_high'], Period) / (ta.SMA(dataframe['dem_high'], Period) + ta.SMA(dataframe['dem_low'], Period))
    return dem


def vortex_indicator(dataframe, Period=14):
    vm_plus = abs(dataframe['high'] - dataframe['low'].shift(1))
    vm_minus = abs(dataframe['low'] - dataframe['high'].shift(1))

    tr1 = dataframe['high'] - dataframe['low']
    tr2 = abs(dataframe['high'] - dataframe['close'].shift(1))
    tr3 = abs(dataframe['low'] - dataframe['close'].shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    sum_vm_plus = vm_plus.rolling(window=Period).sum()
    sum_vm_minus = vm_minus.rolling(window=Period).sum()
    sum_tr = tr.rolling(window=Period).sum()

    vi_plus = sum_vm_plus / sum_tr
    vi_minus = sum_vm_minus / sum_tr

    return vi_plus, vi_minus


def supertrend(df, multiplier, period):
    #df = dataframe.copy()

    df['TR'] = ta.TRANGE(df)
    df['ATR'] = ta.SMA(df['TR'], period)

    st = 'ST'
    stx = 'STX'

    # Compute basic upper and lower bands
    df['basic_ub'] = (df['high'] + df['low']) / 2 + multiplier * df['ATR']
    df['basic_lb'] = (df['high'] + df['low']) / 2 - multiplier * df['ATR']

    # Compute final upper and lower bands
    df['final_ub'] = 0.00
    df['final_lb'] = 0.00
    for i in range(period, len(df)):
        df['final_ub'].iat[i] = df['basic_ub'].iat[i] if df['basic_ub'].iat[i] < df['final_ub'].iat[i - 1] or df['close'].iat[i - 1] > df['final_ub'].iat[i - 1] else df['final_ub'].iat[i - 1]
        df['final_lb'].iat[i] = df['basic_lb'].iat[i] if df['basic_lb'].iat[i] > df['final_lb'].iat[i - 1] or df['close'].iat[i - 1] < df['final_lb'].iat[i - 1] else df['final_lb'].iat[i - 1]

    # Set the Supertrend value
    df[st] = 0.00
    for i in range(period, len(df)):
        df[st].iat[i] = df['final_ub'].iat[i] if df[st].iat[i - 1] == df['final_ub'].iat[i - 1] and df['close'].iat[i] <= df['final_ub'].iat[i] else \
                        df['final_lb'].iat[i] if df[st].iat[i - 1] == df['final_ub'].iat[i - 1] and df['close'].iat[i] >  df['final_ub'].iat[i] else \
                        df['final_lb'].iat[i] if df[st].iat[i - 1] == df['final_lb'].iat[i - 1] and df['close'].iat[i] >= df['final_lb'].iat[i] else \
                        df['final_ub'].iat[i] if df[st].iat[i - 1] == df['final_lb'].iat[i - 1] and df['close'].iat[i] <  df['final_lb'].iat[i] else 0.00
    # Mark the trend direction up/down
    df[stx] = np.where((df[st] > 0.00), np.where((df['close'] < df[st]), 'down',  'up'), np.NaN)

    # Remove basic and final bands from the columns
    df.drop(['basic_ub', 'basic_lb', 'final_ub', 'final_lb'], inplace=True, axis=1)

    df.fillna(0, inplace=True)

    return df


def strategie():
    for pair in global_value.pairs:
        if 'history' in global_value.pairs[pair]:
            history = []
            history.extend(global_value.pairs[pair]['history'])
            if 'dataframe' in global_value.pairs[pair]:
                df = make_df(global_value.pairs[pair]['dataframe'], history)
            else:
                df = make_df(None, history)

            # Strategy 9, period: 30
            heikinashi = qtpylib.heikinashi(df)
            df['open'] = heikinashi['open']
            df['close'] = heikinashi['close']
            df['high'] = heikinashi['high']
            df['low'] = heikinashi['low']
            df = supertrend(df, 1.3, 13)
            df['ma1'] = ta.EMA(df["close"], timeperiod=16)
            df['ma2'] = ta.EMA(df["close"], timeperiod=165)
            df['buy'], df['cross'] = 0, 0
            df.loc[(qtpylib.crossed_above(df['ST'], df['ma1'])), 'cross'] = 1
            df.loc[(qtpylib.crossed_below(df['ST'], df['ma1'])), 'cross'] = -1
            df.loc[(
                    (df['STX'] == "up") &
                    (df['ma1'] > df['ma2']) &
                    (df['cross'] == 1)
                ), 'buy'] = 1
            df.loc[(
                    (df['STX'] == "down") &
                    (df['ma1'] < df['ma2']) &
                    (df['cross'] == -1)
                ), 'buy'] = -1
            if df.loc[len(df)-1]['buy'] != 0:
                t = threading.Thread(target=buy2, args=(100, pair, "call" if df.loc[len(df)-1]['buy'] == 1 else "put", 60,))
                t.start()

            # Strategy 8, period: 15
            # df['ma1'] = ta.SMA(df["close"], timeperiod=7)
            # df['ma2'] = ta.SMA(df["close"], timeperiod=9)
            # df['ma3'] = ta.SMA(df["close"], timeperiod=14)
            # df['buy'], df['ma13c'], df['ma23c'] = 0, 0, 0
            # df.loc[(qtpylib.crossed_above(df['ma1'], df['ma3'])), 'ma13c'] = 1
            # df.loc[(qtpylib.crossed_below(df['ma1'], df['ma3'])), 'ma13c'] = -1
            # df.loc[(qtpylib.crossed_above(df['ma2'], df['ma3'])), 'ma23c'] = 1
            # df.loc[(qtpylib.crossed_below(df['ma2'], df['ma3'])), 'ma23c'] = -1
            # df.loc[(
            #         (df['ma23c'] == 1) &
            #         (
            #             (df['ma13c'] == 1) |
            #             (df['ma13c'].shift(1) == 1)
            #         )
            #     ), 'buy'] = 1
            # df.loc[(
            #         (df['ma23c'] == -1) &
            #         (
            #             (df['ma13c'] == -1) |
            #             (df['ma13c'].shift(1) == -1)
            #         )
            #     ), 'buy'] = -1
            # if df.loc[len(df)-1]['buy'] != 0:
            #     t = threading.Thread(target=buy2, args=(100, pair, "call" if df.loc[len(df)-1]['buy'] == 1 else "put", 60,))
            #     t.start()

            # Strategy 7, period: 60
            # df['exith'] = ta.WMA(2 * ta.WMA(df['high'], int(15 / 2)) - ta.WMA(df['high'], 15), round(math.sqrt(15)))
            # df['exitl'] = ta.WMA(2 * ta.WMA(df['low'], int(15 / 2)) - ta.WMA(df['low'], 15), round(math.sqrt(15)))
            # df['hlv3'], df['buy'] = 0, 0
            # df.loc[(df['close'] > df['exith']), 'hlv3'] = 1
            # df.loc[(df['close'] < df['exitl']), 'hlv3'] = -1
            # df.loc[((df['close'] < df['exith']) & (df['close'] > df['exitl'])), 'hlv3'] = df['hlv3'].shift(1)
            # df.loc[(df['hlv3'] < 0), 'sslexit'] = df['exith']
            # df.loc[(df['hlv3'] > 0), 'sslexit'] = df['exitl']
            # df.loc[(qtpylib.crossed_above(df['close'], df['sslexit'])), 'buy'] = -1
            # df.loc[(qtpylib.crossed_below(df['close'], df['sslexit'])), 'buy'] = 1
            # if df.loc[len(df)-1]['buy'] != 0:
            #     t = threading.Thread(target=buy2, args=(100, pair, "call" if df.loc[len(df)-1]['buy'] == 1 else "put", 60,))
            #     t.start()

            # # Strategy 6, period: 60
            # df['macd'], df['macdsignal'], df['macdhist'] = ta.MACD(df['close'], 10, 15, 5)
            # df['vip'], df['vim'] = vortex_indicator(df, 5)
            # df['vcross'], df['mcross'], df['buy'] = 0, 0, 0
            # df.loc[(qtpylib.crossed_above(df['macd'], df['macdsignal'])), 'mcross'] = 1
            # df.loc[(qtpylib.crossed_below(df['macd'], df['macdsignal'])), 'mcross'] = -1
            # df.loc[(qtpylib.crossed_above(df['vip'], df['vim'])), 'vcross'] = 1
            # df.loc[(qtpylib.crossed_above(df['vim'], df['vip'])), 'vcross'] = -1
            # df.loc[(
            #         (
            #             (df['mcross'] == 1) &
            #             (
            #                 (df['vcross'] == 1) |
            #                 (df['vcross'].shift(1) == 1)
            #             )
            #         ) |
            #         (
            #             (
            #                 (df['mcross'] == 1) |
            #                 (df['mcross'].shift(1) == 1)
            #             ) &
            #             (df['vcross'] == 1)
            #         )
            #     ), 'buy'] = 1
            # df.loc[(
            #         (
            #             (df['mcross'] == -1) &
            #             (
            #                 (df['vcross'] == -1) |
            #                 (df['vcross'].shift(1) == -1)
            #             )
            #         ) |
            #         (
            #             (
            #                 (df['mcross'] == -1) |
            #                 (df['mcross'].shift(1) == -1)
            #             ) &
            #             (df['vcross'] == -1)
            #         )
            #     ), 'buy'] = -1
            # if df.loc[len(df)-1]['buy'] != 0:
            #     t = threading.Thread(target=buy2, args=(100, pair, "call" if df.loc[len(df)-1]['buy'] == 1 else "put", 60,))
            #     t.start()

            # # Strategy 5, period: 120
            # heikinashi = qtpylib.heikinashi(df)
            # df['open'] = heikinashi['open']
            # df['close'] = heikinashi['close']
            # df['high'] = heikinashi['high']
            # df['low'] = heikinashi['low']
            # bollinger = qtpylib.bollinger_bands(qtpylib.typical_price(df), window=6, stds=1.3)
            # df['bb_low'] = bollinger['lower']
            # df['bb_mid'] = bollinger['mid']
            # df['bb_up'] = bollinger['upper']
            # df['macd'], df['macdsignal'], df['macdhist'] = ta.MACD(df['close'], 6, 19, 6)
            # df['macd_cross'], df['hist_cross'], df['buy'] = 0, 0, 0
            # df.loc[(
            #         (df['macd'].shift(1) < df['macdsignal'].shift(1)) &
            #         (df['macd'] > df['macdsignal'])
            #     ), 'macd_cross'] = 1
            # df.loc[(
            #         (df['macd'].shift(1) > df['macdsignal'].shift(1)) &
            #         (df['macd'] < df['macdsignal'])
            #     ), 'macd_cross'] = -1
            # df.loc[(
            #         (df['macdhist'].shift(1) < 0) &
            #         (df['macdhist'] > 0)
            #     ), 'hist_cross'] = 1
            # df.loc[(
            #         (df['macdhist'].shift(1) > 0) &
            #         (df['macdhist'] < 0)
            #     ), 'hist_cross'] = -1
            # df.loc[(
            #         (df['close'] > df['bb_up']) &
            #         (
            #             (df['macd_cross'] == 1) |
            #             (df['macd_cross'].shift(1) == 1) |
            #             (df['macd_cross'].shift(2) == 1)
            #         ) &
            #         (
            #             (df['hist_cross'] == 1) |
            #             (df['hist_cross'].shift(1) == 1) |
            #             (df['hist_cross'].shift(2) == 1)
            #         )
            #     ), 'buy'] = 1
            # df.loc[(
            #         (df['close'] < df['bb_low']) &
            #         (
            #             (df['macd_cross'] == -1) |
            #             (df['macd_cross'].shift(1) == -1) |
            #             (df['macd_cross'].shift(2) == -1)
            #         ) &
            #         (
            #             (df['hist_cross'] == -1) |
            #             (df['hist_cross'].shift(1) == -1) |
            #             (df['hist_cross'].shift(2) == -1)
            #         )
            #     ), 'buy'] = -1
            # if df.loc[len(df)-1]['buy'] != 0:
            #     t = threading.Thread(target=buy2, args=(100, pair, "call" if df.loc[len(df)-1]['buy'] == 1 else "put", 120,))
            #     t.start()

            # Strategy 4, period: 60
            # df['ma1'] = ta.SMA(df["close"], timeperiod=4)
            # df['ma2'] = ta.SMA(df["close"], timeperiod=45)
            # # df['ma1'] = ta.EMA(df["close"], timeperiod=8)
            # # df['ma2'] = ta.EMA(df["close"], timeperiod=21)
            # # df['willr'] = ta.WILLR(df, timeperiod=7)
            # df['buy'], df['ma_cross'] = 0, 0
            # df.loc[(qtpylib.crossed_above(df['ma1'], df['ma2'])), 'ma_cross'] = 1
            # df.loc[(qtpylib.crossed_below(df['ma1'], df['ma2'])), 'ma_cross'] = -1
            # df.loc[(
            #         (df['ma_cross'] == 1)
            #     ), 'buy'] = 1
            # df.loc[(
            #         (df['ma_cross'] == -1)
            #     ), 'buy'] = -1
            # if df.loc[len(df)-1]['buy'] != 0:
            #     t = threading.Thread(target=buy2, args=(100, pair, "call" if df.loc[len(df)-1]['buy'] == 1 else "put", 180,))
            #     t.start()

            # Strategy 3, period: 60
            # heikinashi = qtpylib.heikinashi(df)
            # df['ha_open'] = heikinashi['open']
            # df['ha_close'] = heikinashi['close']
            # df['ha_high'] = heikinashi['high']
            # df['ha_low'] = heikinashi['low']
            # df['ma1'] = ta.SMA(df["ha_close"], timeperiod=5)
            # df['ma2'] = ta.SMA(df["ha_close"], timeperiod=10)
            # df['macd'], df['macdsignal'], df['macdhist'] = ta.MACD(df['ha_close'], 8, 26, 9)
            # df['buy'], df['ma_cross'], df['macd_cross'] = 0, 0, 0
            # df.loc[(qtpylib.crossed_above(df['ma1'], df['ma2'])), 'ma_cross'] = 1
            # df.loc[(qtpylib.crossed_below(df['ma1'], df['ma2'])), 'ma_cross'] = -1
            # df.loc[(qtpylib.crossed_above(df['macd'], df['macdsignal'])), 'macd_cross'] = 1
            # df.loc[(qtpylib.crossed_below(df['macd'], df['macdsignal'])), 'macd_cross'] = -1
            # df.loc[(
            #         (
            #             (df['ma_cross'] == 1) &
            #             (
            #                 (df['macd_cross'] == 1) |
            #                 (df['macd_cross'].shift(1) == 1)
            #             ) &
            #             (df['macdhist'] > 0)
            #         ) |
            #         (
            #             (df['macd_cross'] == 1) &
            #             (
            #                 (df['ma_cross'] == 1) |
            #                 (df['ma_cross'].shift(1) == 1)
            #             ) &
            #             (df['macdhist'] > 0) &
            #             (df['macd'] < 0)
            #         )
            #     ), 'buy'] = 1
            # df.loc[(
            #         (
            #             (df['ma_cross'] == -1) &
            #             (
            #                 (df['macd_cross'] == -1) |
            #                 (df['macd_cross'].shift(1) == -1)
            #             ) &
            #             (df['macdhist'] < 0)
            #         ) |
            #         (
            #             (df['macd_cross'] == -1) &
            #             (
            #                 (df['ma_cross'] == -1) |
            #                 (df['ma_cross'].shift(1) == -1)
            #             ) &
            #             (df['macdhist'] < 0) &
            #             (df['macd'] > 0)
            #         )
