import requests
import pandas as pd
from datetime import datetime

# ---- CONFIG ----
API_KEY = "579b464db66ec23bdd000001ce8cce7242164a315a8d3069bbb48a27"
# Agmarknet: Daily Market Prices (APMC) dataset resource ID
# https://data.gov.in/resources/agmarknet
RESOURCE_ID = "9ef84268-d588-465a-a308-a864a43d0070"
BASE_URL = "https://api.data.gov.in/resource/"

def fetch_mandi_data(district: str | None = None, state="Uttar Pradesh", limit=1000, offset=0, arrival_date: str | None = None):
    """
    Fetch mandi data from data.gov.in API for a specific district & state.
    Returns a pandas DataFrame with cleaned fields.
    """
    url = f"{BASE_URL}{RESOURCE_ID}"
    params = {
        "api-key": API_KEY,
        "format": "json",
        "limit": limit,
        "offset": offset,
        "filters[state]": state,
    }
    if district:
        params["filters[district]"] = district
    if arrival_date:
        # API expects dd/mm/YYYY format for arrival_date equality filter
        params["filters[arrival_date]"] = arrival_date
    
    # Avoid server-side sort that breaks on text fields; sort client-side
    response = requests.get(url, params=params)
    response.raise_for_status()
    
    resp_json = response.json()
    data = resp_json.get("records", [])
    if not data:
        msg = resp_json.get("message") or resp_json.get("msg") or "No records"
        total = resp_json.get("total") or resp_json.get("count")
        print(f"API returned no records. message={msg} total={total}")
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    
    # Clean important fields
    df = df.rename(columns={
        "state": "State",
        "district": "District",
        "market": "Market",
        "commodity": "Commodity",
        "variety": "Variety",
        "grade": "Grade",
        "arrival_date": "Date",
        "min_price": "MinPrice",
        "max_price": "MaxPrice",
        "modal_price": "ModalPrice"
    })
    
    # Convert date and price columns
    df["Date"] = pd.to_datetime(df["Date"], errors="coerce", dayfirst=True)
    df["MinPrice"] = pd.to_numeric(df["MinPrice"], errors="coerce")
    df["MaxPrice"] = pd.to_numeric(df["MaxPrice"], errors="coerce")
    df["ModalPrice"] = pd.to_numeric(df["ModalPrice"], errors="coerce")
    
    return df


def get_prices_for_date(district: str, date_value) -> pd.DataFrame:
    """
    Fetch prices for a specific arrival date. date_value can be a datetime/date/str.
    """
    try:
        dt = pd.to_datetime(date_value, dayfirst=True)
        date_str = dt.strftime("%d/%m/%Y")
    except Exception:
        date_str = str(date_value)
    
    print(f"Searching for date: {date_str}")
    
    # Fetch multiple pages and filter client-side for the specific date
    per_page = 1000
    offset = 0
    pages: list[pd.DataFrame] = []
    max_pages = 20
    total_records = 0
    
    for page_num in range(max_pages):
        page_df = fetch_mandi_data(district, limit=per_page, offset=offset)
        if page_df.empty:
            break
        pages.append(page_df)
        total_records += len(page_df)
        offset += per_page
        print(f"Fetched page {page_num + 1}: {len(page_df)} records (total: {total_records})")
    
    if not pages:
        return pd.DataFrame(columns=["Date", "Market", "Commodity", "Variety", "MinPrice", "MaxPrice", "ModalPrice"])
    
    df = pd.concat(pages, ignore_index=True)
    print(f"Total records fetched: {len(df)}")
    
    # Show unique dates found
    unique_dates = pd.to_datetime(df["Date"], errors="coerce").dt.date.dropna().unique()
    print(f"Available dates in data: {sorted(unique_dates)}")
    
    target = pd.to_datetime(date_str, dayfirst=True).normalize()
    df_normalized = df.copy()
    df_normalized["_D"] = pd.to_datetime(df_normalized["Date"], errors="coerce").dt.normalize()
    filtered = df_normalized[df_normalized["_D"] == target]
    
    if filtered.empty:
        print(f"No exact match found for {date_str}")
        return pd.DataFrame(columns=["Date", "Market", "Commodity", "Variety", "MinPrice", "MaxPrice", "ModalPrice"])
    
    return filtered.sort_values(by=["Market", "Commodity"])[["Date", "Market", "Commodity", "Variety", "MinPrice", "MaxPrice", "ModalPrice"]]


