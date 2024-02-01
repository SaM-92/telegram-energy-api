import requests, json
import pandas as pd
import datetime


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