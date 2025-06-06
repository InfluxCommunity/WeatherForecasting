import pandas as pd

# Load the downloaded CSV file
# Skip the first few rows of metadata
df = pd.read_csv("london_weather_2024_2025.csv", skiprows=3)

# The column names are 'temperature_2m (°C)' and 'precipitation (mm)'.
# Let's rename them for easier access.
df.rename(columns={
    'temperature_2m (°C)': 'temperature_c',
    'precipitation (mm)': 'precipitation_mm'
}, inplace=True)

# Open the output file
with open("london_weather_2024_2025.lp", "w") as f:
    # Iterate over each row in the DataFrame
    for _, row in df.iterrows():
        # Convert the ISO 8601 time string to a nanosecond precision Unix timestamp
        timestamp_ns = int(pd.to_datetime(row["time"]).timestamp() * 1e9)
        
        # Get temperature and precipitation, handling potential missing values
        temp = row["temperature_c"]
        precip = row["precipitation_mm"]
        
        if pd.notna(temp) and pd.notna(precip):
            # Format the string in InfluxDB Line Protocol format
            # Using a new measurement name to avoid conflicts
            line = f"london_weather_24_25,city=london temperature_c={temp},precipitation_mm={precip} {timestamp_ns}"
            # Write the line to the file
            f.write(line + "\n")

print("Conversion to Line Protocol format complete.")
print("Output file: london_weather_2024_2025.lp") 