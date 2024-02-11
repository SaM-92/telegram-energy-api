import openai
import os
import datetime
from datetime import timedelta
import numpy as np
import pandas as pd


def optimize_categorize_periods(df):
    # Define thresholds for CO2 emission categorization
    low_threshold, high_threshold = 250, 500

    # Categorize each timestamp
    df["category"] = pd.cut(
        df["Value"],
        bins=[-np.inf, low_threshold, high_threshold, np.inf],
        labels=["Low", "Medium", "High"],
    )

    # Find consecutive periods with the same category
    df["group"] = (df["category"] != df["category"].shift()).cumsum()

    # Initialize summary text
    summary_text = "Based on the forecasted CO2 emissions data for today, distinct periods are identified as:\n\n"

    # Initialize a dictionary to store concatenated periods for each category
    period_summary = {"Low": [], "Medium": [], "High": []}

    # Group by category and group to concatenate periods
    for category, group in df.groupby(["category", "group"]):
        start_time = group.index.min().strftime("%H:%M")
        end_time = group.index.max().strftime("%H:%M")
        period_str = (
            f"{start_time} to {end_time}" if start_time != end_time else f"{start_time}"
        )
        period_summary[category[0]].append(period_str)

    # Format the summary text for each category
    for category in ["Low", "Medium", "High"]:
        if period_summary[category]:
            periods = ", ".join(period_summary[category])
            summary_text += f"{category} CO2 Emission Periods: {periods}.\n"
        else:
            summary_text += (
                f"{category} CO2 Emission Periods: No specific periods identified.\n"
            )

    return summary_text


def find_optimized_relative_periods(df):
    # Normalize CO2 values to a 0-1 scale
    df["normalized"] = (df["Value"] - df["Value"].min()) / (
        df["Value"].max() - df["Value"].min()
    )

    # Define thresholds for relative categorization
    low_threshold = df["normalized"].quantile(0.33)
    high_threshold = df["normalized"].quantile(0.66)

    # Categorize each timestamp
    df["category"] = pd.cut(
        df["normalized"],
        bins=[-np.inf, low_threshold, high_threshold, np.inf],
        labels=["Low", "Medium", "High"],
    )

    # Find consecutive periods with the same category
    df["group"] = (df["category"] != df["category"].shift()).cumsum()

    # Prepare summary text
    summary_text = "Considering absolute CO2 emission values, distinct periods are identified as:\n\n"

    # Initialize a dictionary to store concatenated periods for each category
    period_summary = {"Low": [], "Medium": [], "High": []}

    # Group by category and group to concatenate periods
    for category, group in df.groupby(["category", "group"]):
        start_time = group.index.min().strftime("%H:%M")
        end_time = group.index.max().strftime("%H:%M")
        # For periods that start and end at the same time, just show one time
        period_str = (
            f"{start_time} to {end_time}" if start_time != end_time else f"{start_time}"
        )
        period_summary[category[0]].append(period_str)

    # Format the summary text for each category
    for category in ["Low", "Medium", "High"]:
        if period_summary[category]:
            periods = ", ".join(period_summary[category])
            summary_text += f"{category} CO2 Emission Period: {periods}.\n"
        else:
            summary_text += (
                f"{category} CO2 Emission Period: No specific periods identified.\n"
            )

    return summary_text


def create_combined_gpt_prompt(date, eu_summary_text, quantile_summary_text):
    prompt = (
        f"Based on the forecasted CO2 emissions data for {date}, here are two analyses:\n\n"
        "1. **EU Standards Analysis**:\n"
        f"{eu_summary_text}\n\n"
        "2. ** Data Analysis**:\n"
        f"{quantile_summary_text}\n\n"
        "Given these detailed analyses, please provide advice on how to align energy consumption to minimize environmental impact, "
        "First start with an overview based on the EU standards. Then, consider only nuanced day-to-day variations.  "
        "Highlight the optimal times for energy usage based on Data Analysis values, especially focusing on the absolute lowest and highest CO2 emission periods identified in the detailed analysis. "
        "The goal is to offer guidance that helps individuals effectively reduce their carbon footprint, "
        "using the insights from both the EU standards perspective and the data analysis. Make it short and cocise and give users time categories"
    )

    return prompt


def opt_gpt_summarise(prompt):
    # Ensure your API key is correctly set in your environment variables
    openai.api_key = os.getenv("OPENAI_API_KEY")

    # Construct the messages

    messages = [
        {"role": "system", "content": prompt}
        # {"role": "user", "content": msg.user},
    ]

    try:
        # Making the API call
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-3.5-turbo" based on your subscription
            messages=messages,
            temperature=1,
            max_tokens=600,  # Adjust the number of tokens as needed
            n=1,  # Number of completions to generate
            stop=None,  # Specify any stopping criteria if needed
        )

        # Extracting the response
        # generated_text = response.choices[0].message['content'].strip()
        generated_text = response.choices[0].message.content.strip()

        return generated_text
    except Exception as e:
        return str(e)
