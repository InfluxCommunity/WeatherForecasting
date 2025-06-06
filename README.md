# Weather Forecasting Workshop

Workshop content for forecasting weather data including anomaly detection using InfluxDB 3 Core's Python Processing Engine.

**Slides**: https://www.slideshare.net/slideshow/timeseries-machine-learning-pydata-london-2025/280261049

### Pre-Requisites:

1. **Python**: Make sure you have Python version 3.x on your system.
2. **Code Editor**: Your favorite code editor.
3. **Install InfluxDB 3**: Either InfluxDB 3 Core or Enterprise.

   - You can install it as a `Docker Image` or directly using `Simple Download` option.
   - When promoted **Start InfluxDB Now? Type 'n'** as we will start it later.

   InfluxDB 3 Core

   ```shell
   curl -O https://www.influxdata.com/d/install_influxdb3.sh && sh install_influxdb3.sh
   ```

   InfluxDB 3 Enterprise

   ```shell
   curl -O https://www.influxdata.com/d/install_influxdb3.sh && sh install_influxdb3.sh enterprise
   ```

4. **Verify installation**: Open terminal window and run `influxdb3 --version` command without error to the latest version installed successfully.

## Processing Engine

It is an embedded Python VM that runs inside your InfluxDB 3 database and lets you:

- Process data as it's written to the database.
- Run code on a schedule.
- Create API endpoints that execute Python code.
- Maintain state between executions with an in-memory cache.

### Plugins & Triggers

- **Plugins**: Python scripts executed by InfluxDB, containing callback functions defined for specific tasks.

- **Triggers**: Mechanisms that activate plugins based on specific conditions or schedules.
  - Configure triggers with arguments (--trigger-arguments) to control plugin behavior.
  - Multiple triggers can run plugins simultaneously, synchronously or asynchronously.

### Workflow

```text
+-----------------+
|   Data Source   |
| (Telegraf, CSV, |
|  CLI, API etc)  |
+-----------------+
         |
         | Write Data
         V
+-----------------+
|   InfluxDB 3    |
| Core/Enterprise |
+-----------------+
         |
         | WAL Flush
         V
+-----------------+       +-----------------+
|  Set Trigger(s) |------>| Executes Plugin |
| (Data Write,    |       |  (Python Code)  |
|  Scheduled,     |       |                 |
|  HTTP Request)  |       |                 |
+-----------------+       +-----------------+
         |                |       |
         |                |       |  Read/Write via API
         |                |       V
         |                | +-----------------+
         |                | |  InfluxDB 3     |
         |                | |  Data Storage   |
         |                | | (Tables, etc.)  |
         |                | +-----------------+
         |                |       |
         |                |       |  Optional APIs
         |                |       V
         |                | +---------------------------------------+
         |                | |In-Memory Cache, Write, Query, Log etc |
         |                | |                                       |
         |                | +---------------------------------------+
         +----------------+
```

### Setup

To enable the Processing Engine, you need to tell InfluxDB where to find your Python plugin files. Use the `--plugin-dir` option when starting the server.

1. Create a plugin directory anywhere you prefer as this is where plugin code will reside. Optionally, you also reference plugin from a GitHub repository in which case you can omit directory creation and start InfluxDB 3 without providing it plugin folder path.

```shell
cd ~
mkdir influxdb3-plugins
```

2. Stop and Start InfluxDB 3 with Plugin Support if using plugins from local directory

2.1 Start InfluxDB with Processing Engine

Arguments:

- `--node-id`: Identifier for your InfluxDB node.
- `--object-store`: Type of object storage (e.g., memory, file, remote such as Amazon S3).
- `--data-dir`: Location of the directory where file baed object storage will reside.
- `--plugin-dir`: Directory containing local Python plugin scripts. Omit this argument if using plugins directly from GitHub.

**Example command**

```shell
influxdb3 serve \
  --node-id node0 \
  --object-store file \
  --data-dir ~/.influxdb/data \
  --plugin-dir ~/influxdb3-plugins
```

Upon running hte command, InfluxDB 3 should start on **localhost:8181** (default) and start printing logs in the terminal window without any error.

3. Create a Token using the CLI

Most `influxdb3` commands require an authentication token. Create an admin token using the following command and save it somewhere securely:

```shell
influxdb3 create token --admin
```

> [!IMPORTANT]
> Remember, tokens give full access to InfluxDB. It is recommended to secure your token string as it is not saved within the database thus can't be retreived if lost. You can save it as a local **INFLUXDB3_AUTH_TOKEN** enviornment variable or in a keystore.

4. Create Database & Verfify it using the cli. It can also be created automatically when line protocol data is first written to it.

```shell
influxdb3 create database my_awesome_db --token "YOUR_TOKEN_STRING"
influxdb3 show databases --token "YOUR_TOKEN_STRING"
```

