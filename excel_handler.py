import openpyxl
from openpyxl.utils import column_index_from_string
import logging
from datetime import datetime
import os
import pandas as pd
from config_manager import config
import logger

logger_inst = logging.getLogger(__name__)

ASSET_MAPPING = config["ASSET_MAPPING"]

class ExcelHandler:
    """
    A class to safely handle opening, updating, and saving an Excel workbook.
    """

    def __init__(self, filename: str, sheet_name: str):
        """
        Initializes the ExcelHandler.

        Args:
            filename (str): The path to the Excel file.
            sheet_name (str): The name of the worksheet to modify.
        """
        self.filename = filename
        self.sheet_name = sheet_name
        self.workbook = None
        self.sheet = None

    def load_workbook(self) -> bool:
        """
        Loads the workbook and selects the target sheet.

        Returns:
            bool: True if successful, False otherwise.
        """
        try:
            # Load the workbook, keeping formulas and formatting intact
            self.workbook = openpyxl.load_workbook(self.filename)

            if self.sheet_name in self.workbook.sheetnames:
                self.sheet = self.workbook[self.sheet_name]
                logger_inst.info(
                    f"Successfully loaded sheet '{
                        self.sheet_name}' from {
                        self.filename}")
                return True
            else:
                logger_inst.error(
                    f"Sheet '{
                        self.sheet_name}' not found in {
                        self.filename}. Available sheets: {
                        self.workbook.sheetnames}")
                return False

        except FileNotFoundError:
            logger_inst.error(f"File not found: {self.filename}")
            return False
        except PermissionError:
            logger_inst.error(
                f"Permission denied: {
                    self.filename}. Is the file open in another program?")
            return False
        except Exception as e:
            logger_inst.error(f"Unexpected error loading {self.filename}: {e}")
            return False

    def update_asset(
            self,
            asset: str,
            current_price: float) -> bool:
        """
        Updates the date and price cells for a specific asset based on ASSET_MAPPING.

        Args:
            asset (str): The asset ticker (e.g., 'MSFT').
            current_price (float): The fetched current market price.

        Returns:
            bool: True if the update was successful, False otherwise.
        """
        if self.sheet is None:
            logger_inst.error(
                "Cannot update asset: Workbook or sheet is not loaded.")
            return False

        if asset not in ASSET_MAPPING:
            logger_inst.warning(
                f"Asset '{asset}' not found in ASSET_MAPPING configuration.")
            return False

        mapping = ASSET_MAPPING[asset]
        row = mapping['row']

        try:
            # Convert column letters to 1-based indexes for openpyxl
            date_col_idx = column_index_from_string(mapping['date_col'])
            price_col_idx = column_index_from_string(mapping['price_col'])

            # Get current date in YYYY-MM-DD format
            today_str = datetime.now().strftime('%Y-%m-%d')

            # Update the cells
            self.sheet.cell(row=row, column=date_col_idx).value = today_str
            self.sheet.cell(
                row=row, column=price_col_idx).value = current_price
            logger_inst.info(
                f"Updated {asset} in Excel: Date={today_str}, Price=${
                    current_price:.2f}")
            return True

        except Exception as e:
            logger_inst.error(f"Failed to update cells for {asset}: {e}")
            return False

    def append_new_position(self, trade_data: dict) -> bool:
        """
        Appends new trade data to the first completely empty row (based on empty Column A)
        in the current sheet.

        Args:
            trade_data (dict): The trade data with keys 'Platform', 'Ticker', 'OrderType', 'Direction', 'Volume', 'Price', 'Justification'.

        Returns:
            bool: True if successful, False otherwise.
        """
        if self.sheet is None:
            logger_inst.error(
                "Cannot append position: Workbook or sheet is not loaded.")
            return False

        try:
            # Find the first row where Column A is empty
            # Start from row 5 as per "Trejdy" sheet requirements.
            empty_row = 5
            while self.sheet.cell(row=empty_row, column=1).value is not None:
                empty_row += 1

            # Date format
            today_str = datetime.now().strftime('%Y-%m-%d')

            # Map columns according to requirements:
            # Column A = Date
            # Column B = Platform
            # Column C = Ticker
            # Column D = Order Type
            # Column E = Direction
            # Column F = Volume
            # Column G = Price
            # Column I = Justification

            self.sheet.cell(row=empty_row, column=1).value = today_str
            self.sheet.cell(row=empty_row, column=2).value = trade_data.get('Platform', '')
            self.sheet.cell(row=empty_row, column=3).value = trade_data.get('Ticker', '')
            self.sheet.cell(row=empty_row, column=4).value = trade_data.get('OrderType', '')
            self.sheet.cell(row=empty_row, column=5).value = trade_data.get('Direction', '')
            self.sheet.cell(row=empty_row, column=6).value = trade_data.get('Volume', '')
            self.sheet.cell(row=empty_row, column=7).value = trade_data.get('Price', '')
            self.sheet.cell(row=empty_row, column=9).value = trade_data.get('Justification', '')

            logger_inst.info(
                f"Appended new position at row {empty_row}: {trade_data}")
            return True

        except Exception as e:
            logger_inst.error(f"Failed to append new position: {e}")
            return False

    def save_workbook(self) -> bool:
        """
        Saves the workbook to the file.

        Returns:
            bool: True if successful, False otherwise.
        """
        if self.workbook is None:
            logger_inst.error("Cannot save: Workbook is not loaded.")
            return False

        try:
            self.workbook.save(self.filename)
            logger_inst.info(f"Successfully saved changes to {self.filename}")
            return True
        except PermissionError:
            logger_inst.error(
                f"Permission denied while saving {
                    self.filename}. Please close the file if it is open in Excel.")
            return False
        except Exception as e:
            logger_inst.error(f"Unexpected error saving {self.filename}: {e}")
            return False

    @staticmethod
    def get_dashboard_data(filename: str, sheet_name: str = "Pozycje otwarte") -> pd.DataFrame:
        """
        Reads the specified sheet and returns a clean pandas DataFrame for the dashboard.
        Skips completely empty rows and columns. Handles header rows based on sheet type.
        """
        try:
            skiprows = None
            header = 0

            if sheet_name in ["Pozycje otwarte", "Trejdy", "Strategia", "Refleksje"]:
                skiprows = 3
            elif sheet_name == "Salda":
                skiprows = 6
            elif sheet_name == "Info":
                header = None

            df = pd.read_excel(filename, sheet_name=sheet_name, skiprows=skiprows, header=header, dtype=str)

            # Drop completely empty rows and columns
            df.dropna(how='all', inplace=True)
            df.dropna(axis=1, how='all', inplace=True)

            # Replace NaNs with empty strings
            df.fillna("", inplace=True)

            return df
        except Exception as e:
            logger_inst.error(f"Error reading dashboard data for sheet '{sheet_name}': {e}")
            return pd.DataFrame()

    @staticmethod
    def export_reports(filename: str) -> bool:
        """
        Exports 'Pozycje otwarte' and 'Trejdy' sheets to CSV files in the exports/ directory.
        """
        export_dir = os.path.join(os.path.dirname(__file__), 'exports')
        os.makedirs(export_dir, exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        success = True

        try:
            # Export 'Pozycje otwarte'
            open_pos_sheet = config.get("EXCEL_SHEET_NAME_OPEN_POS", "Pozycje otwarte")
            df_open_pos = pd.read_excel(filename, sheet_name=open_pos_sheet)
            df_open_pos.dropna(how='all', inplace=True)
            open_pos_filename = os.path.join(export_dir, f'portfolio_snapshot_{timestamp}_{open_pos_sheet}.csv')
            df_open_pos.to_csv(open_pos_filename, index=False, encoding='utf-8')
            logger_inst.info(f"Successfully exported {open_pos_sheet} to {open_pos_filename}")
        except Exception as e:
            logger_inst.error(f"Failed to export {open_pos_sheet}: {e}")
            success = False

        try:
            # Export 'Trejdy'
            trades_sheet = config.get("EXCEL_SHEET_NAME_TRADES", "Trejdy")
            df_trades = pd.read_excel(filename, sheet_name=trades_sheet)
            df_trades.dropna(how='all', inplace=True)
            trades_filename = os.path.join(export_dir, f'portfolio_snapshot_{timestamp}_{trades_sheet}.csv')
            df_trades.to_csv(trades_filename, index=False, encoding='utf-8')
            logger_inst.info(f"Successfully exported {trades_sheet} to {trades_filename}")
        except Exception as e:
            logger_inst.error(f"Failed to export {trades_sheet}: {e}")
            success = False

        return success
