import requests, json
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
import matplotlib.dates as mdates
import numpy as np
from io import BytesIO


def eirgrid_api(area, region, start_time, end_time):
    #     area = [
    #     "CO2Stats",
    #     "generationactual",
    #     "co2emission",
    #     "co2intensity",
    #     "interconnection",
    #     "SnspAll",
    #     "frequency",
    #     "demandactual",
    #     "windactual",
    #     "fuelMix"
    # ]
    #     region = ["ROI", "NI", "ALL"]
    Rows = []
    url = f"http://smartgriddashboard.eirgrid.com/DashboardService.svc/data?area={area}&region={region}&datefrom={start_time}&dateto={end_time}"
    response = requests.get(url)
    Rs = json.loads(response.text)["Rows"]
    for row in Rs:
        Rows.append(row)

    return pd.DataFrame(Rows)


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

    try:
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

        # Make a request with SSL verification disabled due to existing issue from EirGrid
        response = requests.get(api_url, verify=False)

        Rs = response.json()

        df_carbon_forecast = pd.DataFrame(Rs["Rows"])

        # Convert 'EffectiveTime' to datetime and set as index
        df_carbon_forecast["EffectiveTime"] = pd.to_datetime(
            df_carbon_forecast["EffectiveTime"], format="%d-%b-%Y %H:%M:%S"
        )
        df_carbon_forecast_indexed = df_carbon_forecast.set_index("EffectiveTime")

        last_value_index_co_forecast = df_carbon_forecast_indexed[
            "Value"
        ].last_valid_index()

        # Select rows up to the row before the last NaN
        df_carbon_forecast_indexed = df_carbon_forecast_indexed.loc[
            :last_value_index_co_forecast
        ]

        return df_carbon_forecast_indexed

    except Exception as e:
        # Return None or an error message to indicate failure
        return None


def carbon_api_intensity():
    # Function to round time to the nearest 15 minutes
    def round_time(dt):
        # Round minutes to the nearest 15
        new_minute = (dt.minute // 15) * 15
        return dt.replace(minute=new_minute, second=0, microsecond=0)

    # Function to format date in your specific format
    def format_date(dt):
        return dt.strftime("%d-%b-%Y").lower() + "+" + dt.strftime("%H%%3A%M")

    try:
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

    except Exception as e:
        # Return None or an error message to indicate failure
        return None, None


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
    plt.tight_layout()
    return plt


def co2_plot_trend(df_):
    """
    Plots the trend of CO2 intensity over time along with categorized intensity levels.

    This function takes a DataFrame containing CO2 emission data, including timestamps
    and values, and plots a trend line of emissions. It overlays this with a scatter
    plot indicating the intensity of emissions at different times, categorized by color.
    The x-axis is dynamically adjusted to fit the data's time range.

    Parameters:
    - df_ : pandas.DataFrame
        The input DataFrame must contain columns for timestamps ('EffectiveTime'),
        CO2 values ('Value'), a category column ('category'), and normalized values ('normalized').

    Returns:
    - None: Displays a matplotlib plot.
    """
    # Set plot style
    sns.set_style("darkgrid", {"axes.facecolor": ".9"})

    # Prepare data: reset index, convert 'EffectiveTime' to datetime, and sort
    df = df_.reset_index(inplace=False)
    df["EffectiveTime"] = pd.to_datetime(df["EffectiveTime"])
    df.sort_values("EffectiveTime", inplace=True)
    df.set_index("EffectiveTime", inplace=True)  # Set 'EffectiveTime' as index

    # Format today's date for the plot title
    today_date = datetime.datetime.now().strftime("%A %d/%m/%Y")

    # Set up color mapping for CO2 values
    norm = plt.Normalize(100, 600)  # Normalization for value intensity
    cmap = plt.get_cmap("RdYlGn_r")  # Colormap: green to red for low to high intensity

    # Create the plot with specified figure size
    fig, ax = plt.subplots(figsize=(6, 5))

    # Plot the CO2 value trend line
    ax.plot(df.index, df["Value"], color="b", alpha=0.5, linewidth=2)

    # Overlay scatter plot for CO2 value intensity
    sc = ax.scatter(
        df.index, df["Value"], c=df["Value"], cmap=cmap, norm=norm, edgecolor="none"
    )

    # Dynamically adjust x-axis ticks based on data range
    total_duration_hours = (df.index.max() - df.index.min()).total_seconds() / 3600
    interval = max(
        1, round(total_duration_hours / 24)
    )  # Adjust interval based on data span
    ax.xaxis.set_major_locator(mdates.HourLocator(interval=interval))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
    plt.setp(
        ax.get_xticklabels(), rotation=45, ha="right"
    )  # Rotate x-axis labels for readability

    # Customize the colorbar to represent CO2 intensity values
    cbar = fig.colorbar(sc, ax=ax, orientation="vertical", label="Value intensity")
    cbar.set_ticks(np.arange(100, 600, 165))
    cbar.set_ticklabels(["100", "300", "500", "600"])

    # Create a twin y-axis for plotting normalized values by category
    ax2 = ax.twinx()
    ax2.set_yticks([])  # Remove y-ticks for the twin axis

    # Plot categorized CO2 intensity levels
    colors = {"Low": "green", "Medium": "orange", "High": "red"}
    for category, color in colors.items():
        df_cat = df[df["category"] == category]
        ax2.scatter(
            df_cat.index,
            df_cat["normalized"],
            color=color,
            label=category,
            alpha=0.7,
            edgecolor="black",
        )

    ax2.set_ylim([-0.2, 5])  # Adjust y-axis limits for categorized data

    # Final plot adjustments
    ax.set_ylim([100, df["Value"].max() + 100])  # Adjust y-axis limits for CO2 values
    ax.set_ylabel("tCO2/hr")  # Set y-axis label
    ax.set_title(f"CO2 intensity forecast over time for {today_date}")  # Set plot title
    ax2.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.2),
        ncol=4,
        frameon=True,
        edgecolor="black",
        title="Intensity levels determined by data trends",
    )  # Add legend for categories

    plt.tight_layout()  # Adjust layout to make room for plot elements
    return plt
