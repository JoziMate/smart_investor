import os
import sys
import queue
import logging
import threading
import pandas as pd
import customtkinter as ctk
from tkinter import filedialog, ttk
from market_data import MarketDataManager
from excel_handler import ExcelHandler
from vision_parser import extract_trades_from_image
from config_manager import config, save_config
import logger  # Initializes the root logger with File and Stream handlers
import dotenv

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

        self.title("Gra Inwestycyjna - Portfolio Manager")
        self.geometry("900x700")

        # Layout configuration
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(4, weight=1) # The dashboard area
        self.grid_rowconfigure(5, weight=1) # The log area

        # 1. Header Frame (for title and settings button)
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, pady=(20, 10), sticky="ew")
        self.header_frame.grid_columnconfigure(0, weight=1)

        self.header_label = ctk.CTkLabel(
            self.header_frame, text="Gra Inwestycyjna - Portfolio Manager", font=ctk.CTkFont(size=24, weight="bold")
        )
        self.header_label.grid(row=0, column=0)

        # Settings Button
        self.settings_button = ctk.CTkButton(
            self.header_frame, text="⚙️ Ustawienia", command=self.open_settings_window, width=120
        )
        self.settings_button.grid(row=0, column=1, padx=20)

        # 2. Buttons Frame
        self.buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.buttons_frame.grid(row=1, column=0, pady=(10, 10))

        self.api_button = ctk.CTkButton(
            self.buttons_frame, text="Update Market Prices", command=self.update_portfolio_api
        )
        self.api_button.grid(row=0, column=0, padx=10)

        self.vision_button = ctk.CTkButton(
            self.buttons_frame, text="Upload Trade Screenshot", command=self.scan_screenshot_ai
        )
        self.vision_button.grid(row=0, column=1, padx=10)

        self.export_button = ctk.CTkButton(
            self.buttons_frame, text="Eksportuj Raport", command=self.export_reports
        )
        self.export_button.grid(row=0, column=2, padx=10)

        # 3. Dashboard Frame (Treeview)
        self.dashboard_frame = ctk.CTkFrame(self)
        self.dashboard_frame.grid(row=4, column=0, padx=20, pady=(10, 10), sticky="nsew")
        self.dashboard_frame.grid_columnconfigure(0, weight=1)
        self.dashboard_frame.grid_rowconfigure(1, weight=1)

        self.dashboard_header_frame = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        self.dashboard_header_frame.grid(row=0, column=0, sticky="ew", pady=(5, 5), padx=5)
        self.dashboard_header_frame.grid_columnconfigure(0, weight=1)

        self.dashboard_label = ctk.CTkLabel(
            self.dashboard_header_frame, text="Pozycje Otwarte - Dashboard", font=ctk.CTkFont(size=16, weight="bold")
        )
        self.dashboard_label.grid(row=0, column=0, sticky="w")

        self.refresh_button = ctk.CTkButton(
            self.dashboard_header_frame, text="Odśwież widok", command=self.load_dashboard_data, width=100
        )
        self.refresh_button.grid(row=0, column=1, sticky="e")

        self.setup_treeview()

        # 4. Console Log (Textbox)
        self.log_textbox = ctk.CTkTextbox(self, state="disabled", height=150)
        self.log_textbox.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="nsew")

        # Initial load of dashboard
        self.load_dashboard_data()

        # Setup Logging
        self.log_queue = queue.Queue()
        self.setup_logging()

        # Start polling the queue for log messages
        self.after(100, self.poll_log_queue)

    def setup_treeview(self):
        """
        Sets up the ttk.Treeview with a dark theme.
        """
        style = ttk.Style()
        style.theme_use("default")

        # Configure colors for dark theme
        bg_color = "#2b2b2b"
        fg_color = "#dce4ee"
        selected_bg = "#1f538d"

        style.configure("Treeview",
                        background=bg_color,
                        foreground=fg_color,
                        fieldbackground=bg_color,
                        rowheight=25,
                        borderwidth=0)

        style.map("Treeview",
                  background=[('selected', selected_bg)])

        style.configure("Treeview.Heading",
                        background="#3b3b3b",
                        foreground=fg_color,
                        font=('Arial', 10, 'bold'),
                        borderwidth=1)

        style.map("Treeview.Heading",
                  background=[('active', "#4b4b4b")])

        # Treeview Scrollbar
        self.tree_scroll = ttk.Scrollbar(self.dashboard_frame)
        self.tree_scroll.grid(row=1, column=1, sticky="ns")

        self.tree = ttk.Treeview(self.dashboard_frame, yscrollcommand=self.tree_scroll.set, selectmode="browse")
        self.tree.grid(row=1, column=0, sticky="nsew")
        self.tree_scroll.config(command=self.tree.yview)

    def load_dashboard_data(self):
        """
        Loads data from the Excel file and updates the Treeview.
        """
        try:
            df = ExcelHandler.get_dashboard_data(config["EXCEL_FILENAME"])

            # Clear existing data
            self.tree.delete(*self.tree.get_children())

            if df.empty:
                return

            # Setup columns based on dataframe
            columns = list(df.columns)
            self.tree["columns"] = columns
            self.tree["show"] = "headings"

            for col in columns:
                self.tree.heading(col, text=str(col))
                # Auto-adjust column width based on header length (approx)
                self.tree.column(col, width=max(100, len(str(col)) * 10), anchor="center")

            # Insert data rows
            for _, row in df.iterrows():
                values = ["" if pd.isna(v) else str(v) for v in row.tolist()]
                self.tree.insert("", "end", values=values)

        except Exception as e:
            logging.error(f"Failed to load dashboard data: {e}")

    def export_reports(self):
        """
        Exports 'Pozycje otwarte' and 'Trejdy' to CSV files.
        """
        self.export_button.configure(state="disabled")
        logging.info("--- Starting Export to CSV ---")

        def _run_export():
            success = ExcelHandler.export_reports(config["EXCEL_FILENAME"])
            if success:
                logging.info("--- Export Completed Successfully ---")
            else:
                logging.error("--- Export Failed ---")
            self.after(0, lambda: self.export_button.configure(state="normal"))

        thread = threading.Thread(target=_run_export, daemon=True)
        thread.start()

    def open_settings_window(self):
        """
        Opens a Toplevel window for Settings (API Key and ASSET_MAPPING).
        """
        if hasattr(self, "settings_window") and self.settings_window is not None and self.settings_window.winfo_exists():
            self.settings_window.focus()
            return

        self.settings_window = ctk.CTkToplevel(self)
        self.settings_window.title("Ustawienia")
        self.settings_window.geometry("500x500")

        # Bring to front
        self.settings_window.attributes("-topmost", True)
        self.after(100, lambda: self.settings_window.attributes("-topmost", False))

        # 1. API Key Section
        api_frame = ctk.CTkFrame(self.settings_window)
        api_frame.pack(fill="x", padx=20, pady=20)

        ctk.CTkLabel(api_frame, text="Gemini API Key:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 0))
        self.api_key_entry = ctk.CTkEntry(api_frame, show="*")
        self.api_key_entry.pack(fill="x", padx=10, pady=10)

        # Load current API Key
        current_api_key = os.getenv("GEMINI_API_KEY", "")
        if current_api_key:
            self.api_key_entry.insert(0, current_api_key)

        # 2. Add New Asset Mapping Section
        mapping_frame = ctk.CTkFrame(self.settings_window)
        mapping_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        ctk.CTkLabel(mapping_frame, text="Add/Update Asset Mapping:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10, 10))

        # Grid for mapping inputs
        input_grid = ctk.CTkFrame(mapping_frame, fg_color="transparent")
        input_grid.pack(fill="x", padx=10, pady=5)

        ctk.CTkLabel(input_grid, text="Ticker:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.ticker_entry = ctk.CTkEntry(input_grid, width=100)
        self.ticker_entry.grid(row=0, column=1, padx=5, pady=5)

        ctk.CTkLabel(input_grid, text="Row:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        self.row_entry = ctk.CTkEntry(input_grid, width=100)
        self.row_entry.grid(row=0, column=3, padx=5, pady=5)

        ctk.CTkLabel(input_grid, text="Date Col:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.date_col_entry = ctk.CTkEntry(input_grid, width=100)
        self.date_col_entry.grid(row=1, column=1, padx=5, pady=5)
        self.date_col_entry.insert(0, "A") # Default

        ctk.CTkLabel(input_grid, text="Price Col:").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.price_col_entry = ctk.CTkEntry(input_grid, width=100)
        self.price_col_entry.grid(row=1, column=3, padx=5, pady=5)
        self.price_col_entry.insert(0, "G") # Default

        # 3. Save Button
        save_btn = ctk.CTkButton(self.settings_window, text="Save & Apply", command=self.save_settings)
        save_btn.pack(pady=20)

    def save_settings(self):
        """
        Saves the API Key to .env and Asset Mapping to config.json.
        """
        # Save API Key
        new_api_key = self.api_key_entry.get().strip()
        if new_api_key:
            env_file = os.path.join(os.path.dirname(__file__), '.env')
            if not os.path.exists(env_file):
                open(env_file, 'w').close()
            dotenv.set_key(env_file, "GEMINI_API_KEY", new_api_key)
            os.environ["GEMINI_API_KEY"] = new_api_key
            logging.info("GEMINI_API_KEY updated successfully.")

        # Save Mapping
        ticker = self.ticker_entry.get().strip()
        row_str = self.row_entry.get().strip()
        date_col = self.date_col_entry.get().strip()
        price_col = self.price_col_entry.get().strip()

        if ticker and row_str and date_col and price_col:
            try:
                row = int(row_str)
                # Update local config dict
                if "ASSET_MAPPING" not in config:
                    config["ASSET_MAPPING"] = {}

                config["ASSET_MAPPING"][ticker] = {
                    "row": row,
                    "date_col": date_col,
                    "price_col": price_col
                }

                # Save to config.json
                save_config(config)
                logging.info(f"Asset mapping for {ticker} updated and saved.")

                # Clear mapping inputs
                self.ticker_entry.delete(0, 'end')
                self.row_entry.delete(0, 'end')
                self.date_col_entry.delete(0, 'end')
                self.date_col_entry.insert(0, "A")
                self.price_col_entry.delete(0, 'end')
                self.price_col_entry.insert(0, "G")

            except ValueError:
                logging.error("Row must be an integer.")

        self.settings_window.destroy()

    def setup_logging(self):
        """
        Configures logging and stdout to write to the queue.
        """
        # Configure custom logging handler
        queue_handler = QueueLoggingHandler(self.log_queue)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
        queue_handler.setFormatter(formatter)

        # Get the root logger and add our handler
        root_logger = logging.getLogger()
        root_logger.addHandler(queue_handler)
        # Root logger level is already configured in logger.py

        # Redirect stdout (optional now, since print is replaced, but keeps traceback routing)
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
        logging.info("--- Starting Market Prices Update ---")

        thread = threading.Thread(target=self._run_update_portfolio_api, daemon=True)
        thread.start()

    def _run_update_portfolio_api(self):
        """
        Background thread logic for updating portfolio via API.
        """
        try:
            excel = ExcelHandler(config["EXCEL_FILENAME"], config["EXCEL_SHEET_NAME_OPEN_POS"])

            if not excel.load_workbook():
                logging.critical("Could not load the Excel workbook. Please check file path and permissions.")
                return

            market_data = MarketDataManager()

            # Process All Assets dynamically
            assets_to_fetch = list(config.get("ASSET_MAPPING", {}).keys())
            prices = market_data.get_all_prices(assets_to_fetch)

            for ticker, price in prices.items():
                if price is not None:
                    excel.update_asset(ticker, price)
                else:
                    logging.error(f"Failed to fetch price for {ticker}, skipping update.")

            # Save workbook
            if excel.save_workbook():
                logging.info("--- Market Prices Update completed successfully ---")
            else:
                logging.error("--- Market Prices Update failed during save ---")
        except Exception as e:
            logging.error(f"An unexpected error occurred during Market Prices Update: {e}")
        finally:
            self.after(0, self._restore_buttons)
            self.after(0, self.load_dashboard_data)

    def scan_screenshot_ai(self):
        """
        Opens a file dialog to select an image, then triggers Vision parsing in a background thread.
        """
        file_path = filedialog.askopenfilename(
            title="Select Trade Screenshot",
            filetypes=[("Image files", "*.png *.jpg *.jpeg")]
        )

        if not file_path:
            return

        self.api_button.configure(state="disabled")
        self.vision_button.configure(state="disabled")
        logging.info(f"--- Starting AI analysis for file: {os.path.basename(file_path)} ---")

        thread = threading.Thread(target=self._run_scan_screenshot_ai, args=(file_path,), daemon=True)
        thread.start()

    def _run_scan_screenshot_ai(self, image_path):
        """
        Background thread logic for scanning screenshot via Gemini AI and appending trades.
        """
        try:
            excel = ExcelHandler(config["EXCEL_FILENAME"], config["EXCEL_SHEET_NAME_TRADES"])

            if not excel.load_workbook():
                logging.critical("Could not load the Excel workbook. Please check file path and permissions.")
                return

            trades = extract_trades_from_image(image_path)

            if trades:
                for trade in trades:
                    excel.append_new_position(trade)

                if excel.save_workbook():
                    logging.info("--- AI analysis and file save completed successfully ---")
                else:
                    logging.error("--- File save failed after AI analysis ---")
            else:
                logging.warning("Failed to extract trades from the image or an error occurred. Workbook not saved.")
        except Exception as e:
            logging.error(f"An unexpected error occurred during AI analysis: {e}")
        finally:
            self.after(0, self._restore_buttons)
            self.after(0, self.load_dashboard_data)

    def _restore_buttons(self):
        """
        Re-enables the buttons on the main thread after background tasks finish.
        """
        self.api_button.configure(state="normal")
        self.vision_button.configure(state="normal")


if __name__ == "__main__":
    app = SmartInwestorApp()
    app.mainloop()
