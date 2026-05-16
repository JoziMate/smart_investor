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
from ai_analyzer import generate_market_reflections
from config_manager import config, save_config
import logger  # Initializes the root logger with File and Stream handlers
import dotenv
from nbp_api import fetch_usd_pln_rate
from plyer import notification
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

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

        # Rate Label
        self.rate_label = ctk.CTkLabel(
            self.header_frame, text="Kurs USD/PLN (NBP): Trwa pobieranie...", font=ctk.CTkFont(size=14)
        )
        self.rate_label.grid(row=0, column=1, padx=(10, 20), sticky="e")

        # Auto-update Checkbox
        self.auto_update_var = ctk.BooleanVar(value=False)
        self.auto_update_checkbox = ctk.CTkCheckBox(
            self.header_frame, text="▶ Auto-update (15 min)", variable=self.auto_update_var, command=self.toggle_auto_update
        )
        self.auto_update_checkbox.grid(row=0, column=2, padx=(10, 20), sticky="e")

        # Settings Button
        self.settings_button = ctk.CTkButton(
            self.header_frame, text="⚙️ Ustawienia", command=self.open_settings_window, width=120
        )
        self.settings_button.grid(row=0, column=3, padx=20)

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

        self.secondary_buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.secondary_buttons_frame.grid(row=2, column=0, pady=(0, 10))

        self.saldo_button = ctk.CTkButton(
            self.secondary_buttons_frame, text="Aktualizuj Saldo", command=self.update_saldo
        )
        self.saldo_button.grid(row=0, column=0, padx=10)

        self.strategy_button = ctk.CTkButton(
            self.secondary_buttons_frame, text="Dodaj Strategię", command=self.open_strategy_modal
        )
        self.strategy_button.grid(row=0, column=1, padx=10)

        self.reflection_button = ctk.CTkButton(
            self.secondary_buttons_frame, text="Generuj Refleksje (AI)", command=self.generate_reflections
        )
        self.reflection_button.grid(row=0, column=2, padx=10)

        self.risk_calc_button = ctk.CTkButton(
            self.secondary_buttons_frame, text="🧮 Kalkulator Ryzyka", command=self.open_risk_calculator
        )
        self.risk_calc_button.grid(row=0, column=3, padx=10)

        # 3. Dashboard Frame (Treeview)
        self.dashboard_frame = ctk.CTkFrame(self)
        self.dashboard_frame.grid(row=4, column=0, padx=20, pady=(10, 10), sticky="nsew")
        self.dashboard_frame.grid_columnconfigure(0, weight=1)
        self.dashboard_frame.grid_rowconfigure(1, weight=1)

        self.dashboard_header_frame = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        self.dashboard_header_frame.grid(row=0, column=0, sticky="ew", pady=(5, 5), padx=5)
        self.dashboard_header_frame.grid_columnconfigure(0, weight=1)

        self.tab_view = ctk.CTkTabview(self.dashboard_header_frame, command=self.load_dashboard_data, height=40)
        self.tab_view._segmented_button.configure(font=ctk.CTkFont(size=16, weight="bold"))
        self.tab_view.grid(row=0, column=0, sticky="ew")

        self.tab_names = ["Info", "Strategia", "Salda", "Pozycje otwarte", "Trejdy", "Refleksje", "📈 Wykres"]
        for tab_name in self.tab_names:
            self.tab_view.add(tab_name)

        self.tab_view.set("Pozycje otwarte")

        self.refresh_button = ctk.CTkButton(
            self.dashboard_header_frame, text="Odśwież widok", command=self.load_dashboard_data, width=100
        )
        self.refresh_button.grid(row=0, column=1, sticky="e", padx=(10, 0))

        self.setup_treeview()

        # Frame for Matplotlib Chart (hidden by default)
        self.chart_frame = ctk.CTkFrame(self.dashboard_frame, fg_color="transparent")
        self.chart_frame.grid(row=1, column=0, sticky="nsew")
        self.chart_frame.grid_remove() # Hide initially

        # 4. Console Log (Textbox)
        self.log_textbox = ctk.CTkTextbox(self, state="disabled", height=150, font=ctk.CTkFont(size=13))
        self.log_textbox.grid(row=5, column=0, padx=20, pady=(0, 20), sticky="nsew")

        # Initial load of dashboard
        self.load_dashboard_data()

        # Setup Logging
        self.log_queue = queue.Queue()
        self.setup_logging()

        # Start polling the queue for log messages
        self.after(100, self.poll_log_queue)

        # Fetch NBP Rate
        self.usd_pln_rate = 4.00 # Default
        self.fetch_rate_bg()

    def fetch_rate_bg(self):
        """Fetches the NBP rate in the background to avoid freezing the GUI."""
        def _fetch():
            rate = fetch_usd_pln_rate()
            self.usd_pln_rate = rate
            self.after(0, lambda: self.rate_label.configure(text=f"Kurs USD/PLN (NBP): {rate:.2f}"))

        threading.Thread(target=_fetch, daemon=True).start()

    def toggle_auto_update(self):
        """Toggles the auto-update loop based on the checkbox state."""
        if self.auto_update_var.get():
            logging.info("Auto-update activated. Next update in 15 minutes.")
            self.auto_update_loop()
        else:
            logging.info("Auto-update deactivated.")
            if hasattr(self, '_auto_update_timer') and self._auto_update_timer is not None:
                self.after_cancel(self._auto_update_timer)
                self._auto_update_timer = None

    def auto_update_loop(self):
        """The loop that runs every 15 minutes if auto-update is active."""
        if self.auto_update_var.get():
            # Trigger the update process. We want portfolio prices AND saldo update.
            # We'll call update_portfolio_api and let it cascade to update_saldo if auto-update is active.
            logging.info("--- Running Auto-Update Cycle ---")
            self._run_auto_update_sequence()
            # Schedule next run in 15 minutes (900,000 ms)
            self._auto_update_timer = self.after(900000, self.auto_update_loop)

    def _run_auto_update_sequence(self):
        """Runs the portfolio update and then immediately the saldo update."""
        self.api_button.configure(state="disabled")
        self.vision_button.configure(state="disabled")
        self.saldo_button.configure(state="disabled")

        def _sequence():
            # 1. Update Market Prices
            self._run_update_portfolio_api(trigger_saldo_after=True)

        thread = threading.Thread(target=_sequence, daemon=True)
        thread.start()

    def setup_treeview(self):
        """
        Sets up the ttk.Treeview with a dark theme and custom typography.
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
                        font=('Arial', 13),
                        rowheight=30,
                        borderwidth=0)

        style.map("Treeview",
                  background=[('selected', selected_bg)])

        style.configure("Treeview.Heading",
                        background="#3b3b3b",
                        foreground=fg_color,
                        font=('Arial', 14, 'bold'),
                        borderwidth=1)

        style.map("Treeview.Heading",
                  background=[('active', "#4b4b4b")])

        # Treeview Scrollbars
        self.tree_scroll_y = ttk.Scrollbar(self.dashboard_frame, orient="vertical")
        self.tree_scroll_y.grid(row=1, column=1, sticky="ns")

        self.tree_scroll_x = ttk.Scrollbar(self.dashboard_frame, orient="horizontal")
        self.tree_scroll_x.grid(row=2, column=0, sticky="ew")

        self.tree = ttk.Treeview(
            self.dashboard_frame,
            yscrollcommand=self.tree_scroll_y.set,
            xscrollcommand=self.tree_scroll_x.set,
            selectmode="browse"
        )
        self.tree.grid(row=1, column=0, sticky="nsew")

        self.tree_scroll_y.config(command=self.tree.yview)
        self.tree_scroll_x.config(command=self.tree.xview)

    def update_saldo(self):
        """
        Triggers the saldo update in a background thread.
        """
        self.saldo_button.configure(state="disabled")
        logging.info("--- Starting Saldo Update ---")

        def _run_update_saldo():
            try:
                # Read open positions df
                df_open_pos = ExcelHandler.get_dashboard_data(config["EXCEL_FILENAME"], "Pozycje otwarte")
                if df_open_pos.empty:
                    logging.warning("No data found in 'Pozycje otwarte'.")
                    return

                excel = ExcelHandler(config["EXCEL_FILENAME"], "Salda")
                if not excel.load_workbook():
                    logging.error("Could not load the Excel workbook to update Salda.")
                    return

                if excel.update_saldo(df_open_pos, getattr(self, 'usd_pln_rate', 1.0)):
                    if excel.save_workbook():
                        logging.info("--- Saldo Update completed successfully ---")
                    else:
                        logging.error("--- Saldo Update failed during save ---")
                else:
                    logging.error("--- Saldo Update failed ---")
            except Exception as e:
                logging.error(f"Unexpected error during Saldo Update: {e}")
            finally:
                self.after(0, lambda: self.saldo_button.configure(state="normal"))
                self.after(0, self.load_dashboard_data)

        thread = threading.Thread(target=_run_update_saldo, daemon=True)
        thread.start()

    def open_strategy_modal(self):
        """
        Opens a modal window to add a new strategy.
        """
        if hasattr(self, "strategy_window") and self.strategy_window is not None and self.strategy_window.winfo_exists():
            self.strategy_window.focus()
            return

        self.strategy_window = ctk.CTkToplevel(self)
        self.strategy_window.title("Dodaj Strategię")
        self.strategy_window.geometry("500x600")

        # Bring to front
        self.strategy_window.attributes("-topmost", True)
        self.after(100, lambda: self.strategy_window.attributes("-topmost", False))

        frame = ctk.CTkFrame(self.strategy_window)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Wersja
        ctk.CTkLabel(frame, text="Wersja:").grid(row=0, column=0, sticky="w", pady=(10, 5))
        self.strat_wersja = ctk.CTkEntry(frame, width=300)
        self.strat_wersja.grid(row=0, column=1, pady=(10, 5), padx=(10, 0))

        # Klasa aktywów
        ctk.CTkLabel(frame, text="Klasa aktywów:").grid(row=1, column=0, sticky="w", pady=5)
        self.strat_klasa = ctk.CTkEntry(frame, width=300)
        self.strat_klasa.grid(row=1, column=1, pady=5, padx=(10, 0))

        # Horyzont
        ctk.CTkLabel(frame, text="Horyzont:").grid(row=2, column=0, sticky="w", pady=5)
        self.strat_horyzont = ctk.CTkEntry(frame, width=300)
        self.strat_horyzont.grid(row=2, column=1, pady=5, padx=(10, 0))

        # Kryteria wejścia/wyjścia
        ctk.CTkLabel(frame, text="Kryteria wejścia/wyjścia:").grid(row=3, column=0, sticky="nw", pady=5)
        self.strat_kryteria = ctk.CTkTextbox(frame, width=300, height=100)
        self.strat_kryteria.grid(row=3, column=1, pady=5, padx=(10, 0))

        # Zarządzanie ryzykiem
        ctk.CTkLabel(frame, text="Zarządzanie ryzykiem:").grid(row=4, column=0, sticky="nw", pady=5)
        self.strat_ryzyko = ctk.CTkTextbox(frame, width=300, height=100)
        self.strat_ryzyko.grid(row=4, column=1, pady=5, padx=(10, 0))

        # Save Button
        save_btn = ctk.CTkButton(frame, text="Zapisz", command=self.save_strategy)
        save_btn.grid(row=5, column=0, columnspan=2, pady=20)

    def save_strategy(self):
        """
        Saves the new strategy to the Excel file.
        """
        strategy_data = {
            "Wersja": self.strat_wersja.get().strip(),
            "Klasa aktywów": self.strat_klasa.get().strip(),
            "Horyzont": self.strat_horyzont.get().strip(),
            "Kryteria wejścia/wyjścia": self.strat_kryteria.get("1.0", "end-1c").strip(),
            "Zarządzanie ryzykiem": self.strat_ryzyko.get("1.0", "end-1c").strip()
        }

        self.strategy_window.destroy()

        def _run_save_strategy():
            try:
                excel = ExcelHandler(config["EXCEL_FILENAME"], "Strategia")
                if not excel.load_workbook():
                    logging.error("Could not load the Excel workbook to save Strategy.")
                    return

                if excel.append_strategy(strategy_data):
                    if excel.save_workbook():
                        logging.info("--- Strategy Saved successfully ---")
                    else:
                        logging.error("--- Strategy Save failed during save ---")
                else:
                    logging.error("--- Strategy Save failed ---")
            except Exception as e:
                logging.error(f"Unexpected error saving strategy: {e}")
            finally:
                self.after(0, self.load_dashboard_data)

        thread = threading.Thread(target=_run_save_strategy, daemon=True)
        thread.start()

    def generate_reflections(self):
        """
        Triggers the AI reflections generation in a background thread.
        """
        self.reflection_button.configure(state="disabled")
        logging.info("--- Starting AI Reflections Generation ---")

        def _run_generate_reflections():
            try:
                performance_data = ExcelHandler.get_open_positions_performance(config["EXCEL_FILENAME"])
                if not performance_data:
                    logging.warning("No performance data found for reflections.")
                    return

                reflection_json = generate_market_reflections(performance_data)

                if reflection_json:
                    excel = ExcelHandler(config["EXCEL_FILENAME"], "Refleksje")
                    if not excel.load_workbook():
                        logging.error("Could not load the Excel workbook to save Reflections.")
                        return

                    if excel.append_reflection(reflection_json):
                        if excel.save_workbook():
                            logging.info("--- AI Reflections Generated and Saved successfully ---")
                        else:
                            logging.error("--- AI Reflections Save failed during save ---")
                    else:
                        logging.error("--- AI Reflections Save failed ---")
                else:
                    logging.error("--- AI Reflections Generation returned empty ---")

            except Exception as e:
                logging.error(f"Unexpected error generating reflections: {e}")
            finally:
                self.after(0, lambda: self.reflection_button.configure(state="normal"))
                self.after(0, self.load_dashboard_data)

        thread = threading.Thread(target=_run_generate_reflections, daemon=True)
        thread.start()

    def load_dashboard_data(self):
        """
        Loads data from the Excel file based on the selected tab and updates the Treeview or Chart.
        """
        try:
            selected_tab = self.tab_view.get()

            if selected_tab == "📈 Wykres":
                self.tree.grid_remove()
                self.tree_scroll_y.grid_remove()
                self.tree_scroll_x.grid_remove()
                self.chart_frame.grid()
                self._render_chart()
            else:
                self.chart_frame.grid_remove()
                self.tree.grid()
                self.tree_scroll_y.grid()
                self.tree_scroll_x.grid()

                df = ExcelHandler.get_dashboard_data(config["EXCEL_FILENAME"], sheet_name=selected_tab)

                # Clear existing data
                self.tree.delete(*self.tree.get_children())

                if df.empty:
                    self.tree["columns"] = []
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

    def _render_chart(self):
        """
        Renders the Matplotlib chart in the chart frame.
        """
        # Clear existing widgets in chart_frame
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        # Prevent memory leaks with pyplot
        plt.close('all')

        try:
            df = ExcelHandler.get_dashboard_data(config["EXCEL_FILENAME"], sheet_name="Historia")

            if df.empty or "Date" not in df.columns or "Total_PLN" not in df.columns:
                label = ctk.CTkLabel(self.chart_frame, text="Brak danych do wyświetlenia wykresu. Zaktualizuj saldo.")
                label.pack(expand=True)
                return

            # Convert types for plotting
            df["Date"] = pd.to_datetime(df["Date"])
            df["Total_PLN"] = pd.to_numeric(df["Total_PLN"], errors='coerce')
            df.dropna(subset=["Total_PLN"], inplace=True)
            df.sort_values(by="Date", inplace=True)

            if df.empty:
                label = ctk.CTkLabel(self.chart_frame, text="Dane w arkuszu 'Historia' są niepoprawne.")
                label.pack(expand=True)
                return

            # Set dark background style
            plt.style.use('dark_background')

            fig, ax = plt.subplots(figsize=(8, 4), dpi=100)
            fig.patch.set_facecolor('#2b2b2b')
            ax.set_facecolor('#2b2b2b')

            ax.plot(df["Date"], df["Total_PLN"], marker='o', linestyle='-', color='#1f538d', linewidth=2)

            ax.set_title("Wartość Portfela w Czasie", fontsize=14, color="#dce4ee")
            ax.set_xlabel("Data", fontsize=12, color="#dce4ee")
            ax.set_ylabel("Total PLN", fontsize=12, color="#dce4ee")

            # Formatting axes
            ax.tick_params(axis='x', colors='#dce4ee', rotation=45)
            ax.tick_params(axis='y', colors='#dce4ee')
            ax.grid(True, linestyle='--', alpha=0.3, color='#dce4ee')
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            ax.spines['bottom'].set_color('#dce4ee')
            ax.spines['left'].set_color('#dce4ee')

            fig.tight_layout()

            # Embed in Tkinter
            canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

        except Exception as e:
            logging.error(f"Failed to render chart: {e}")
            label = ctk.CTkLabel(self.chart_frame, text="Błąd podczas ładowania wykresu.")
            label.pack(expand=True)

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

    def open_risk_calculator(self):
        """
        Opens a Toplevel window for the Institutional Risk Management Calculator.
        """
        if hasattr(self, "risk_calc_window") and self.risk_calc_window is not None and self.risk_calc_window.winfo_exists():
            self.risk_calc_window.focus()
            return

        self.risk_calc_window = ctk.CTkToplevel(self)
        self.risk_calc_window.title("Kalkulator Ryzyka")
        self.risk_calc_window.geometry("450x550")

        # Bring to front
        self.risk_calc_window.attributes("-topmost", True)
        self.after(100, lambda: self.risk_calc_window.attributes("-topmost", False))

        # Main frame
        frame = ctk.CTkFrame(self.risk_calc_window)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Inputs
        ctk.CTkLabel(frame, text="Instrument (Ticker):", font=ctk.CTkFont(weight="bold")).grid(row=0, column=0, sticky="w", pady=(10, 5), padx=5)
        ticker_entry = ctk.CTkEntry(frame, width=200)
        ticker_entry.grid(row=0, column=1, pady=(10, 5), padx=5)

        ctk.CTkLabel(frame, text="Wielkość kapitału:").grid(row=1, column=0, sticky="w", pady=5, padx=5)
        capital_entry = ctk.CTkEntry(frame, width=200)
        capital_entry.insert(0, "100000")
        capital_entry.grid(row=1, column=1, pady=5, padx=5)

        ctk.CTkLabel(frame, text="Maksymalne ryzyko %:").grid(row=2, column=0, sticky="w", pady=5, padx=5)
        risk_entry = ctk.CTkEntry(frame, width=200)
        risk_entry.insert(0, "2.0")
        risk_entry.grid(row=2, column=1, pady=5, padx=5)

        ctk.CTkLabel(frame, text="Cena wejścia:").grid(row=3, column=0, sticky="w", pady=5, padx=5)
        entry_price_entry = ctk.CTkEntry(frame, width=200)
        entry_price_entry.grid(row=3, column=1, pady=5, padx=5)

        ctk.CTkLabel(frame, text="Poziom Stop-Loss:").grid(row=4, column=0, sticky="w", pady=5, padx=5)
        sl_price_entry = ctk.CTkEntry(frame, width=200)
        sl_price_entry.grid(row=4, column=1, pady=5, padx=5)

        # Calculate Button
        calc_btn = ctk.CTkButton(frame, text="Oblicz Wolumen", command=lambda: self.calculate_risk(
            ticker_entry.get(),
            capital_entry.get(),
            risk_entry.get(),
            entry_price_entry.get(),
            sl_price_entry.get()
        ))
        calc_btn.grid(row=5, column=0, columnspan=2, pady=20)

        # Output Section
        output_frame = ctk.CTkFrame(frame, fg_color="transparent")
        output_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=10)

        self.calc_error_label = ctk.CTkLabel(output_frame, text="", text_color="red", font=ctk.CTkFont(weight="bold"))
        self.calc_error_label.pack(pady=5)

        self.calc_vol_label = ctk.CTkLabel(output_frame, text="Maksymalny Wolumen: --", font=ctk.CTkFont(size=14))
        self.calc_vol_label.pack(anchor="w", pady=2)

        self.calc_pos_val_label = ctk.CTkLabel(output_frame, text="Wartość Pozycji: --", font=ctk.CTkFont(size=14))
        self.calc_pos_val_label.pack(anchor="w", pady=2)

        self.calc_risk_amt_label = ctk.CTkLabel(output_frame, text="Kwota zaryzykowana: --", font=ctk.CTkFont(size=14))
        self.calc_risk_amt_label.pack(anchor="w", pady=2)

    def calculate_risk(self, ticker, capital_str, risk_str, entry_price_str, sl_price_str):
        # Reset error and outputs
        self.calc_error_label.configure(text="")
        self.calc_vol_label.configure(text="Maksymalny Wolumen: --")
        self.calc_pos_val_label.configure(text="Wartość Pozycji: --")
        self.calc_risk_amt_label.configure(text="Kwota zaryzykowana: --")

        try:
            capital = float(capital_str.replace(',', '.'))
            risk_pct = float(risk_str.replace(',', '.'))
            entry_price = float(entry_price_str.replace(',', '.'))
            sl_price = float(sl_price_str.replace(',', '.'))
        except ValueError:
            self.calc_error_label.configure(text="Błąd: Wprowadź poprawne wartości liczbowe.")
            return

        if entry_price == sl_price:
            self.calc_error_label.configure(text="Błąd: Cena wejścia i Stop-Loss nie mogą być równe!")
            return

        risk_amount = capital * (risk_pct / 100.0)
        risk_per_unit = abs(entry_price - sl_price)
        optimal_volume = risk_amount / risk_per_unit
        total_position_value = optimal_volume * entry_price

        # Format based on ticker
        if '/' in ticker:
            optimal_volume_formatted = f"{optimal_volume:.2f}"
        else:
            optimal_volume_formatted = f"{int(round(optimal_volume))}"

        self.calc_vol_label.configure(text=f"Maksymalny Wolumen: {optimal_volume_formatted}")
        self.calc_pos_val_label.configure(text=f"Wartość Pozycji: {total_position_value:.2f}")
        self.calc_risk_amt_label.configure(text=f"Kwota zaryzykowana: {risk_amount:.2f}")


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

    def _run_update_portfolio_api(self, trigger_saldo_after=False):
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
                try:
                    notification.notify(
                        title="Gra Inwestycyjna",
                        message="Market Prices Update completed successfully.",
                        app_name="Gra Inwestycyjna",
                        timeout=5
                    )
                except Exception as notif_e:
                    logging.warning(f"Could not show desktop notification: {notif_e}")
            else:
                logging.error("--- Market Prices Update failed during save ---")
        except Exception as e:
            logging.error(f"An unexpected error occurred during Market Prices Update: {e}")
        finally:
            self.after(0, self._restore_buttons)
            self.after(0, self.load_dashboard_data)
            if trigger_saldo_after:
                self.after(0, self.update_saldo)

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
