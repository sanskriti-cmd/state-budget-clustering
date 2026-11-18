#!/usr/bin/env python3
"""Render paper.html to the journal-format PDF (needs Playwright + Chromium and the Carlito font)."""
import os
import sys

from playwright.sync_api import sync_playwright

here = os.path.dirname(os.path.abspath(__file__))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "State_Budget_Priorities_Clustering_Paper.pdf")

HEADER = """
<div style="width:100%; padding:0 18mm; font-family:Carlito,Calibri,sans-serif; -webkit-print-color-adjust:exact;">
  <div style="background:#1f3864; color:#fff; font-size:8.5px; font-weight:bold; padding:4px 8px;
              display:flex; justify-content:space-between;">
    <span>ML Application Assignment, B.Sc. (H) Computer Science, Sem VI (University of Delhi)</span>
    <span>Journal-format submission</span>
  </div>
</div>"""
FOOTER = """
<div style="width:100%; padding:0 18mm; font-family:Carlito,Calibri,sans-serif; font-size:8px; color:#595959;">
  <div style="border-top:0.6px solid #bbb; padding-top:4px; display:flex; justify-content:space-between;">
    <span>Clustering Indian states by budget priorities | RBI State Finances 2025-26 | SDG 16 and SDG 17</span>
    <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
  </div>
</div>"""

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("file://" + os.path.join(here, "paper.html"))
    page.wait_for_load_state("networkidle")
    page.pdf(path=out, format="A4", print_background=True, display_header_footer=True,
             header_template=HEADER, footer_template=FOOTER,
             margin={"top": "22mm", "bottom": "20mm", "left": "18mm", "right": "18mm"})
    browser.close()
print("wrote", out)
