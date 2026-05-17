import re
with open('app_gui.py', 'r') as f:
    content = f.read()

# Remove references to deleted buttons in other methods
content = re.sub(r'\s*self\.api_button\.configure\(state="disabled"\)', '', content)
content = re.sub(r'\s*self\.vision_button\.configure\(state="disabled"\)', '', content)
content = re.sub(r'\s*self\.saldo_button\.configure\(state="disabled"\)', '', content)
content = re.sub(r'\s*self\.reflection_button\.configure\(state="disabled"\)', '', content)
content = re.sub(r'\s*self\.export_button\.configure\(state="disabled"\)', '', content)

content = re.sub(r'\s*self\.after\(0, lambda: self\.saldo_button\.configure\(state="normal"\)\)', '', content)
content = re.sub(r'\s*self\.after\(0, lambda: self\.reflection_button\.configure\(state="normal"\)\)', '', content)
content = re.sub(r'\s*self\.after\(0, lambda: self\.export_button\.configure\(state="normal"\)\)', '', content)

# Update _restore_buttons
restore_buttons_str = """    def _restore_buttons(self):
        \"\"\"
        Re-enables the buttons on the main thread after background tasks finish.
        \"\"\"
        self.api_button.configure(state="normal")
        self.vision_button.configure(state="normal")"""

new_restore_buttons_str = """    def _restore_buttons(self):
        \"\"\"
        (Deprecated) Used to re-enable buttons on the main thread.
        \"\"\"
        pass"""

content = content.replace(restore_buttons_str, new_restore_buttons_str)

with open('app_gui.py', 'w') as f:
    f.write(content)
