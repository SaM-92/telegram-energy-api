import requests, json
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
from io import BytesIO


def carbon_api_forecast():
    # data is availble every 30 minutes, so we need to start at the nearest half-hour
    def round_down_time(dt):
        # Round down to the nearest half-ho/ur
        new_minute = 30 if dt.minute >= 30 else 0
        return dt.replace(minute=new_minute, second=0, microsecond=0)

    # Function to create the API URL based on the start and end datetimes and the region
    def create_url(start_datetime, end_datetime, region):
        start_str = start_datetime.strftime("%Y%m%d%H%M")
        end_str = end_datetime.strftime("%Y%m%d%H%M")
        url = f"https://www.co2.smartgriddashboard.com/api/co2_fc/{start_str}/{end_str}/{region}"
        return url

    # Current date and time
    now = datetime.datetime.now()
    # Round down to the nearest half-hour
    start_time = round_down_time(now)
    # For end time, let's use 24 hours from now
    end_time = now.replace(
        hour=23, minute=59, second=59, microsecond=0
    )  # now + timedelta(days=1)

    # Define the region
    region = ["ROI", "NI", "ALL"]

    # Create the URL
    api_url = create_url(start_time, end_time, region[2])
    response = requests.get(api_url)
    Rs = response.json()

    df_carbon_forecast = pd.DataFrame(Rs["Rows"])

    # Convert 'EffectiveTime' to datetime and set as index
    df_carbon_forecast["EffectiveTime"] = pd.to_datetime(
        df_carbon_forecast["EffectiveTime"], format="%d-%b-%Y %H:%M:%S"
    )
    df_carbon_forecast_indexed = df_carbon_forecast.set_index("EffectiveTime")
    return df_carbon_forecast_indexed


def carbon_api_intensity():
    # Function to round time to the nearest 15 minutes
    def round_time(dt):
        # Round minutes to the nearest 15
        new_minute = (dt.minute // 15) * 15
        return dt.replace(minute=new_minute, second=0, microsecond=0)

    # Function to format date in your specific format
    def format_date(dt):
        return dt.strftime("%d-%b-%Y").lower() + "+" + dt.strftime("%H%%3A%M")

    # Current date and time, rounded to the nearest 15 minutes
    now = round_time(datetime.datetime.now())

    # Start time (same time yesterday, rounded to the nearest 15 minutes)
    yesterday = now - datetime.timedelta(days=1)
    startDateTime = format_date(yesterday)

    # End time (current time, rounded to the nearest 15 minutes)
    endDateTime = format_date(now)

    area = [
        "CO2Stats",
        "generationactual",
        "co2emission",
        "co2intensity",
        "interconnection",
        "SnspAll",
        "frequency",
        "demandactual",
        "windactual",
    ]
    region = ["ROI", "NI", "ALL"]
    Rows = []

    url = f"http://smartgriddashboard.eirgrid.com/DashboardService.svc/data?area={area[3]}&region={region[2]}&datefrom={startDateTime}&dateto={endDateTime}"
    response = requests.get(url)
    Rs = json.loads(response.text)["Rows"]
    for row in Rs:
        Rows.append(row)

    df_carbon_intensity_day_before = pd.DataFrame(Rows)

    # Convert 'EffectiveTime' to datetime and set as index
    df_carbon_intensity_day_before["EffectiveTime"] = pd.to_datetime(
        df_carbon_intensity_day_before["EffectiveTime"], format="%d-%b-%Y %H:%M:%S"
    )
    df_carbon_intensity_indexed = df_carbon_intensity_day_before.set_index(
        "EffectiveTime"
    )

    last_value_index_co_intensity = df_carbon_intensity_indexed[
        "Value"
    ].last_valid_index()

    # Select rows up to the row before the last NaN
    df_carbon_intensity_recent = df_carbon_intensity_indexed.loc[
        :last_value_index_co_intensity
    ]

    df_carbon_intensity_recent["Value"] = df_carbon_intensity_recent[
        "Value"
    ].interpolate()

    # Calculate mean, min, and max
    mean_val = df_carbon_intensity_recent["Value"].mean()
    min_val = df_carbon_intensity_recent["Value"].min()
    max_val = df_carbon_intensity_recent["Value"].max()

    # Create a dictionary with these values
    co2_stats_prior_day = {"mean": mean_val, "min": min_val, "max": max_val}

    return co2_stats_prior_day, df_carbon_intensity_recent


def classify_status(value, min_val, max_val):
    if value < min_val:
        return "low"
    elif value > max_val:
        return "high"
    else:
        return "medium"


def status_classification(df, co2_stats_prior_day):
    df["status_compared_to_yesterday"] = df["Value"].apply(
        classify_status, args=(co2_stats_prior_day["min"], co2_stats_prior_day["max"])
    )
    df["status_compared_to_EU"] = df["Value"].apply(classify_status, args=(250, 500))

    return df


def co2_int_plot(df_):
    # Assuming df_carbon_forecast_indexed is your DataFrame
    df = df_.reset_index(inplace=False)
    df["EffectiveTime"] = pd.to_datetime(df["EffectiveTime"])
    df.sort_values("EffectiveTime", inplace=True)

    # Map status to colors
    color_map = {"low": "green", "medium": "orange", "high": "red"}

    # Create a custom colormap from green to red
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "custom_green_red", ["green", "red"]
    )

    # Normalize the "Value" data to [0, 1]
    norm = mcolors.Normalize(vmin=100, vmax=600)

    # Create figure and axes
    fig, ax = plt.subplots(
        figsize=(8, 6)
    )  # Adjusted figure size for additional bars and color bar

    # Plot a bar for each row in the DataFrame.
    for i, (index, row) in enumerate(df.iterrows()):
        ax.barh(
            i,
            1,
            color=color_map[row["status_compared_to_yesterday"]],
            edgecolor="white",
        )
        ax.barh(
            i,
            1,
            left=1,
            color=color_map[row["status_compared_to_EU"]],
            edgecolor="white",
        )
        # Use the custom colormap and normalized values to determine the color for the "Value" column.
        ax.barh(i, 1, left=2, color=cmap(norm(row["Value"])), edgecolor="white")

    # Customize plot appearance.
    ax.set_facecolor("black")
    fig.patch.set_facecolor("black")
    ax.tick_params(axis="x", colors="white")  # X-axis ticks color.
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("white")
    ax.spines["bottom"].set_color("white")

    # Remove x-axis ticks.
    ax.xaxis.set_ticks([])

    # Set y-axis labels.
    ax.set_yticks(range(len(df)))
    ax.set_yticklabels(
        df["EffectiveTime"].dt.strftime("%Y-%m-%d %H:%M"), color="white", fontsize=8
    )

    plt.tight_layout()

    ax.set_title(
        "CO2 Intensity Forecast for the Remaining Hours of Today", color="white"
    )
    ax.set_xticks([0.5, 1.5, 2.5])
    ax.set_xticklabels(
        ["Compared to \n Yesterday", "Compared to \n EU Standards", "Value\nIntensity"],
        color="white",
    )

    # Create and customize the color bar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, orientation="vertical", label="Value Intensity")
    cbar.set_ticks([norm.vmin, norm.vmax])  # Set ticks to the min and max of the data
    cbar.set_ticklabels(
        [100, 600], color="white"
    )  # Format min and max values as labels

  return plt 