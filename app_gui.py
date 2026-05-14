import os
import sys
import queue
import logging
import threading
import customtkinter as ctk
from tkinter import filedialog
from market_data import MarketDataManager
from excel_handler import ExcelHandler
from vision_parser import extract_trades_from_image

# Constants
EXCEL_FILENAME = "Dziennik_inwestora.xlsx"
EXCEL_SHEET_NAME_OPEN_POS = "Pozycje otwarte"

# Set customtkinter appearance and theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class QueueLoggingHandler(logging.Handler):
    """
    A custom logging handler that pushes formatted log messages to a queue.
    """
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        try:
            msg = self.format(record)
            self.log_queue.put(msg)
        except Exception:
            self.handleError(record)


class StdoutRedirector:
    """
    A file-like object to redirect stdout to a queue.
    """
    def __init__(self, log_queue):
        self.log_queue = log_queue

    def write(self, message):
        if message.strip():  # Skip empty newlines
            self.log_queue.put(message.strip())

    def flush(self):
        pass


class SmartInwestorApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Smart Inwestor - Risk & Data Manager")
        self.geometry("600x500")

        # Layout configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # 1. Header
        self.header_label = ctk.CTkLabel(
            self, text="Smart Inwestor", font=ctk.CTkFont(size=24, weight="bold")
        )
        self.header_label.grid(row=0, column=0, pady=(20, 10))

        # 2. Button 1: Aktualizuj portfel z API
        self.api_button = ctk.CTkButton(
            self, text="Aktualizuj portfel z API", command=self.update_portfolio_api
        )
        self.api_button.grid(row=1, column=0, pady=(10, 10))

        # 3. Button 2: Skanuj zrzut ekranu - AI
        self.vision_button = ctk.CTkButton(
            self, text="Skanuj zrzut ekranu - AI", command=self.scan_screenshot_ai
        )
        self.vision_button.grid(row=2, column=0, pady=(10, 20))

        # 4. Console Log (Textbox)
        self.log_textbox = ctk.CTkTextbox(self, state="disabled")
        self.log_textbox.grid(row=3, column=0, padx=20, pady=(0, 20), sticky="nsew")

        # Setup Logging
        self.log_queue = queue.Queue()
        self.setup_logging()

        # Start polling the queue for log messages
        self.after(100, self.poll_log_queue)

    def setup_logging(self):
        """
        Configures logging and stdout to write to the queue.
        """
        # Configure custom logging handler
        queue_handler = QueueLoggingHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        queue_handler.setFormatter(formatter)

        # Get the root logger and add our handler
        root_logger = logging.getLogger()
        root_logger.addHandler(queue_handler)
        root_logger.setLevel(logging.INFO)

        # Redirect stdout
        sys.stdout = StdoutRedirector(self.log_queue)

    def poll_log_queue(self):
        """
        Polls the log queue every 100ms and updates the text box.
        """
        while not self.log_queue.empty():
            msg = self.log_queue.get_nowait()
            self.log_textbox.configure(state="normal")
            self.log_textbox.insert("end", msg + "\n")
            self.log_textbox.configure(state="disabled")
            self.log_textbox.yview("end")

        # Poll again after 100ms
        self.after(100, self.poll_log_queue)

    def update_portfolio_api(self):
        """
        Triggers the API update in a background thread.
        """
        self.api_button.configure(state="disabled")
        self.vision_button.configure(state="disabled")
        print("--- Rozpoczęto aktualizację portfela z API ---")

        thread = threading.Thread(target=self._run_update_portfolio_api, daemon=True)
        thread.start()

    def _run_update_portfolio_api(self):
        """
        Background thread logic for updating portfolio via API.
        """
        try:
            excel = ExcelHandler(EXCEL_FILENAME, EXCEL_SHEET_NAME_OPEN_POS)

            if not excel.load_workbook():
                logging.critical("Could not load the Excel workbook. Please check file path and permissions.")
                return

            market_data = MarketDataManager()

            # Process Stocks (yfinance)
            stocks_to_fetch = ['MSFT', 'GOOGL', 'TSLA']
            for ticker in stocks_to_fetch:
                price = market_data.get_stock_price(ticker)
                if price is not None:
                    excel.update_asset(ticker, price)
                else:
                    logging.error(f"Failed to fetch price for {ticker}, skipping update.")

            # Process Crypto (ccxt)
            crypto_symbol = 'BTC/USDT'
            btc_price = market_data.get_crypto_price(crypto_symbol)

            if btc_price is not None:
                excel.update_asset(crypto_symbol, btc_price)
            else:
                logging.error(f"Failed to fetch price for {crypto_symbol}, skipping update.")

            # Save workbook
            if excel.save_workbook():
                print("--- Aktualizacja API zakończona sukcesem ---")
            else:
                print("--- Aktualizacja API nie powiodła się podczas zapisu ---")
        except Exception as e:
            logging.error(f"Wystąpił nieoczekiwany błąd podczas aktualizacji API: {e}")
        finally:
            self.after(0, self._restore_buttons)

    def scan_screenshot_ai(self):
        """
        Opens a file dialog to select an image, then triggers Vision parsing in a background thread.
        """
        file_path = filedialog.askopenfilename(
            title="Wybierz zrzut ekranu",
            filetypes=[("Image files", "*.png *.jpg *.jpeg")]
        )

        if not file_path:
            return

        self.api_button.configure(state="disabled")
        self.vision_button.configure(state="disabled")
        print(f"--- Rozpoczęto analizę AI dla pliku: {os.path.basename(file_path)} ---")

        thread = threading.Thread(target=self._run_scan_screenshot_ai, args=(file_path,), daemon=True)
        thread.start()

    def _run_scan_screenshot_ai(self, image_path):
        """
        Background thread logic for scanning screenshot via Gemini AI and appending trades.
        """
        try:
            excel = ExcelHandler(EXCEL_FILENAME, EXCEL_SHEET_NAME_OPEN_POS)

            if not excel.load_workbook():
                logging.critical("Could not load the Excel workbook. Please check file path and permissions.")
                return

            trades = extract_trades_from_image(image_path)

            if trades:
                for trade in trades:
                    excel.append_new_position(trade)

                if excel.save_workbook():
                    print("--- Analiza AI i zapis do pliku zakończone sukcesem ---")
                else:
                    print("--- Zapis do pliku po analizie AI nie powiódł się ---")
            else:
                logging.warning("Nie udało się odczytać żadnych transakcji ze zdjęcia lub wystąpił błąd. Skoroszyt nie został zapisany.")
        except Exception as e:
            logging.error(f"Wystąpił nieoczekiwany błąd podczas analizy AI: {e}")
        finally:
            self.after(0, self._restore_buttons)

    def _restore_buttons(self):
        """
        Re-enables the buttons on the main thread after background tasks finish.
        """
        self.api_button.configure(state="normal")
        self.vision_button.configure(state="normal")


if __name__ == "__main__":
    app = SmartInwestorApp()
    app.mainloop()
