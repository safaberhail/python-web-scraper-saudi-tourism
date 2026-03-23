"""
Saudi Tourism Ministry Data Scraper
Author: [اسمك هنا]
Description: A professional web scraping tool designed to extract tourism entities 
data from the Saudi Ministry of Tourism portal, handling anti-bot measures and Shadow DOM.
"""

import os
import time
import pandas as pd
from playwright.sync_api import sync_playwright

class TourismScraper:
    def __init__(self, output_file="Saudi_Tourism_Data.xlsx"):
        self.output_file = output_file
        self.base_url = "https://mt.gov.sa/e-services/forms/licensed-activities-inquiry"
        self.user_data_dir = os.path.join(os.getcwd(), "chrome_profile")
        self.results = []

    def start_browser(self, playwright):
        """Initializes a persistent browser context to bypass anti-bot detections."""
        print("[*] Launching browser with persistent context...")
        context = playwright.chromium.launch_persistent_context(
            self.user_data_dir,
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0]
        # Stealth script to hide automation fingerprints
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return context, page

    def extract_page_data(self, page):
        """Extracts data from the current page cards using an optimized JS script."""
        print(f"[*] Extracting data from the current page...")
        
        # This script targets data even within Shadow DOM layers
        return page.evaluate("""
            () => {
                let cards = Array.from(document.querySelectorAll('div')).filter(d => 
                    d.innerText && d.innerText.includes('رقم الرخصة') && 
                    d.innerText.includes('التصنيف') && d.innerText.length < 500
                );
                return cards.map(c => ({ content: c.innerText }));
            }
        """)

    def parse_content(self, raw_data):
        """Parses raw text into structured dictionary format."""
        for entry in raw_data:
            lines = [line.strip() for line in entry['content'].split('\n') if line.strip()]
            if not lines: continue
            
            item = {
                'Entity Name': lines[0],
                'Category': self._find_value(lines, "التصنيف"),
                'Entity Type': self._find_value(lines, "نوع المنشأة"),
                'License Number': self._find_value(lines, "رقم الرخصة"),
                'License Status': self._find_value(lines, "حالة الترخيص"),
                'Location': self._find_value(lines, "موقع المنشأة")
            }
            self.results.append(item)

    def _find_value(self, lines, keyword):
        """Helper to find values next to keywords in text lines."""
        for i, line in enumerate(lines):
            if keyword in line:
                return lines[i+1] if i+1 < len(lines) else ""
        return ""

    def save_to_excel(self):
        """Saves the extracted data to an Excel file using Pandas."""
        if self.results:
            df = pd.DataFrame(self.results).drop_duplicates(subset=['License Number'])
            df.to_excel(self.output_file, index=False)
            print(f"[+] Success! {len(df)} records saved to {self.output_file}")
        else:
            print("[-] No data found to save.")

    def run(self):
        """Main execution flow."""
        with sync_playwright() as p:
            context, page = self.start_browser(p)
            page.goto(self.base_url)
            
            print("\n--- USER ACTION REQUIRED ---")
            print("1. Perform your search in the opened browser.")
            print("2. Wait for results to appear.")
            input("3. Press Enter here to start automated extraction...")

            page_num = 1
            try:
                while True:
                    print(f"\n[Page {page_num}]")
                    time.sleep(3)
                    raw_data = self.extract_page_data(page)
                    self.parse_content(raw_data)
                    
                    # Pagination logic
                    next_btn = page.locator("button:has-text('التالي'), a:has-text('التالي'), .page-link:has-text('التالي')").first
                    if next_btn.is_visible() and "disabled" not in (next_btn.get_attribute("class") or ""):
                        next_btn.click(force=True)
                        page_num += 1
                    else:
                        break
            except Exception as e:
                print(f"[!] Error during scraping: {e}")
            finally:
                self.save_to_excel()
                context.close()

if __name__ == "__main__":
    scraper = TourismScraper()
    scraper.run()