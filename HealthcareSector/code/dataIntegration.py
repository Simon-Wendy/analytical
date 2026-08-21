import numpy as np,pandas as pd
import baostock as bs
from sklearn.ensemble import IsolationForest

class dataPipeline:
    def __init__(self):
        pass
    def loadData(self):
        start_date = "2020-01-01"
        end_date = "2026-7-31"
        print(f'读取时间周期：{start_date} - {end_date}')
        lg = bs.login()
        rs = bs.query_history_k_data_plus("sz.399440",  # 上海市场需加 sh. 前缀
                                          "date,open,high,low,close,volume",
                                          start_date=start_date,
                                          end_date=end_date)
        data = pd.DataFrame(rs.data, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
        bs.logout()
        print(f'数据读取结束，读取总长度 {len(data)} 条.')
        return data
    def featureExtraction(self,data):
        print('开始构建特征')
        data['date'] = pd.to_datetime(data['date'])

        data = data.set_index('date')
        data = data.sort_index()

        # 转换成数值
        col = ['open', 'high', 'low', 'close', 'volume']
        for c in col:
            data[c] = pd.to_numeric(data[c])


        # 构建基础特征
        data['returns'] = data['close'].pct_change()
        data['log_returns'] = np.log(data['close'] / data['close'].shift(1))
        data['amplitude'] = (data['high'] - data['low']) / data['close'].shift(1)
        data['close_change'] = data['close'] - data['close'].shift(1)
        data['close_pct'] = data['close'].pct_change()

        # 移动平均线
        for w in [5, 10, 20, 60, 120]:
            data[f'ma{w}'] = data['close'].rolling(w).mean()
            data[f'ma{w}_diff'] = data['close'] - data[f'ma{w}']

        # MA金叉死叉信号
        data['ma5_ma20_cross'] = np.where(data['ma5'] > data['ma20'], 1, -1)
        data['ma10_ma60_cross'] = np.where(data['ma10'] > data['ma60'], 1, -1)

        # 指数移动平均
        for w in [5, 12, 26]:
            data[f'ema{w}'] = data['close'].ewm(span=w, adjust=False).mean()

        # MACD
        data['dif'] = data['ema12'] - data['ema26']
        data['dea'] = data['dif'].ewm(span=9, adjust=False).mean()
        data['macd'] = 2 * (data['dea'] - data['dif'])

        # RSI
        for period in [6, 14, 24]:
            delta = data['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
            rs = gain / (loss + 1e-10)
            data[f'rsi{period}'] = 100 - (100 / (1 + rs))

        # 布林带
        for w in [20]:
            mid = data['close'].rolling(w).mean()
            std = data['close'].rolling(w).std()
            data[f'boll_upper_{w}'] = mid + 2 * std
            data[f'boll_lower_{w}'] = mid - 2 * std
            data[f'boll_width_{w}'] = (data[f'boll_upper_{w}'] - data[f'boll_lower_{w}']) / mid
            data[f'boll_pos_{w}'] = (data['close'] - data[f'boll_lower_{w}']) / (
                        data[f'boll_upper_{w}'] - data[f'boll_lower_{w}'] + 1e-10)

        # ATR 平均真实波动幅度
        tr = pd.DataFrame(
            {'hl': data['high'] - data['low'], 'hc': abs(data['high'] - data['close'].shift(1)),
             'lc': abs(data['low'] - data['close'].shift(1))}
        ).max(axis=1)
        data['atr14'] = tr.rolling(14).mean()
        data['art14_pct'] = data['atr14'] / data['close']

        # 成交量特征
        data['vol_ma5'] = data['volume'].rolling(5).mean()
        data['vol_ma20'] = data['volume'].rolling(20).mean()
        data['vol_ratio'] = data['volume'] / (data['vol_ma5'] + 1e-10)
        data['vol_change'] = data['volume'].pct_change()
        data['obv'] = (np.sign(data['close'].diff()) * data['volume']).fillna(0).cumsum()

        # 动量特征
        for w in [5, 10, 20]:
            data[f'momentum_{w}'] = data['close'] / data['close'].shift(w) - 1

        # 波动率
        for w in [5, 20, 60]:
            data[f'volatility_{w}'] = data['returns'].rolling(w).std()

        # 滞后特征
        for w in [1, 2, 3, 5, 10, 20]:
            data[f'close_lag{w}'] = data['close'].shift(w)
            data[f'returns_lag{w}'] = data['returns'].shift(w)

        # 价格形态
        data['upper_shadow'] = data['high'] - data[['open', 'close']].max(axis=1)
        data['lower_shadow'] = data[['open', 'close']].min(axis=1) - data['low']
        data['body'] = abs(data['close'] - data['open'])
        data['body_pct'] = (data['close'] - data['open']) / data['open']
        data.dropna(inplace=True)

        # 孤立森林 对单变量使用，需 reshape
        isolate = data['volume'].values.reshape(-1, 1)
        iso_clf = IsolationForest(contamination=0.05)  # 预期异常比例
        preds = iso_clf.fit_predict(isolate)  # 1正常，-1异常
        data['anomaly'] = preds

        # 构建日期特征
        data['day'] = data.index.day
        data['month'] = data.index.month
        data['week'] = data.index.isocalendar().week

        return data
    def getData(self):
        data = self.loadData()
        data = self.featureExtraction(data)
        m,n = data.shape
        print(f'剩余数据总长度：{m}, 构建特征数量: {n}')
        return data

if __name__ == '__main__':
    pipeline = dataPipeline()
    pipeline.getData()