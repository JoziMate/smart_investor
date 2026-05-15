import yfinance as yf
import ccxt
import logging
import logger

logger_inst = logging.getLogger(__name__)

class MarketDataManager:
    """
    A class to handle fetching market data for stocks and cryptocurrencies.
    """

    def __init__(self):
        # Initialize Binance exchange for public data (no API key required)
        # Using binanceus instead of binance because regular binance API might
        # block requests depending on region
        self.binance = ccxt.binanceus()

    def get_stock_price(self, ticker: str) -> float | None:
        """
        Fetches the current market price for a given stock ticker using yfinance.

        Args:
            ticker (str): The stock ticker symbol (e.g., 'MSFT').

        Returns:
            float | None: The current price if successful, None otherwise.
        """
        try:
            stock = yf.Ticker(ticker)
            # Fetch the most recent daily data
            todays_data = stock.history(period='1d')
            if not todays_data.empty:
                # Use the 'Close' price of the most recent day (which acts as
                # current price during trading hours)
                price = todays_data['Close'].iloc[0]
                return float(price)
            else:
                logger_inst.warning(f"No price data found for stock: {ticker}")
                return None
        except Exception as e:
            logger_inst.error(f"Error fetching stock price for {ticker}: {e}")
            return None

    def get_crypto_price(self, symbol: str) -> float | None:
        """
        Fetches the current market price for a given crypto pair using ccxt and Binance.

        Args:
            symbol (str): The crypto pair symbol (e.g., 'BTC/USDT').

        Returns:
            float | None: The current price if successful, None otherwise.
        """
        try:
            ticker = self.binance.fetch_ticker(symbol)
            if ticker and 'last' in ticker:
                return float(ticker['last'])
            else:
                logger_inst.warning(
                    f"No last price found in ticker data for {symbol}")
                return None
        except ccxt.NetworkError as e:
            logger_inst.error(
                f"Network error while fetching crypto price for {symbol}: {e}")
            return None
        except ccxt.ExchangeError as e:
            logger_inst.error(
                f"Exchange error while fetching crypto price for {symbol}: {e}")
            return None
        except Exception as e:
            logger_inst.error(
                f"Unexpected error fetching crypto price for {symbol}: {e}")
            return None
