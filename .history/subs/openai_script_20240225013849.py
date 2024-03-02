import openai
import os
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from elevenlabs import generate

# Load environment variables from .env file
load_dotenv()
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ELEVEN_API_KEY = os.environ.get("ELEVEN_API_KEY")


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
    # summary_text = "Based on the forecasted CO2 emissions data for today, distinct periods are identified as:\n\n"
    summary_text = ""
    # Initialize a dictionary to store concatenated periods for each category
    period_summary = {"Low": [], "Medium": [], "High": []}

    # Define emojis for each category
    emoji_dict = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}

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
            summary_text += f"- {emoji_dict[category]} {category} Emission: {periods}\n"
        else:
            summary_text += f"- {emoji_dict[category]} {category} Emission: No specific periods identified.\n"

    return summary_text


def find_optimized_relative_periods(df):

    if len(df) > 1:
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
        # summary_text = "Considering absolute CO2 emission values, determined by data trends, distinct periods are identified as:\n\n"
        summary_text = ""

        # Initialize a dictionary to store concatenated periods for each category
        period_summary = {"Low": [], "Medium": [], "High": []}

        # Define emojis for each category
        emoji_dict = {"Low": "🟢", "Medium": "🟡", "High": "🔴"}

        # Group by category and group to concatenate periods
        for (category, group), data in df.groupby(["category", "group"]):
            start_time = data.index.min().strftime("%H:%M")
            end_time = data.index.max().strftime("%H:%M")
            # For periods that start and end at the same time, just show one time
            period_str = (
                f"{start_time} to {end_time}" if start_time != end_time else start_time
            )
            period_summary[category].append(period_str)

        # Format the summary text for each category
        for category in ["Low", "Medium", "High"]:
            if period_summary[category]:
                periods = ", ".join(period_summary[category])
                summary_text += (
                    f"- {emoji_dict[category]} {category} Emission: {periods}\n"
                )
            else:
                summary_text += f"- {emoji_dict[category]} {category} Emission: No specific periods identified.\n"
    else:
        summary_text = (
            "Sorry, we do not have enough data to process data trend analysis."
        )

    return summary_text, df


def create_combined_gpt_prompt(date, eu_summary_text, quantile_summary_text):
    prompt_data = (
        f"🌍 CO2 Emissions Forecast for {date}:\n\n"
        "1. **EU Standards Analysis** 🇪🇺 :\n"
        f"{eu_summary_text}\n\n"
        "2. **Data Trend**: 🔍\n"
        f"{quantile_summary_text}\n\n"
    )

    structure_example = (
        "📋 CO2 Emission Brief & Energy Efficiency Guide:\n\n"
        "- 🇪🇺 EU Standards Forecast: ONLY report it\n"
        "- 🔍 Data Trend Schedule: ONLY report it\n"
        f"- 💡 Energy-Saving Actions: Give an example of energy-saving actions for each category of CO2 emission trend, "
        f"considering the current season ({date}). Examples should cover:\n"
        "   -🟢 Low Emission Periods: [Your Example Here]\n"
        "   -🟡 Medium Emission Periods: [Your Example Here]\n"
        "   -🔴High Emission Periods: [Your Example Here]\n"
    )

    prompt_text = (
        f"📊 Given the CO2 emission forecasts and detailed analysis for {date}, let's explore how we can adjust our "
        "energy consumption to minimize our environmental impact. Our aim is to provide straightforward and practical "
        "advice, utilizing specific data trends.\n\n"
        f"{prompt_data}"
        "💡 In periods of low emissions, feel free to use energy-intensive appliances without much concern for reduction.\n\n"
        f"👉 Please use the following format for your response and avoid using * in your response: \n\n {structure_example}\n"
    )

    return prompt_text


def opt_gpt_summarise(prompt):
    # Ensure your API key is correctly set in your environment variables
    openai.api_key = OPENAI_API_KEY  # os.getenv("OPENAI_API_KEY")

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


def get_energy_actions(text):
    start_keyword = "- 💡 Energy-Saving Actions:"
    end_keywords = [
        "📋",
        "- 🇪🇺",
        "- 🔍",
        "- 💡",
    ]  # Add possible start of next sections if format varies
    end_keyword = next(
        (kw for kw in end_keywords if kw in text[text.find(start_keyword) :]),
        None,
    )

    # Find start and end positions
    start_pos = text.find(start_keyword)
    end_pos = text.find(end_keyword, start_pos + 1) if end_keyword else len(text)

    # Extract the section
    energy_saving_actions = text[start_pos:end_pos].strip()
    return energy_saving_actions


def generate_voice(text):
    return generate(
        text=text,
        voice="Callum",
        model="eleven_multilingual_v1",
        output_format="mp3_44100_128",
        api_key=ELEVEN_API_KEY,
    )
