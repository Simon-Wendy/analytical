import pandas as pd,numpy as np
import matplotlib.pyplot as plt
import datetime

from scipy import stats
from scipy.stats import t
import statsmodels.api as sm
from statsmodels.tsa.api import VAR
from statsmodels.tsa.stattools import adfuller,acf,pacf,grangercausalitytests
from statsmodels.tsa.seasonal import seasonal_decompose,STL
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.statespace.sarimax import SARIMAX
from statsmodels.tsa.vector_ar.vecm import coint_johansen,VECM
from statsmodels.tsa.holtwinters import ExponentialSmoothing
from statsmodels.stats.diagnostic import acorr_ljungbox
from statsmodels.graphics.tsaplots import plot_acf,plot_pacf
from statsmodels.stats.multitest import multipletests

from arch import arch_model

from sklearn.linear_model import Ridge,LinearRegression
from sklearn.ensemble import RandomForestRegressor ,IsolationForest
from sklearn.preprocessing import MinMaxScaler,StandardScaler
# 构建XGBoost模型
from sklearn.model_selection import train_test_split
import xgboost as xgb
from sklearn.metrics import mean_squared_error,mean_absolute_error

import pmdarima as pm

#深度学习
import torch
import torch.nn as nn

import warnings
warnings.filterwarnings('ignore')

# 定义LSTM模型
class LSTMModel(nn.Module):
    def __init__(self,input_size=1, hidden_size=64, num_layers=2,output_size=1):
        super(LSTMModel,self).__init__()
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first = True, dropout = 0.2)
        self.fc = nn.Linear(hidden_size, output_size)
    def forward(self,x):
        h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size)
        out,_ = self.lstm(x,(h0,c0))
        out = self.fc(out[:,-1,:])
        return out

