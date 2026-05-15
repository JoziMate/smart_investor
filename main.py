import logging
import argparse
from market_data import MarketDataManager
from excel_handler import ExcelHandler
from vision_parser import extract_trades_from_image
from config_manager import config
import logger  # Configures the root logger

def main():
    """
    Main execution script:
    Depending on arguments, either parses an image for new trades or updates current prices.
    If no arguments are provided, it launches the graphical user interface.
    """
    parser = argparse.ArgumentParser(description="Portfolio Risk & Data Manager")
    parser.add_argument("--vision", type=str, help="Path to a screenshot for parsing new trades.")
    parser.add_argument("--update", action="store_true", help="Run standard market update in the terminal.")

    # If no arguments were passed, launch the GUI
    import sys
    if len(sys.argv) == 1:
        from app_gui import SmartInwestorApp
        app = SmartInwestorApp()
        app.mainloop()
        return

    args = parser.parse_args()

    logging.info("--- Starting Academic Investment Portfolio Update ---")

    filename = config["EXCEL_FILENAME"]

    if args.vision:
        # Vision Mode
        sheet_name = config["EXCEL_SHEET_NAME_TRADES"]
        excel = ExcelHandler(filename, sheet_name)

        if not excel.load_workbook():
            logging.critical(
                "Exiting: Could not load the Excel workbook. Please check file path and permissions.")
            return

        logging.info(f"Running in Vision Mode with image: {args.vision}")
        trades = extract_trades_from_image(args.vision)

        if trades:
            for trade in trades:
                excel.append_new_position(trade)

            if excel.save_workbook():
                logging.info("--- Vision parsing and update completed successfully ---")
            else:
                logging.error("--- Update failed during save ---")
        else:
            logging.warning("No trades were extracted or an error occurred. Workbook not saved.")

    elif args.update:
        # Standard Update Mode
        sheet_name = config["EXCEL_SHEET_NAME_OPEN_POS"]
        excel = ExcelHandler(filename, sheet_name)

        if not excel.load_workbook():
            logging.critical(
                "Exiting: Could not load the Excel workbook. Please check file path and permissions.")
            return

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
            logging.info("--- Update completed successfully ---")
        else:
            logging.error("--- Update failed during save ---")


if __name__ == "__main__":
    main()
