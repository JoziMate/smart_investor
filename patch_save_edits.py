import re
with open('excel_handler.py', 'r') as f:
    content = f.read()

old_save_sheet_edits = """    def save_sheet_edits(self, data: list) -> bool:
        \"\"\"
        Saves changes directly to the currently loaded sheet based on the grid data.

        Args:
            data (list): A list of rows, where each row is a list of string values.
                         Assumes the column count matches the data exactly.
        \"\"\"
        if self.sheet is None:
            logger_inst.error("Cannot save edits: Workbook or sheet is not loaded.")
            return False

        try:
            # Determine start row and skip empty header space based on sheet type
            start_row = 1
            if self.sheet_name in ["Pozycje otwarte", "Trejdy", "Strategia", "Refleksje"]:
                start_row = 5
            elif self.sheet_name == "Salda":
                start_row = 8

            # Clear existing data rows starting from start_row downwards.
            # We determine max row based on actual sheet dimension, and max column.
            max_row = self.sheet.max_row
            max_col = self.sheet.max_column

            for row in range(start_row, max_row + 1):
                for col in range(1, max_col + 1):
                    self.sheet.cell(row=row, column=col).value = None

            # Insert new data
            for r_idx, row_data in enumerate(data):
                # Excel rows are 1-indexed, starting from start_row
                current_row = start_row + r_idx
                for c_idx, val in enumerate(row_data):
                    # Attempt to parse back to numbers if appropriate to avoid converting entire sheet to strings,
                    # but since the UI edits might be strings, we insert as strings or floats if possible.
                    # As a safe default, write what's given. Let's try converting to float where possible for numerical data consistency.
                    value_to_write = val
                    if value_to_write == "":
                        value_to_write = None
                    else:
                        try:
                            # If it looks like a clean float/int, parse it, except for 'Info' maybe.
                            if '.' in str(value_to_write):
                                value_to_write = float(value_to_write)
                            elif str(value_to_write).lstrip('-').isdigit():
                                value_to_write = int(value_to_write)
                        except ValueError:
                            pass

                    self.sheet.cell(row=current_row, column=c_idx + 1).value = value_to_write

            return True

        except Exception as e:
            logger_inst.error(f"Failed to apply sheet edits: {e}")
            return False"""

new_save_sheet_edits = """    def save_sheet_edits(self, data: list) -> bool:
        \"\"\"
        Saves changes directly to the currently loaded sheet based on the grid data.

        Args:
            data (list): A list of rows, where each row is a list of string values.
                         Assumes the column count matches the data exactly.
        \"\"\"
        if self.sheet is None:
            logger_inst.error("Cannot save edits: Workbook or sheet is not loaded.")
            return False

        try:
            # Determine start row and skip empty header space based on sheet type
            start_row = 1
            if self.sheet_name in ["Pozycje otwarte", "Trejdy", "Strategia", "Refleksje"]:
                start_row = 5
            elif self.sheet_name == "Salda":
                start_row = 8

            # Clear existing data rows starting from start_row downwards.
            # We determine max row based on actual sheet dimension, and max column.
            max_row = self.sheet.max_row
            max_col = self.sheet.max_column

            for row in range(start_row, max_row + 1):
                for col in range(1, max_col + 1):
                    self.sheet.cell(row=row, column=col).value = None

            # Insert new data
            for r_idx, row_data in enumerate(data):
                # Excel rows are 1-indexed, starting from start_row
                current_row = start_row + r_idx
                for c_idx, val in enumerate(row_data):
                    # Write strings raw/object as per instruction "Treat all incoming edits as raw strings/objects (consistent with our `dtype=object` read strategy)."
                    value_to_write = str(val) if val is not None and val != "" else None
                    self.sheet.cell(row=current_row, column=c_idx + 1).value = value_to_write

            return True

        except Exception as e:
            logger_inst.error(f"Failed to apply sheet edits: {e}")
            return False"""

content = content.replace(old_save_sheet_edits, new_save_sheet_edits)

with open('excel_handler.py', 'w') as f:
    f.write(content)
