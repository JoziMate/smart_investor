import re
with open('app_gui.py', 'r') as f:
    content = f.read()

# Remove 2. Buttons Frame
content = re.sub(r'        # 2\. Buttons Frame.*?        self\.risk_calc_button\.grid\(row=0, column=3, padx=10\)', '', content, flags=re.DOTALL)

with open('app_gui.py', 'w') as f:
    f.write(content)
