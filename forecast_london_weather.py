import pandas as pd
from neuralprophet import NeuralProphet

import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend - prevents GUI crashes
import matplotlib.pyplot as plt
plt.ioff()  # Turn off interactive mode

def process_scheduled_call(influxdb3_local, call_time, args=None):
    influxdb3_local.info("Running NeuralProphet forecast on 'london_weather'")

    # Query full data from InfluxDB
    query = """
        SELECT time AS ds, temperature_c, precipitation_mm
        FROM london_weather
        ORDER BY time
    """
    results = influxdb3_local.query(query)
    if not results:
        influxdb3_local.warn("No data found in 'london_weather'")
        return

    df = pd.DataFrame(results)
    df["ds"] = pd.to_datetime(df["ds"])

    # Train on 3 months of data up to Jan 31, 2024
    start = pd.Timestamp("2023-11-01 00:00:00")
    cutoff = pd.Timestamp("2024-01-31 23:00:00")
    df = df[(df["ds"] >= start) & (df["ds"] <= cutoff)]

    # Forecast horizon: 7 days (168 hours)
    forecast_horizon = 168

    def forecast_and_write(series_name, value_column):
        df_series = df[["ds", value_column]].rename(columns={value_column: "y"}).dropna()
        if df_series.empty:
            influxdb3_local.warn(f"No data for {value_column}")
            return

        model = NeuralProphet(
            yearly_seasonality=True,
            weekly_seasonality=True,
            daily_seasonality=True,
            learning_rate=0.01,
            batch_size=32
        )
        model.fit(df_series, freq="H")

        future = model.make_future_dataframe(df_series, periods=forecast_horizon)
        forecast = model.predict(future)
        forecast_only = forecast[forecast["ds"] > df_series["ds"].max()]

        # Write forecast to InfluxDB
        for _, row in forecast_only.iterrows():
            ts_ns = int(pd.to_datetime(row["ds"]).timestamp() * 1e9)
            line = LineBuilder("forecast_weather")
            line.time_ns(ts_ns)
            line.string_field("forecast_time", str(row["ds"]))
            line.string_field("type", series_name)
            line.float64_field("yhat1", max(0, row["yhat1"]))
            influxdb3_local.write(line)

        # Save plot to PNG
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df_series["ds"], df_series["y"], label="Historical", color="blue")
        ax.plot(forecast["ds"], forecast["yhat1"], label="Forecast", color="green")
        ax.axvline(df_series["ds"].max(), color="gray", linestyle="--", label="Forecast Start")
        ax.set_title(f"NeuralProphet Forecast - {series_name}")
        ax.set_xlabel("Date")
        ax.set_ylabel(series_name)
        ax.legend()
        ax.grid(True)
        fig.tight_layout()
        plot_path = f"/tmp/{series_name}_forecast.png"
        fig.savefig(plot_path)
        plt.close(fig)

        influxdb3_local.info(f"Saved forecast plot: {plot_path}")
        influxdb3_local.info(f"Forecast complete for {series_name} through {forecast_only['ds'].max()}")

    forecast_and_write("temperature_c", "temperature_c")
    forecast_and_write("precipitation_mm", "precipitation_mm")