class modelEnsembel:
    def __init__(self):
        self.FORECAST_DAYS = 5
        self.BACKTEST_SETPS = 100
        self.results = {}
        self.FORECAST_VALUE = {}
        self.USE_COLS = []
        self.L = 0

    def metrics(self,actual,predicted,name):
        print(f'评分模型{name}，真实值长度：{len(actual)}, 验证集长度：{len(predicted)}')
        mae = mean_absolute_error(actual,predicted)
        rmse = np.sqrt(mean_squared_error(actual,predicted))
        mape = np.mean(np.abs((actual - predicted) / actual) *100)
        self.results[name] = {'mae':mae,'rmse':rmse,'mape':mape}
        print(f'{name} > MAP: {mae:.2f}; RMSE: {rmse:.2f}; MAPE: {mape:.2f}% \n')

    def buildTrainTest(self,data):
        # 构建训练数据
        feature_cols = [c for c in data.columns if c not in ['close']]
        dfs = data.copy()
        dfs['target'] = dfs['close'].shift(-1)
        dfs.dropna(inplace=True)
        s = int(self.BACKTEST_SETPS)
        train = dfs.iloc[:-s]
        test = dfs.iloc[-s:]
        x_train = train[feature_cols]
        y_train = train['target']
        x_test = test[feature_cols]
        y_test = test['target']
        return x_train,y_train,x_test,y_test
    def xgbModel(self,x_train,y_train,x_test,y_test):
        print(f'开始时间：{datetime.datetime.now()};\n 开始训练 XGB model.....')
        xgb_model = xgb.XGBRegressor(
            n_estimators=500,
            max_depth=6,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42,
            n_jobs=-1
        )
        xgb_model.fit(x_train, y_train, eval_set=[(x_test, y_test)], verbose=False)
        pred_test_xgb = xgb_model.predict(x_test)

        self.metrics(y_test,pred_test_xgb,'xgb')
        self.FORECAST_VALUE['xgb'] = pred_test_xgb

    def ridgeModel(self,train, test,feature_cols):
        print(f'开始时间：{datetime.datetime.now()};\n 开始训练 ridge model.....')
        # Ridge回归
        scaler = StandardScaler()
        r_train = scaler.fit_transform(train[feature_cols])
        r_test = scaler.transform(test[feature_cols])
        y_train = train['target'].values
        y_test = test['target'].values

        ridge_model = Ridge(alpha=1.0)
        ridge_model.fit(r_train, y_train)

        pred_test_ridge = ridge_model.predict(r_test)
        self.metrics(y_test,pred_test_ridge,'ridge')
        self.FORECAST_VALUE['ridge'] = pred_test_ridge

    def arimaModel(self,data):
        print(f'开始时间：{datetime.datetime.now()};\n 开始训练 ARIMA model.....')
        train = data['close'][-500:-self.BACKTEST_SETPS]
        test = data['close'][-self.BACKTEST_SETPS:]

        auto_model = pm.auto_arima(
            train,
            seasonal=True,
            m=22,
            # 非季节性参数范围 (p, d, q)
            start_p=0, max_p=4,  # 根据ACF/PACF分析，AR阶数可能不高
            start_q=0, max_q=4,  # 搜索MA阶数0-3
            d=True,  # 让auto_arima自动检测最优差分阶数
            # 季节性参数范围 (P, D, Q)
            start_P=0, max_P=3,
            start_Q=0, max_Q=3,
            D=True,  # 让auto_arima自动检测季节差分阶数，强制季节差分
            # 其他控制
            stepwise=True,  # 开启，否则搜索会非常慢
            trace=False,  # 开启，观察搜索过程
            maxiter=50,  # 限制迭代次数
        )

        auto_pre, conf_int = auto_model.predict(n_periods=len(test), return_conf_int=True, alpha=0.05)
        self.metrics(test,auto_pre.values,'arima')
        self.FORECAST_VALUE['arima'] = auto_pre.values

    def varModel(self,data):
        print(f'开始时间：{datetime.datetime.now()};\n 开始训练 VAR model.....')

        use_cols = ['close', 'volume', 'rsi14', 'macd', 'boll_width_20', 'volatility_20']
        val_data = data[use_cols][:-self.BACKTEST_SETPS]
        val_data_diff = val_data.diff().dropna()
        var_model = VAR(val_data_diff)
        lag_order = var_model.select_order(maxlags=15)
        optimal_lag = lag_order.aic
        # var 预测（差分空间）
        var_result = var_model.fit(optimal_lag)
        forecast = var_result.forecast(val_data_diff.values[-optimal_lag:], steps=self.BACKTEST_SETPS)
        # 反差分还原
        last_close = val_data['close'].iloc[-1]
        var_forecast = []
        current_close = last_close
        for i in range(self.BACKTEST_SETPS):
            current_close += forecast[i, 0]
            var_forecast.append(current_close)
        # backtest_steps = self.BACKTEST_SETPS
        # train_diff = val_data_diff.iloc[:-backtest_steps]
        # train_model = VAR(train_diff)
        # train_fit = train_model.fit(optimal_lag)
        # backtest_fc_diff = train_fit.forecast(train_diff.values[-optimal_lag:], steps=backtest_steps)
        #
        # # 反差分还原
        # train_last_close = val_data['close'].iloc[-(backtest_steps + 1)]
        # backtest_pred = []
        # cc = train_last_close
        # for i in range(backtest_steps):
        #     cc += backtest_fc_diff[i, 0]
        #     backtest_pred.append(cc)

        actual_test = data['close'].iloc[-self.BACKTEST_SETPS:].values
        self.metrics(actual_test, var_forecast,'var')
        self.FORECAST_VALUE['var'] = np.array(var_forecast)

    def rfModel(self,x_train,y_train,x_test,y_test):
        print(f'开始时间：{datetime.datetime.now()};\n 开始训练 RANDOM FOREST model.....')

        # 随机森林模型
        rf_model = RandomForestRegressor(
            n_estimators=300,
            max_depth=12,
            min_samples_split=10,
            min_samples_leaf=5,
            random_state=42,
            n_jobs=-1
        )
        rf_model.fit(x_train, y_train)

        rf_pred_test = rf_model.predict(x_test)
        self.metrics(y_test,rf_pred_test,'rf')
        self.FORECAST_VALUE['rf'] = rf_pred_test

    def lstmModel(self,data):
        print(f'开始时间：{datetime.datetime.now()};\n 开始训练 LSTM model.....')

        device = torch.device('cpu')
        # 使用close价格
        close_price = data['close'].values.reshape(-1, 1)
        scaler = MinMaxScaler()
        scaled = scaler.fit_transform(close_price)
        # 构建序列
        seq_len = 30
        x, y = [], []
        for i in range(seq_len, len(scaled)):
            x.append(scaled[i - seq_len:i, 0])
            y.append(scaled[i, 0])
        x = np.array(x)
        y = np.array(y)
        split_idx = self.BACKTEST_SETPS  # int(len(data)*0.85)
        x_train = torch.FloatTensor(x[:-split_idx]).unsqueeze(-1).to(device)
        y_train = torch.FloatTensor(y[:-split_idx]).to(device)
        x_test = torch.FloatTensor(x[-split_idx:]).unsqueeze(-1).to(device)
        y_test = torch.FloatTensor(y[-split_idx:]).to(device)

        model = LSTMModel(input_size=1, hidden_size=64, num_layers=2).to(device)
        criterion = nn.MSELoss()
        optimizer = torch.optim.Adam(model.parameters(), lr=0.005)
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=0.5)
        epochs = 150
        best_loss = float('inf')
        for epoch in range(epochs):
            model.train()
            optimizer.zero_grad()
            outputs = model(x_train)
            loss = criterion(outputs.squeeze(), y_train)
            loss.backward()
            optimizer.step()
            model.eval()
            with torch.no_grad():
                test_outputs = model(x_test)
                test_loss = criterion(test_outputs.squeeze(), y_test)

            scheduler.step(test_loss)
            if test_loss.item() < best_loss:
                best_loss = test_loss.item()
                best_state = model.state_dict().copy()
        model.load_state_dict(best_state)
        # 评估
        model.eval()
        with torch.no_grad():
            pred_test = model(x_test).squeeze().cpu().numpy()
        pred_test_unscaled = scaler.inverse_transform(pred_test.reshape(-1, 1)).flatten()
        actual_test = scaler.inverse_transform(y_test.cpu().numpy().reshape(-1, 1)).flatten()
        # mae = mean_absolute_error(actual_test, pred_test_unscaled)
        # rmse = np.sqrt(mean_squared_error(actual_test, pred_test_unscaled))
        # mape = np.mean(np.abs((actual_test - pred_test_unscaled) / actual_test)) * 100
        # print(f'LSTM: MAE={mae:.2f}; RMSE={rmse:.2f}; MAPE={mape:.2f}%')
        self.metrics(actual_test,pred_test_unscaled,'lstm')
        self.FORECAST_VALUE['lstm'] = pred_test_unscaled
        # return pred_test_unscaled, {'mae': mae, 'rmse': rmse, 'mape': mape}
    # 反MAPE加权
    def weithshModel(self):
        weights = {}
        if self.results:
            total_inv_mape = sum(1 / m['mape'] for m in self.results.values())
            for name, metrics in self.results.items():
                weights[name] = (1 / metrics['mape']) / total_inv_mape

        return weights

    def plotForecast(self,actual):
        print('绘制预测值与真实值图形')
        dt = actual.index
        fig, ax = plt.subplots(figsize=(12, 6))
        for key,values in self.FORECAST_VALUE.items():
            ax.plot(dt, values, linewidth = 0.7,label=key)
        ax.plot(dt, actual,label = 'actual')
        ax.set_title('真实值与预测值趋势',fontsize = 20,fontweight = 'bold')
        ax.legend()
        plt.savefig(r'./image/1.png')
        plt.show()

    def go(self,data):
        cols = data.columns

        feature_cols = [c for c in cols if c not in ['close']]
        dfs = data.copy()
        dfs['target'] = dfs['close'].shift(-1)
        dfs.dropna(inplace=True)
        s = int(self.BACKTEST_SETPS)
        train = dfs.iloc[:-s]
        test = dfs.iloc[-s:]
        x_train = train[feature_cols]
        y_train = train['target']
        x_test = test[feature_cols]
        y_test = test['target']
        # ARIMA模型选取500条训练
        self.arimaModel(data)
        self.varModel(data)
        self.rfModel(x_train,y_train,x_test,y_test)
        self.xgbModel(x_train,y_train,x_test,y_test)
        self.ridgeModel(train,test,feature_cols)
        self.lstmModel(data)
        weights = self.weithshModel()
        print('='*50,'\n', weights)
        weights_value = 0
        print('='*100)

        if weights:
            print('开始加权集成最终值......')
            for key,value in weights.items():
                weights_value = weights_value + self.FORECAST_VALUE[key] * value

            self.FORECAST_VALUE['integration']= weights_value
            self.plotForecast(y_test)
        else:
            print('权重加权失败，没有权重信息.')


if __name__ == '__main__':
    pass