def get_available_dates(district: str) -> list:
    """
    Get list of available dates for a district.
    """
    per_page = 1000
    offset = 0
    pages = []
    max_pages = 20  # Increased to get more historical data
    total_records = 0
    
    print(f"Fetching available dates for {district}...")
    
    for page_num in range(max_pages):
        page_df = fetch_mandi_data(district, limit=per_page, offset=offset)
        if page_df.empty:
            break
        pages.append(page_df)
        total_records += len(page_df)
        offset += per_page
        print(f"Page {page_num + 1}: {len(page_df)} records")
    
    if not pages:
        return []
    
    all_df = pd.concat(pages, ignore_index=True)
    print(f"Total records analyzed: {len(all_df)}")
    
    if all_df["Date"].isna().all():
        return []
    
    dates = pd.to_datetime(all_df["Date"], errors="coerce").dt.date.dropna().unique()
    sorted_dates = sorted(dates, reverse=True)
    
    print(f"Found {len(sorted_dates)} unique dates")
    return sorted_dates


def get_date_range_info(district: str) -> dict:
    """
    Get comprehensive date range information for a district.
    """
    dates = get_available_dates(district)
    if not dates:
        return {"error": "No data available"}
    
    return {
        "total_dates": len(dates),
        "earliest_date": min(dates),
        "latest_date": max(dates),
        "date_range_days": (max(dates) - min(dates)).days,
        "all_dates": dates
    }


def save_csv_safe(df: pd.DataFrame, base_filename: str) -> None:
    """
    Save DataFrame to CSV. If the filename is locked, write to a timestamped file instead.
    """
    try:
        df.to_csv(base_filename, index=False, encoding="utf-8-sig")
    except PermissionError:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        alt = base_filename.replace(".csv", f"_{ts}.csv")
        df.to_csv(alt, index=False, encoding="utf-8-sig")


# ---- Example Usage ----
if __name__ == "__main__":
    print("=== Mandi Prices Data Fetcher (Uttar Pradesh) ===")
    print("Enter the details to fetch mandi prices:")
    
    # Get user input
    district = input("Enter district name (e.g., Lucknow, Agra): ").strip()
    if not district:
        district = "Lucknow"  # default
        print(f"Using default district: {district}")
    
    # Show available date range first
    print(f"\nChecking available dates for {district}...")
    date_info = get_date_range_info(district)
    
    if "error" in date_info:
        print(f"Error: {date_info['error']}")
        exit()
    
    print(f"\n📅 Date Range Information for {district}:")
    print(f"   Total dates available: {date_info['total_dates']}")
    print(f"   Date range: {date_info['earliest_date']} to {date_info['latest_date']}")
    print(f"   Span: {date_info['date_range_days']} days")
    
    if date_info['total_dates'] <= 10:
        print(f"   Available dates: {date_info['all_dates']}")
    else:
        print(f"   Recent dates: {date_info['all_dates'][:5]}")
        print(f"   Oldest dates: {date_info['all_dates'][-5:]}")
    
    date_input = input(f"\nEnter date (dd/mm/yyyy format, e.g., {date_info['latest_date'].strftime('%d/%m/%Y')}): ").strip()
    if not date_input:
        date_input = date_info['latest_date'].strftime("%d/%m/%Y")  # Use latest available date
        print(f"Using latest available date: {date_input}")
    
    print(f"\nFetching prices for {district} on {date_input}...")
    
    # Fetch data for the specified date and district
    result_df = get_prices_for_date(district, date_input)
    
    if result_df.empty:
        print(f"\n❌ No data found for {district} on {date_input}")
        print("Try a different date from the available dates shown above.")
    else:
        print(f"\n✅ Mandi Prices for {district} on {date_input}:")
        print("=" * 80)
        print(result_df[["Date", "Market", "Commodity", "Variety", "MinPrice", "MaxPrice", "ModalPrice"]])
        print(f"\nTotal records: {len(result_df)}")
        
        # Save to CSV
        filename = f"mandi_prices_{district}_{date_input.replace('/', '_')}.csv"
        save_csv_safe(result_df, filename)
        print(f"\n💾 Data saved to: {filename}")
        
        # Show summary
        print(f"\n📊 Summary:")
        print(f"- District: {district}")
        print(f"- Date: {date_input}")
        print(f"- Markets: {result_df['Market'].nunique()}")
        print(f"- Commodities: {result_df['Commodity'].nunique()}")
        print(f"- Price range: ₹{result_df['MinPrice'].min():,.0f} - ₹{result_df['MaxPrice'].max():,.0f}")
        
        # Show top commodities by price
        print(f"\n🏆 Top 5 commodities by modal price:")
        top_commodities = result_df.nlargest(5, 'ModalPrice')[['Commodity', 'Variety', 'ModalPrice']]
        for _, row in top_commodities.iterrows():
            print(f"   {row['Commodity']} ({row['Variety']}): ₹{row['ModalPrice']:,.0f}")