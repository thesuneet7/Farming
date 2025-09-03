import asyncio
import pandas as pd
from playwright.async_api import async_playwright

async def scrape_up_dealers():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        async def close_popup():
            try:
                # Wait briefly for popup, if exists
                popup = await page.query_selector("#onloadModal")
                if popup:
                    close_btn = await popup.query_selector("button.close, .btn-close, .close")
                    if close_btn:
                        await close_btn.click()
                        print("Closed popup")
                        await page.wait_for_timeout(1000)
                    else:
                        # Fallback: press Escape
                        await page.keyboard.press("Escape")
                        print("Dismissed popup with Escape")
                        await page.wait_for_timeout(1000)
            except:
                pass

        await page.goto("https://www.napanta.com/seed-dealer", wait_until="domcontentloaded")
        await page.wait_for_selector("#ddlState")

        # Close popup if it appears on first load
        await close_popup()

        # Select Uttar Pradesh
        await page.select_option("#ddlState", label="Uttar Pradesh")
        await page.wait_for_timeout(2000)

        # Get all districts
        district_options = await page.query_selector_all("#ddlDistrict option")
        districts = [await d.inner_text() for d in district_options[1:]]  # skip first option

        all_data = []

        for district in districts:
            print(f"Processing district: {district}")
            await page.select_option("#ddlDistrict", label=district)
            await page.wait_for_timeout(2000)
            await close_popup()

            # Get all areas for this district
            area_options = await page.query_selector_all("#ddlMarket option")
            areas = [await a.inner_text() for a in area_options[1:]]

            for area in areas:
                print(f"   Processing area: {area}")
                await page.select_option("#ddlMarket", label=area)
                await close_popup()

                # Click GO
                go_btn = await page.wait_for_selector("button.go-btn", timeout=10000)
                await go_btn.scroll_into_view_if_needed()
                await go_btn.click()
                await page.wait_for_timeout(3000)
                await close_popup()

                # Extract dealer table
                try:
                    rows = await page.query_selector_all("table tbody tr")
                    for row in rows:
                        cols = await row.query_selector_all("td")
                        data = [await c.inner_text() for c in cols]
                        if data:
                            all_data.append(data)
                except Exception as e:
                    print(f"      No data for {district}-{area}: {e}")

        await browser.close()

        # Convert to DataFrame
        if all_data:
            headers = [
                "Serial No", "Type", "District", "Area",
                "Dealer name", "Mobile No", "Address", "NaPanta Mobile App"
            ]
            df = pd.DataFrame(all_data, columns=headers[:len(all_data[0])])
            df.to_csv("uttar_pradesh_dealers.csv", index=False)
            print(f"\n✅ Saved {len(df)} dealers to uttar_pradesh_dealers.csv")
            return df
        else:
            print("No data extracted")
            return pd.DataFrame()


if __name__ == "__main__":
    asyncio.run(scrape_up_dealers())
