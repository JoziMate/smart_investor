import logging
from market_data import MarketDataManager
from excel_handler import ExcelHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    """
    Main execution script:
    1. Initializes market data and excel handler modules.
    2. Opens the Excel file.
    3. Fetches live prices for stocks and crypto.
    4. Updates the date and price columns and saves the Excel file.
    """
    print("--- Starting Academic Investment Portfolio Update ---")

    # Initialization
    market_data = MarketDataManager()

    filename = "Dziennik_inwestora.xlsx"
    sheet_name = "Pozycje otwarte"
    excel = ExcelHandler(filename, sheet_name)

    # 1. Load the workbook
    if not excel.load_workbook():
        logging.critical(
            "Exiting: Could not load the Excel workbook. Please check file path and permissions.")
        return

    # 2. Process Stocks (yfinance)
    stocks_to_fetch = ['MSFT', 'GOOGL', 'TSLA']
    for ticker in stocks_to_fetch:
        price = market_data.get_stock_price(ticker)
        if price is not None:
            # Update Excel
            excel.update_asset(ticker, price)
        else:
            logging.error(
                f"Failed to fetch price for {ticker}, skipping update.")

    # 3. Process Crypto (ccxt)
    crypto_symbol = 'BTC/USDT'
    btc_price = market_data.get_crypto_price(crypto_symbol)

    if btc_price is not None:
        # Update Excel
        excel.update_asset(crypto_symbol, btc_price)
    else:
        logging.error(
            f"Failed to fetch price for {crypto_symbol}, skipping update.")

    # 4. Save the workbook
    if excel.save_workbook():
        print("--- Update completed successfully ---")
    else:
        print("--- Update failed during save ---")


if __name__ == "__main__":
    main()
