import re
with open('app_gui.py', 'r') as f:
    content = f.read()

# _run_scan_screenshot_ai expects `self.api_button` and `self.vision_button` to be disabled before. The code snippet review mentioned the hasattr check is a code smell. Let's fix that. Since buttons are gone, we shouldn't even interact with them.

old_scan_thread = """    def _run_scan_screenshot_ai_thread(self, file_path):
        if hasattr(self, 'api_button'):
            self.api_button.configure(state="disabled")
        if hasattr(self, 'vision_button'):
            self.vision_button.configure(state="disabled")
        logging.info(f"--- Starting AI analysis for dropped file: {os.path.basename(file_path)} ---")
        thread = threading.Thread(target=self._run_scan_screenshot_ai, args=(file_path,), daemon=True)
        thread.start()"""

new_scan_thread = """    def _run_scan_screenshot_ai_thread(self, file_path):
        logging.info(f"--- Starting AI analysis for dropped file: {os.path.basename(file_path)} ---")
        thread = threading.Thread(target=self._run_scan_screenshot_ai, args=(file_path,), daemon=True)
        thread.start()"""

content = content.replace(old_scan_thread, new_scan_thread)


old_scan_screenshot_ai = """    def scan_screenshot_ai(self):
        \"\"\"
        Opens a file dialog to select an image, then triggers Vision parsing in a background thread.
        \"\"\"
        file_path = filedialog.askopenfilename(
            title="Select Trade Screenshot",
            filetypes=[("Image files", "*.png *.jpg *.jpeg")]
        )

        if not file_path:
            return

        if hasattr(self, 'api_button'):
            self.api_button.configure(state="disabled")
        if hasattr(self, 'vision_button'):
            self.vision_button.configure(state="disabled")
        logging.info(f"--- Starting AI analysis for file: {os.path.basename(file_path)} ---")

        thread = threading.Thread(target=self._run_scan_screenshot_ai, args=(file_path,), daemon=True)
        thread.start()"""

new_scan_screenshot_ai = """    def scan_screenshot_ai(self):
        \"\"\"
        Opens a file dialog to select an image, then triggers Vision parsing in a background thread.
        \"\"\"
        file_path = filedialog.askopenfilename(
            title="Select Trade Screenshot",
            filetypes=[("Image files", "*.png *.jpg *.jpeg")]
        )

        if not file_path:
            return

        logging.info(f"--- Starting AI analysis for file: {os.path.basename(file_path)} ---")

        thread = threading.Thread(target=self._run_scan_screenshot_ai, args=(file_path,), daemon=True)
        thread.start()"""

content = content.replace(old_scan_screenshot_ai, new_scan_screenshot_ai)

old_update_portfolio_api = """    def update_portfolio_api(self):
        \"\"\"
        Triggers the API update in a background thread.
        \"\"\"
        self.api_button.configure(state="disabled")
        self.vision_button.configure(state="disabled")
        logging.info("--- Starting Market Prices Update ---")

        thread = threading.Thread(target=self._run_update_portfolio_api, daemon=True)
        thread.start()"""

new_update_portfolio_api = """    def update_portfolio_api(self):
        \"\"\"
        Triggers the API update in a background thread.
        \"\"\"
        logging.info("--- Starting Market Prices Update ---")

        thread = threading.Thread(target=self._run_update_portfolio_api, daemon=True)
        thread.start()"""

content = content.replace(old_update_portfolio_api, new_update_portfolio_api)

# _run_auto_update_sequence
old_auto_update_seq = """    def _run_auto_update_sequence(self):
        \"\"\"Runs the portfolio update and then immediately the saldo update.\"\"\"
        self.api_button.configure(state="disabled")
        self.vision_button.configure(state="disabled")
        self.saldo_button.configure(state="disabled")

        def _sequence():
            # 1. Update Market Prices
            self._run_update_portfolio_api(trigger_saldo_after=True)

        thread = threading.Thread(target=_sequence, daemon=True)
        thread.start()"""

new_auto_update_seq = """    def _run_auto_update_sequence(self):
        \"\"\"Runs the portfolio update and then immediately the saldo update.\"\"\"

        def _sequence():
            # 1. Update Market Prices
            self._run_update_portfolio_api(trigger_saldo_after=True)

        thread = threading.Thread(target=_sequence, daemon=True)
        thread.start()"""

content = content.replace(old_auto_update_seq, new_auto_update_seq)

with open('app_gui.py', 'w') as f:
    f.write(content)
