import logging
import argparse
from market_data import MarketDataManager
from excel_handler import ExcelHandler
from vision_parser import extract_trades_from_image

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    """
    Main execution script:
    Depending on arguments, either parses an image for new trades or updates current prices.
    """
    parser = argparse.ArgumentParser(description="Portfolio Risk & Data Manager")
    parser.add_argument("--vision", type=str, help="Path to a screenshot for parsing new trades.")
    args = parser.parse_args()

    print("--- Starting Academic Investment Portfolio Update ---")

    filename = "Dziennik_inwestora.xlsx"
    sheet_name = "Pozycje otwarte"
    excel = ExcelHandler(filename, sheet_name)

    # 1. Load the workbook
    if not excel.load_workbook():
        logging.critical(
            "Exiting: Could not load the Excel workbook. Please check file path and permissions.")
        return

    if args.vision:
        # Vision Mode
        logging.info(f"Running in Vision Mode with image: {args.vision}")
        trades = extract_trades_from_image(args.vision)

        if trades:
            for trade in trades:
                excel.append_new_position(trade)

            if excel.save_workbook():
                print("--- Vision parsing and update completed successfully ---")
            else:
                print("--- Update failed during save ---")
        else:
            logging.warning("No trades were extracted or an error occurred. Workbook not saved.")

    else:
        # Standard Update Mode
        logging.info("Running in Standard Market Update Mode.")
        market_data = MarketDataManager()

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
