import pytest
from market_data import MarketDataManager

def test_get_stock_price_success(mocker):
    # Mock yf.Ticker to return a specific structure
    mock_ticker = mocker.Mock()

    # We need a proper mock for a pandas dataframe slice
    # 'todays_data['Close'].iloc[0]'
    import pandas as pd
    mock_history = pd.DataFrame({'Close': [150.5]})

    mock_ticker.history.return_value = mock_history

    mocker.patch('yfinance.Ticker', return_value=mock_ticker)

    manager = MarketDataManager()
    price = manager.get_stock_price('MSFT')

    assert price == 150.5
    mock_ticker.history.assert_called_once_with(period='1d')

def test_get_stock_price_failure(mocker):
    mock_ticker = mocker.Mock()
    mock_history = mocker.Mock()
    mock_history.empty = True
    mock_ticker.history.return_value = mock_history

    mocker.patch('yfinance.Ticker', return_value=mock_ticker)

    manager = MarketDataManager()
    price = manager.get_stock_price('MSFT')

    assert price is None

def test_get_crypto_price_success(mocker):
    manager = MarketDataManager()
    # Mock the binance exchange fetch_ticker
    mocker.patch.object(manager.binance, 'fetch_ticker', return_value={'last': 60000.0})

    price = manager.get_crypto_price('BTC/USDT')
    assert price == 60000.0
    manager.binance.fetch_ticker.assert_called_once_with('BTC/USDT')

def test_get_crypto_price_failure(mocker):
    import ccxt
    manager = MarketDataManager()
    mocker.patch.object(manager.binance, 'fetch_ticker', side_effect=ccxt.NetworkError("Network down"))

    price = manager.get_crypto_price('BTC/USDT')
    assert price is None
