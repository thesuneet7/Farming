# dealer_tool.py

import asyncio
import pandas as pd
from playwright.async_api import async_playwright

# This function is working correctly, no changes needed.
async def get_available_markets(state_name: str, district_name: str):
    # ... (The code for this function remains the same as before)
    """
    Part 1: Get all available markets for a given state and district
    Returns: List of market names
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        async def close_popup(page_context):
            try:
                modal = await page_context.query_selector("#onloadModal")
                if modal and await modal.is_visible():
                    close_button = await modal.query_selector("button.close")
                    if close_button:
                        await close_button.click()
                        await page_context.wait_for_timeout(1000) # Wait for animation
            except Exception:
                pass # No popup found or other error
        
        try:
            await page.goto("https://www.napanta.com/seed-dealer", wait_until="domcontentloaded")
            await close_popup(page)
            
            await page.select_option("#ddlState", label=state_name)
            await page.wait_for_timeout(2000)
            
            await page.select_option("#ddlDistrict", label=district_name)
            await page.wait_for_timeout(2000)

            await page.wait_for_selector("#ddlMarket", timeout=10000)
            market_options = await page.query_selector_all("#ddlMarket option")
            
            markets = []
            for option in market_options[1:]:  # Skip first "Select Market" option
                market_text = await option.inner_text()
                if market_text and market_text.strip():
                    markets.append(market_text.strip())
            
            return markets
            
        except Exception as e:
            print(f"Error getting markets: {e}")
            await page.screenshot(path="error_screenshot_markets.png")
            return []
        finally:
            await browser.close()


async def get_dealers_for_market(state_name: str, district_name: str, market_name: str):
    """
    Part 2: Get data for a specific state, district, and market combination
    """
    async with async_playwright() as p:
        # We'll keep this visible for now so you can confirm the fix
        browser = await p.chromium.launch(headless=False, slow_mo=500)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # --- IMPROVEMENT #1: A more robust popup closer ---
        async def close_popup(page_context):
            """Checks for a visible popup and tries multiple ways to close it."""
            try:
                modal = await page_context.query_selector("#onloadModal")
                # Only proceed if the modal exists and is visible
                if modal and await modal.is_visible():
                    print("Popup is visible. Attempting to close...")
                    close_button = await modal.query_selector("button.close")
                    if close_button and await close_button.is_visible():
                        await close_button.click()
                        print("Clicked the popup 'X' button.")
                    else:
                        # Fallback to pressing the Escape key
                        await page_context.keyboard.press("Escape")
                        print("Used 'Escape' key to close popup.")
                    # Wait for the closing animation
                    await page_context.wait_for_timeout(1000)
            except Exception as e:
                print(f"Could not close popup (this might be okay): {e}")

        async def extract_table_data(page_context):
            try:
                await page_context.wait_for_selector("table tbody tr", timeout=15000)
                headers = [th.strip() for th in await page_context.locator("table thead tr th").all_inner_texts()]
                rows = await page_context.query_selector_all("table tbody tr")
                rows_data = [
                    [td.strip() for td in await row.locator("td").all_inner_texts()] 
                    for row in rows if len(await row.locator("td").all_inner_texts()) > 1
                ]
                return rows_data, headers
            except Exception as e:
                print(f"Error extracting table data: {e}")
                return [], []
        
        try:
            await page.goto("https://www.napanta.com/seed-dealer", wait_until="domcontentloaded")
            await close_popup(page)
            
            # --- IMPROVEMENT #2: Calling close_popup after EVERY action ---
            await page.select_option("#ddlState", label=state_name)
            await close_popup(page)
            
            await page.select_option("#ddlDistrict", label=district_name)
            await close_popup(page)
            
            await page.select_option("#ddlMarket", label=market_name)
            await close_popup(page)
            
            go_button = await page.wait_for_selector("button.go-btn", timeout=10000)
            
            async with page.expect_response(lambda r: "seed-dealer" in r.url and r.status == 200, timeout=20000):
                await go_button.click()
            print("Network response received after clicking 'GO'.")

            await close_popup(page)
            
            data, headers = await extract_table_data(page)
            
            if not data:
                print("No data rows found after extraction.")
                return pd.DataFrame()

            # Header and DataFrame creation logic...
            if not headers:
                headers = ["Serial No", "Type", "District", "Area", "Dealer name", 
                           "Mobile No", "Address", "NaPanta Mobile App"]
            if data and len(data[0]) != len(headers):
                 headers = headers[:len(data[0])]
            df = pd.DataFrame(data, columns=headers)
            return df
            
        except Exception as e:
            print(f"Error during scraping: {e}")
            await page.screenshot(path="error_screenshot_final.png")
            return pd.DataFrame()
        finally:
            await browser.close()