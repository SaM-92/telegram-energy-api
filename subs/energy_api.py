import requests
import json
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import seaborn as sns
import matplotlib.dates as mdates
import numpy as np
from matplotlib.dates import DateFormatter, HourLocator


def eirgrid_api(area, region, start_time, end_time):
    """Fetches data from the EirGrid API for a specified area and region within a given time range.

    Args:
        area (str): The data area of interest. Valid values include "CO2Stats", "generationactual",
                    "co2emission", "co2intensity", "interconnection", "SnspAll", "frequency",
                    "demandactual", "windactual", "fuelMix".
        region (str): The region for which the data is requested. Options are "ROI" (Republic of Ireland),
                      "NI" (Northern Ireland), or "ALL" for both.
        start_time (str): The start time for the data request in 'YYYY-MM-DD' format.
        end_time (str): The end time for the data request in 'YYYY-MM-DD' format.

    Returns:
        pd.DataFrame: A DataFrame containing the requested data.
    """
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


# Function to round time to the nearest 15 minutes
def round_time(dt):
    """Rounds a datetime object's minutes to the nearest quarter hour.

    Args:
        dt (datetime): The datetime object to round.

    Returns:
        datetime: A new datetime object rounded to the nearest 15 minutes, with seconds and microseconds set to 0.
    """
    # Round minutes to the nearest 15
    new_minute = (dt.minute // 15) * 15
    return dt.replace(minute=new_minute, second=0, microsecond=0)


# Function to format date in a specific format
def format_date(dt):
    """Formats a datetime object into a specific string representation.

    Args:
        dt (datetime): The datetime object to format.

    Returns:
        str: The formatted date string in 'dd-mmm-yyyy+HH%3AMM' format
    """
    return dt.strftime("%d-%b-%Y").lower() + "+" + dt.strftime("%H%%3A%M")


def carbon_api_forecast():
    """
    Fetches CO2 emission forecast data for a specified region within a 24-hour period starting from the nearest half-hour mark.

    The function rounds down the current time to the nearest half-hour to align with data availability, sets the end time to the end of the current day, and then constructs and sends a request to the CO2 forecast API for the specified region. The response is processed into a pandas DataFrame, indexed by the effective time of each forecast.

    Returns:
        pd.DataFrame: A DataFrame containing CO2 emission forecast data, indexed by effective time, or None if an error occurs.
    """

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

    except Exception:
        # Return None or an error message to indicate failure
        return None


def carbon_api_intensity():
    """
    Fetches and analyzes CO2 intensity data from the previous day, rounded to the nearest 15 minutes.

    This function retrieves CO2 intensity data for the last 24 hours, processes the data to fill any gaps with interpolated values, and then calculates the mean, minimum, and maximum CO2 intensity values for the period.

    Returns:
        tuple: A tuple containing a dictionary with 'mean', 'min', and 'max' CO2 intensity values, and a pandas DataFrame with the recent CO2 intensity data indexed by effective time. Returns (None, None) in case of an error.
    """
    try:
        # Current date and time, rounded to the nearest 15 minutes
        now = round_time(datetime.datetime.now())

        # Start time (same time yesterday, rounded to the nearest 15 minutes)
        yesterday = now - datetime.timedelta(days=1)
        startDateTime = format_date(yesterday)

        # End time (current time, rounded to the nearest 15 minutes)
        endDateTime = format_date(now)

        # call API to get data
        df_carbon_intensity_day_before = eirgrid_api(
            "co2intensity", "ALL", startDateTime, endDateTime
        )

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

    except Exception:
        # Return None or an error message to indicate failure
        return None, None


def fuel_mix():
    """
    Retrieves and processes the fuel mix data for the current time, rounded to the nearest 15 minutes, compared to the same time yesterday.

    This function fetches the fuel mix data, maps raw field names to more descriptive names, calculates the percentage share of each fuel type in the total energy mix, and determines whether the region is net importing or exporting energy based on the fuel mix data.

    Returns:
        tuple: A tuple containing a pandas DataFrame with the fuel mix data, including the percentage share of each fuel type, and a string indicating if the region is 'importing' or 'exporting' energy. Returns (None, None) in case of an error.
    """
    try:
        # Current date and time, rounded to the nearest 15 minutes
        now = round_time(datetime.datetime.now())

        # Start time (same time yesterday, rounded to the nearest 15 minutes)
        yesterday = now - datetime.timedelta(days=1)
        startDateTime = format_date(yesterday)

        # End time (current time, rounded to the nearest 15 minutes)
        endDateTime = format_date(now)

        # call API to get fuel mix for current time
        fuel_mix_eirgrid = eirgrid_api("fuelMix", "ALL", startDateTime, startDateTime)

        descriptive_names = {
            "FUEL_COAL": "Coal",
            "FUEL_GAS": "Gas",
            "FUEL_NET_IMPORT": "Net Import",
            "FUEL_OTHER_FOSSIL": "Other Fossil",
            "FUEL_RENEW": "Renewables",
        }

        fuel_mix_eirgrid["FieldName"] = fuel_mix_eirgrid["FieldName"].map(
            descriptive_names
        )
        fuel_mix_eirgrid["ValueForPercentage"] = fuel_mix_eirgrid["Value"].apply(
            lambda x: max(x, 0)
        )
        total_for_percentage = sum(fuel_mix_eirgrid["ValueForPercentage"])
        percentages = [
            (value / total_for_percentage) * 100 if value > 0 else 0
            for value in fuel_mix_eirgrid["ValueForPercentage"]
        ]
        fuel_mix_eirgrid["Percentage"] = percentages
        if (
            fuel_mix_eirgrid.loc[
                fuel_mix_eirgrid["FieldName"] == "Net Import", "Value"
            ].values[0]
            < 0
        ):
            net_import = "exporting"
        else:
            net_import = "importing"
        return fuel_mix_eirgrid, net_import
    except:
        return None, None


def classify_status(value, min_val, max_val):
    """
    Categorizes a numeric value as 'low', 'medium', or 'high' based on its comparison with provided minimum and maximum values.

    Args:
        value (float): The numeric value to categorize.
        min_val (float): The minimum value of the range.
        max_val (float): The maximum value of the range.

    Returns:
        str: A string indicating the category of the value: 'low' if the value is less than the min_val, 'high' if it is greater than the max_val, and 'medium' if it falls within the range inclusive of the min_val and max_val.
    """
    if value < min_val:
        return "low"
    elif value > max_val:
        return "high"
    else:
        return "medium"


def status_classification(df, co2_stats_prior_day):
    """
    Classifies each CO2 emission value in the dataframe based on its comparison to the prior day's statistics and predefined EU standards.

    For each emission value, this function assigns a 'status_compared_to_yesterday' based on whether the value falls below, within, or above the range defined by the previous day's minimum and maximum CO2 values. It also assigns a 'status_compared_to_EU' based on a comparison to predefined minimum and maximum values representing EU standards.

    Args:
        df (pd.DataFrame): A DataFrame containing CO2 emission data with a column named 'Value'.
        co2_stats_prior_day (dict): A dictionary containing 'min' and 'max' keys with float values representing the previous day's CO2 emission range.

    Returns:
        pd.DataFrame: The modified DataFrame with two new columns: 'status_compared_to_yesterday' and 'status_compared_to_EU', each containing classification results ('low', 'medium', 'high') for the CO2 values.
    """
    df["status_compared_to_yesterday"] = df["Value"].apply(
        classify_status, args=(co2_stats_prior_day["min"], co2_stats_prior_day["max"])
    )
    df["status_compared_to_EU"] = df["Value"].apply(classify_status, args=(250, 500))

    return df


def co2_int_plot(df_):
    """
    Plots CO2 intensity data with comparisons to the previous day, EU standards, and value intensity using a color-coded bar chart.

    Args:
        df_ (pd.DataFrame): A DataFrame containing CO2 intensity data, with columns for 'EffectiveTime', 'Value', 'status_compared_to_yesterday', and 'status_compared_to_EU'.

    Returns:
        matplotlib.pyplot: The plotted figure.
    """
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
    """Plots the trend of CO2 intensity over time along with categorized intensity levels.

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


def today_time():
    """Generate start and end date and time strings for today's data reading.

    Returns:
        Tuple[str, str]: A tuple containing the start date and time string
        formatted as 'YYYY-MM-DD HH:MM:SS' and the end date and time string
        formatted as 'YYYY-MM-DD HH:MM:SS'.
    """
    now = round_time(datetime.datetime.now())

    # Start time of today
    startDateTime = format_date(
        datetime.datetime(now.year, now.month, now.day, 0, 0, 0)
    )

    # End time (current time, rounded to the nearest 15 minutes)
    endDateTime = format_date(now)

    return startDateTime, endDateTime


def process_data_frame(data_frame):
    """Process a DataFrame by converting timestamps, interpolating missing values,
    and selecting recent data.

    Args:
        data_frame (pd.DataFrame): DataFrame containing data.

    Returns:
        pd.DataFrame: Processed DataFrame with timestamps converted,
            missing values interpolated, and recent data selected.
    """
    # Convert 'EffectiveTime' to datetime and set as index
    data_frame["EffectiveTime"] = pd.to_datetime(
        data_frame["EffectiveTime"], format="%d-%b-%Y %H:%M:%S"
    )
    data_frame_indexed = data_frame.set_index("EffectiveTime")

    # Find the last valid index
    last_valid_index = data_frame_indexed["Value"].last_valid_index()

    # Select rows up to the row before the last NaN
    recent_data_frame = data_frame_indexed.loc[:last_valid_index]

    # Interpolate missing values
    recent_data_frame["Value"] = recent_data_frame["Value"].interpolate()

    return recent_data_frame


def wind_gen_cal():
    """This function retrives the generated wind for today

    Returns:
        pandas.DataFrame: DataFrame containing wind generation data for today.
            The DataFrame has the following columns:
                - EffectiveTime: Timestamps representing the time of measurement.
                - FieldName: Name of the wind generation field.
                - Region: Region for which the wind generation is recorded (ROI/NI/ALL).
                - Value: Wind generation values.
    """
    startDateTime, endDateTime = today_time()

    # Retrive data for generated wind for today
    wind_for_today = eirgrid_api("windactual", "ALL", startDateTime, endDateTime)

    # Return only the valid part of dataframe
    return process_data_frame(wind_for_today)


def actual_demand_cal():
    """Return total actual demand as a DataFrame.

    Returns:
        pd.DataFrame: DataFrame containing actual demand data for today.
            The DataFrame has the following columns:
                - EffectiveTime: Timestamps representing the time of measurement.
                - FieldName: Name of the demand field.
                - Region: Region for which the demand is recorded.
                - Value: Demand values.
    """
    startDateTime, endDateTime = today_time()

    # Retrive data for actual demand for today
    demand_for_today = eirgrid_api("demandactual", "ALL", startDateTime, endDateTime)

    # Return only the valid part of dataframe
    return process_data_frame(demand_for_today)


def calculate_stats_wind_demand(df):
    """
    Calculate mean, min, and max of the 'Value' column in the DataFrame,
    and identify the EffectiveTime for both min and max values.

    Args:
        df (pd.DataFrame): DataFrame with 'EffectiveTime' as index and a 'Value' column.

    Returns:
        dict: A dictionary with mean, min, max values, and the times at which min and max occurred.
    """
    mean_value = df["Value"].mean()
    min_value = df["Value"].min()
    max_value = df["Value"].max()

    # Find the time at which the min and max values occurred
    time_of_min = df["Value"].idxmin()
    time_of_max = df["Value"].idxmax()

    return {
        "Mean": mean_value,
        "Min": min_value,
        "Time of Min": time_of_min,
        "Max": max_value,
        "Time of Max": time_of_max,
    }


def generate_xaxis_ticks(start, end, interval_hours):
    """Generate x-axis tick marks from start to end time at given hour intervals.

    Args:
        start (pd.Timestamp): The start time of the data.
        end (pd.Timestamp): The end time of the data.
        interval_hours (float): The interval between ticks in hours.

    Returns:
        list: A list of `pd.Timestamp` objects representing the tick marks.
    """
    tick_marks = [start]
    current_tick = start
    while current_tick <= end:
        current_tick += pd.Timedelta(hours=interval_hours)
        tick_marks.append(current_tick)
    # Ensure the end time is included, adjusting the last tick if necessary
    if tick_marks[-1] > end:
        tick_marks[-1] = end
    return tick_marks


def area_plot_wind_demand(demand, wind):
    """Generates an area plot with dynamic x-axis intervals based on the data span,
    ensuring the x-axis ticks start from the data start point and end with the data endpoint,
    divided into rational intervals.

    Args:
        demand (pd.DataFrame): DataFrame containing energy demand data with a DateTimeIndex.
        wind (pd.DataFrame): DataFrame containing wind energy production data with a DateTimeIndex.

    Returns:
        matplotlib.pyplot: A plot object showing total energy demand and wind energy contribution over time with dynamically adjusted x-axis intervals.
    """
    # Increase font size
    plt.rcParams.update({"font.size": 14})

    plt.figure(figsize=(10, 6))
    sns.set_style("darkgrid", {"axes.facecolor": ".9"})

    combined = pd.DataFrame({"Demand": demand["Value"], "Wind": wind["Value"]}).dropna()

    start_time = combined.index.min()
    end_time = combined.index.max()

    # Calculate the total duration in hours to determine the interval
    duration_hours = (end_time - start_time).total_seconds() / 3600
    if duration_hours <= 2:
        interval_hours = 0.5  # 30 minutes
    elif duration_hours <= 12:
        interval_hours = 3  # Every 3 hours
    elif duration_hours <= 24:
        interval_hours = 4  # Every 4 hours
    else:
        interval_hours = 6  # Every 6 hours

    # Generate x-axis ticks
    ticks = generate_xaxis_ticks(start_time, end_time, interval_hours)

    # Adding fill_between with edgecolor and linewidth
    plt.fill_between(
        combined.index,
        combined["Demand"],
        label="Total Demand",
        color="skyblue",
        edgecolor="blue",
        linewidth=1.5,
    )
    plt.fill_between(
        combined.index,
        combined["Wind"],
        label="Wind Contribution",
        color="lightgreen",
        edgecolor="green",
        linewidth=1.5,
    )

    # Set the formatter for x-axis
    plt.gca().xaxis.set_major_formatter(DateFormatter("%H:%M"))

    # Set custom ticks
    plt.xticks(ticks, rotation=45)

    plt.title("Demand vs Wind Energy Contribution")
    plt.ylabel("Power (MW)")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    return plt
