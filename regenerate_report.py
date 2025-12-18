from report_generator import ReportGenerator
import os

print("Generating Dashboard...")
gen = ReportGenerator()
output = gen.generate_dashboard()
print(f"Done: {output}")

# Open it
gen.open_in_browser(output)