5. Collect the historical weather data

   - The original workshop uses a pre-generated data file for 2024. To run the forecast for a more recent period, we will generate our own data.
   - The included `convert_lp.py` script will download one year of historical data for London from the [Open-Meteo API](https://open-meteo.com/en/docs) (from June 2024 to June 2025) and convert it to InfluxDB Line Protocol format.
   - Run the script to generate the data:
     ```shell
     python3 convert_lp.py
     ```
     This will create `london_weather_2024_2025.lp`.

6. Write Weather data for 2024-2025 for London using the CLI.

```shell
influxdb3 write --database my_awesome_db --file london_weather_2024_2025.lp --token 'YOUR_TOKEN_STRING'
```

7. Query Data using the CLI

```shell
influxdb3 query \
  --database my_awesome_db \
  --token 'YOUR_TOKEN_STRING' \
  "SHOW tables"
```

```shell
influxdb3 query \
  --database my_awesome_db \
  --token 'YOUR_TOKEN_STRING' \
  "SELECT * FROM london_weather_24_25 LIMIT 5"
```

### Plugin & Triggers

A plugin is a Python file containing a callback function with a specific signature that corresponds to the trigger type. The trigger defines and configures the plugin including providing any optional information using `--trigger-arguments` option. One or more trigger can be setup to run simultaneously either synchnorously (default behavior) or asynchnorously. Triggers can also be disabled or deleted.

#### Install Python dependencies (optional)

InfluxDB 3 provides a virtual enviornment for running python processing engine plugins. Those plugins are often dependent on python packages such as those from PyPy. They can be installed using influxdb3 cli for example `influxdb3 install package pandas --token YOUR_TOKEN_STRING'.

**Install Python Packages**

```sh
influxdb3 install package pandas neuralprophet plotly matplotlib --token 'YOUR_TOKEN_STRING'
```

#### Forecast Weather

We will create a Schedule plugin so it runs at a given schedule defined in the `trigger-spec`.

2.1 Create a plugin for Schedule trigger. [Plugin code](https://github.com/InfluxCommunity/WeatherForecasting/blob/main/forecast_london_weather.py))

2.2 Create a Schedule trigger that runs on any particular schedule.

Arguments:

- `--trigger-spec`: Specifies how often trigger activates (e.g. Run every minute, you can use cron syntax too).
- `--plugin-filename`: Name of the Python plugin file.
- `--database`: Database to use.
- '--token': YOUR_TOKEN_STRING
- `NAME_OF_TRIGGER`

```shell
influxdb3 create trigger \
  --trigger-spec "every:1m" \
  --plugin-filename "forecast_london_weather.py" \
  --token 'YOUR_TOKEN_STRING' \
  --database my_awesome_db \
  london_weather_forecast
```

2.3 Verify the Forecasted Data

Run the following command to query forecasted data written to the new table at given interval.

```shell
influxdb3 query \
  --database my_awesome_db \
  --token 'YOUR_TOKEN_STRING' \
  "SELECT * FROM forecast_weather_24_25"
```

3.  Disable Trigger & Stop InfluxDB3

To disable the plugin trigger:

```sh
influxdb3 disable trigger --database my_awesome_db london_weather_forecast --token 'YOUR_TOKEN_STRING'
```

Last step is to stop InfluxDB3 if you'd like. If InfluxDB 3 is running in the foreground, you can usually stop it by pressing `Ctrl+C` otherwise in a new terminal window execute the following commands to find and kill the InfluxDB 3 server:

```shell
ps aux | grep influxdb3
kill -9 <PID>
```

### Using Community created Plugin

You can directly use plugins from the official [InfluxData Plugins GitHub repository](https://github.com/influxdata/influxdb3_plugins) or other public repositories using the gh: prefix in the `--plugin-filename argument`

Example - using sample system_metrics schedule plugin

```shell
influxdb3 create trigger \
  --trigger-spec "every:1m" \
  --plugin-filename "gh:examples/schedule/system_metrics/system_metrics.py" \
  --database my_awesome_db \
  system_metrics
```

### Get Involved and Contribute!

We encourage you to contribute to the InfluxDB community and help make the Processing Engine even better!

- **Report Issues**: If you encounter any problems or have questions, please open an issue on the GitHub repository.
- **Share Your Plugins**: Create your own InfluxDB 3 plugins and share them with the community by contributing to the InfluxData Plugins Repository.
- **Join the Community**: Connect with other InfluxDB users and developers through our community channels on [Discord](https://discord.com/invite/vZe2w2Ds8B), [Slack](https://influxdata.com/slack) and website [forum](https://community.influxdata.com)
- **Star the Repository**: If you found this valuable, please star this repository.
