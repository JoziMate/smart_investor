import re
with open('app_gui.py', 'r') as f:
    content = f.read()

# 1. Update imports
import_insert_pos = content.find('import customtkinter as ctk')
if import_insert_pos != -1:
    new_imports = "from tkinterdnd2 import TkinterDnD, DND_FILES\n"
    content = content[:import_insert_pos] + new_imports + content[import_insert_pos:]

# 2. Inherit from TkinterDnD.Tk or wrap. We can use a wrapper for CTk.
class_def = "class SmartInwestorApp(ctk.CTk):"
new_class_def = """class TkinterDnDCTk(ctk.CTk, TkinterDnD.DnDWrapper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.TkdndVersion = TkinterDnD._require(self)

class SmartInwestorApp(TkinterDnDCTk):"""
content = content.replace(class_def, new_class_def)

# 3. Add drop target setup
init_pos = content.find('        # Layout configuration')
if init_pos != -1:
    drop_setup = """        # Setup Drag and Drop
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_file_drop)

"""
    content = content[:init_pos] + drop_setup + content[init_pos:]

# 4. Add the handler function
handler_def = """    def handle_file_drop(self, event):
        \"\"\"
        Handles file drop events on the main window.
        \"\"\"
        file_path = event.data
        if file_path.startswith('{') and file_path.endswith('}'):
            file_path = file_path[1:-1]

        # Clean up path issues sometimes present on Windows
        file_path = file_path.strip()

        if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
            logging.info(f"File dropped: {file_path}")
            # Ensure file picker is bypassed and start scanning
            self._run_scan_screenshot_ai_thread(file_path)
        else:
            logging.warning(f"Ignored dropped file (unsupported type): {file_path}")

    def _run_scan_screenshot_ai_thread(self, file_path):
        self.api_button.configure(state="disabled") if hasattr(self, 'api_button') else None
        self.vision_button.configure(state="disabled") if hasattr(self, 'vision_button') else None
        logging.info(f"--- Starting AI analysis for dropped file: {os.path.basename(file_path)} ---")
        thread = threading.Thread(target=self._run_scan_screenshot_ai, args=(file_path,), daemon=True)
        thread.start()

"""

# Insert right before scan_screenshot_ai
scan_pos = content.find('    def scan_screenshot_ai(self):')
if scan_pos != -1:
    content = content[:scan_pos] + handler_def + content[scan_pos:]


with open('app_gui.py', 'w') as f:
    f.write(content)
