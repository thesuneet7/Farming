import asyncio
import pandas as pd
from playwright.async_api import async_playwright
from rapidfuzz import process

# ---------- Helper for fuzzy matching ----------
async def normalize_dropdown(page, selector: str, user_value: str) -> str:
    """Normalize user input against available dropdown options using fuzzy matching.
       Returns the VALUE attribute (not the label)."""
    options = await page.query_selector_all(f"{selector} option")
    option_map = {}
    for opt in options:
        label = (await opt.inner_text()).strip()
        value = await opt.get_attribute("value")
        if label and value:
            option_map[label] = value

    if not option_map:
        return user_value  # fallback

    # Fuzzy match against labels
    best_match, score, _ = process.extractOne(user_value, list(option_map.keys()), score_cutoff=60)
    if best_match:
        print(f"Matched '{user_value}' -> '{best_match}' (score {score})")
        return option_map[best_match]  # return the VALUE
    else:
        print(f"No good match found for '{user_value}', using raw value")
        return user_value


# ---------- Scraper ----------
async def get_dealers_for_market(state_name: str, district_name: str, market_name: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        async def close_popup():
            try:
                await page.wait_for_selector("#onloadModal", timeout=3000)
                close_btn = await page.query_selector(
                    "#onloadModal button.close, #onloadModal .btn-close, .modal .close"
                )
                if close_btn:
                    await close_btn.click()
                    await page.wait_for_timeout(1000)
                    print("Closed popup")
            except:
                pass

        async def extract_table_data():
            try:
                await page.wait_for_selector("table", timeout=15000)
                headers = [await h.inner_text() for h in await page.query_selector_all("table thead tr th")]
                rows = await page.query_selector_all("table tbody tr")
                data = []
                for row in rows:
                    cols = await row.query_selector_all("td")
                    data.append([await col.inner_text() for col in cols])
                return data, headers
            except Exception as e:
                print(f"Error extracting table data: {e}")
                return [], []

        try:
            print("Opening website...")
            await page.goto("https://www.napanta.com/seed-dealer", wait_until="domcontentloaded")
            await page.wait_for_timeout(2000)
            await close_popup()

            # --- Select State ---
            await page.wait_for_selector("#ddlState", timeout=10000)
            state_val = await normalize_dropdown(page, "#ddlState", state_name)
            await page.select_option("#ddlState", value=state_val)
            await page.wait_for_timeout(2000)
            await close_popup()

            # --- Select District ---
            await page.wait_for_selector("#ddlDistrict", timeout=10000)
            district_val = await normalize_dropdown(page, "#ddlDistrict", district_name)
            await page.select_option("#ddlDistrict", value=district_val)
            await page.wait_for_timeout(2000)
            await close_popup()

            # --- Select Market ---
            await page.wait_for_selector("#ddlMarket", timeout=10000)
            market_val = await normalize_dropdown(page, "#ddlMarket", market_name)
            await page.select_option("#ddlMarket", value=market_val)
            await page.wait_for_timeout(1000)
            await close_popup()

            # --- Click GO button ---
            go_button = await page.wait_for_selector("button.go-btn", timeout=10000)
            await go_button.scroll_into_view_if_needed()
            await go_button.click()
            await page.wait_for_timeout(3000)
            await close_popup()

            # --- Extract Data ---
            data, headers = await extract_table_data()
            if data:
                df = pd.DataFrame(data, columns=headers)
                for col in df.columns:
                    df[col] = df[col].astype(str).str.strip()
                df.replace({"": None, "-": None, "nan": None}, inplace=True)
                return df
            else:
                print("No data found")
                return pd.DataFrame()

        except Exception as e:
            print(f"Scraping failed: {e}")
            return pd.DataFrame()
        finally:
            await browser.close()

async def get_top5_and_csv(state, district, market, filename="dealers_full.csv"):
    df = await get_dealers_for_market(state, district, market)
    if df.empty:
        return {"top5": [], "csv": None}

    # Save full CSV
    df.to_csv(filename, index=False)

    # Return first 5 dealers (dicts)
    top5 = df.head(5).to_dict(orient="records")
    return {"top5": top5, "csv": filename}

# -----------------------------
# Example direct run
# -----------------------------
if __name__ == "__main__":
    state = "Uttar Pradesh"
    district = "Mirzapur"
    market = "Nagar City"   # You can type naturally
    df = asyncio.run(get_dealers_for_market(state, district, market))
    if not df.empty:
        print(df.head())
        df.to_csv("dealers_sample.csv", index=False)
        print("Saved to dealers_sample.csv")
    else:
        print("No dealers found.")
