import requests
import json
import pandas as pd

url = "https://soilhealth4.dac.gov.in/"

headers = {
    "Content-Type": "application/json",
    "Accept": "application/json",
}

payload = {
    "operationName": "GetTestCenters",
    "variables": {
        "state": "63f600f38cec41e6c9607e6b",   # Uttar Pradesh
        # Remove or set district to null to get all districts
        "district": None
    },
    "query": """
    query GetTestCenters($state: String, $district: String) {
      getTestCenters(state: $state, district: $district) {
        district
        email
        name
        STLdetails {
          phone
          __typename
        }
        state
        region
        address
        __typename
      }
    }
    """
}

response = requests.post(url, headers=headers, json=payload)

print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    centers = data.get('data', {}).get('getTestCenters', [])
    
    print(f"Total Soil Testing Centers in Uttar Pradesh: {len(centers)}")
    
    # Create DataFrame
    df_data = []
    
    for center in centers:
        # Extract district name
        district_info = center.get('district', {})
        if isinstance(district_info, dict):
            district_name = district_info.get('name', 'Unknown District')
        else:
            district_name = str(district_info) if district_info else 'Unknown District'
        
        # Extract region information
        region_info = center.get('region', {})
        state_name = 'N/A'
        region_district_name = 'N/A'
        coordinates = 'N/A'
        
        if isinstance(region_info, dict):
            # State name
            state_info = region_info.get('state', {})
            if isinstance(state_info, dict):
                state_name = state_info.get('name', 'N/A')
            
            # Region district name
            region_district_info = region_info.get('district', {})
            if isinstance(region_district_info, dict):
                region_district_name = region_district_info.get('name', 'N/A')
            
            # Coordinates
            geolocation = region_info.get('geolocation', {})
            if isinstance(geolocation, dict) and 'coordinates' in geolocation:
                coords = geolocation['coordinates']
                if len(coords) >= 2:
                    coordinates = f"{coords[1]}, {coords[0]}"  # lat, lng format
        
        # Extract phone
        phone = 'N/A'
        if center.get('STLdetails') and center['STLdetails'].get('phone'):
            phone = center['STLdetails']['phone']
        
        # Create row data
        row_data = {
            'Center_Name': center.get('name', 'N/A'),
            'District': district_name,
            'State': state_name,
            'Email': center.get('email', 'N/A'),
            'Phone': phone,
            'Address': center.get('address', 'N/A'),
            'Region_District': region_district_name,
            'Coordinates': coordinates
        }
        
        df_data.append(row_data)
    
    # Create DataFrame
    df = pd.DataFrame(df_data)
    
    # Display summary
    print("\n" + "="*80)
    print("DATAFRAME SUMMARY:")
    print("="*80)
    print(f"Total Records: {len(df)}")
    print(f"Total Districts: {df['District'].nunique()}")
    print(f"\nDistricts covered:")
    district_counts = df['District'].value_counts()
    for district, count in district_counts.items():
        print(f"  {district}: {count} centers")
    
    # Display first few rows
    print("\n" + "="*80)
    print("SAMPLE DATA (First 5 rows):")
    print("="*80)
    print(df.head().to_string(index=False))
    
    # Save DataFrame to different formats
    df.to_csv('uttar_pradesh_soil_centers.csv', index=False)
    
    # Try to save Excel file, handle missing openpyxl
    excel_saved = False
    try:
        df.to_excel('uttar_pradesh_soil_centers.xlsx', index=False)
        excel_saved = True
    except ImportError:
        print("Note: openpyxl not installed. Excel file not created.")
        print("Install with: pip install openpyxl")
    
    # Save raw JSON data as well
    with open('uttar_pradesh_soil_centers_raw.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    print(f"\n" + "="*80)
    print("FILES SAVED:")
    print("="*80)
    print("✓ uttar_pradesh_soil_centers.csv - CSV format")
    if excel_saved:
        print("✓ uttar_pradesh_soil_centers.xlsx - Excel format")
    else:
        print("✗ Excel format - openpyxl module required")
    print("✓ uttar_pradesh_soil_centers_raw.json - Raw JSON data")
    
    # Return DataFrame for further analysis
    print(f"\nDataFrame shape: {df.shape}")
    print("DataFrame is ready for analysis!")
    
    # Display DataFrame info
    print("\n" + "="*80)
    print("DATAFRAME INFO:")
    print("="*80)
    print(df.info())
    
else:
    print(f"Error: {response.status_code}")
    print(response.text)