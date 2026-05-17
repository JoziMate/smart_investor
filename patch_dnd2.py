import re
with open('app_gui.py', 'r') as f:
    content = f.read()

# _run_scan_screenshot_ai disables buttons but we need to ensure that it correctly skips missing buttons.
scan_str = """        self.api_button.configure(state="disabled")
        self.vision_button.configure(state="disabled")"""

new_scan_str = """        if hasattr(self, 'api_button'):
            self.api_button.configure(state="disabled")
        if hasattr(self, 'vision_button'):
            self.vision_button.configure(state="disabled")"""

content = content.replace(scan_str, new_scan_str)

with open('app_gui.py', 'w') as f:
    f.write(content)
