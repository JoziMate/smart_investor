import re
with open('app_gui.py', 'r') as f:
    content = f.read()

# Make rowheight larger (32) and font 14pt (already 14pt, just ensure rowheight)
content = re.sub(r'rowheight=30,', 'rowheight=32,', content)

# Replace on_double_click to be more robust
old_on_double_click = """    def on_double_click(self, event):
        \"\"\"
        Handles double-click events to spawn an entry widget over the cell.
        \"\"\"
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)
        if not column or not item:
            return

        col_index = int(column[1:]) - 1
        x, y, width, height = self.tree.bbox(item, column)

        # Get current value
        current_value = self.tree.set(item, column)

        # Create entry widget
        entry = ctk.CTkEntry(self.tree, font=ctk.CTkFont(size=14))
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, current_value)
        entry.select_range(0, 'end')
        entry.focus()

        def save_edit(event=None):
            if entry.winfo_exists():
                new_value = entry.get()
                self.tree.set(item, column, new_value)
                entry.destroy()
                logging.info(f"Cell edited at row {item}, col {column}: '{current_value}' -> '{new_value}'")

        def cancel_edit(event=None):
            if entry.winfo_exists():
                entry.destroy()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)
        entry.bind("<Escape>", cancel_edit)"""


new_on_double_click = """    def on_double_click(self, event):
        \"\"\"
        Handles double-click events to spawn an entry widget over the cell.
        \"\"\"
        region = self.tree.identify_region(event.x, event.y)
        if region != "cell":
            return

        column = self.tree.identify_column(event.x)
        item = self.tree.identify_row(event.y)
        if not column or not item:
            return

        col_index = int(column[1:]) - 1
        x, y, width, height = self.tree.bbox(item, column)

        # Get current value
        current_value = self.tree.set(item, column)

        # Create entry widget with explicit configuration matching the Treeview
        # Using a solid font setting inside a new CTkEntry instance to guarantee it renders clearly
        # and doesn't get squished.
        entry = ctk.CTkEntry(
            self.tree,
            font=ctk.CTkFont(family="Arial", size=14),
            border_width=1,
            corner_radius=0
        )
        entry.place(x=x, y=y, width=width, height=height)
        entry.insert(0, current_value)
        entry.select_range(0, 'end')
        entry.focus()

        def save_edit(event=None):
            if entry.winfo_exists():
                new_value = entry.get()
                self.tree.set(item, column, new_value)
                entry.destroy()
                logging.info(f"Cell edited at row {item}, col {column}: '{current_value}' -> '{new_value}'")

        def cancel_edit(event=None):
            if entry.winfo_exists():
                entry.destroy()

        entry.bind("<Return>", save_edit)
        entry.bind("<FocusOut>", save_edit)
        entry.bind("<Escape>", cancel_edit)"""

content = content.replace(old_on_double_click, new_on_double_click)

with open('app_gui.py', 'w') as f:
    f.write(content)
