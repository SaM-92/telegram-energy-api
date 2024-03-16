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
    """
    Categorizes forecasted CO2 emission periods into 'Low', 'Medium', and 'High' based on predefined thresholds, EU standards, and summarizes these periods.

    Args:
        df (pd.DataFrame): A DataFrame with a 'Value' column containing CO2 emission values.

    Returns:
        str: A summary text listing the start and end times of periods categorized into 'Low', 'Medium', and 'High' emissions.
    """
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
    """
    Normalizes CO2 values within a DataFrame and categorizes these values into 'Low', 'Medium', and 'High' segments based on quantiles. It then identifies and summarizes consecutive periods within each category.

    This function is designed for datasets with more than one entry, applying normalization to the CO2 emission values and using quantiles to determine thresholds for categorization. Each period's start and end times are summarized with corresponding categories.

    Args:
        df (pd.DataFrame): The DataFrame containing CO2 emission values under the 'Value' column.

    Returns:
        tuple: A summary string detailing categorized emission periods, and the modified DataFrame with added 'normalized', 'category', and 'group' columns.
    """

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
    """
    Constructs a detailed prompt for a GPT model, combining CO2 emissions forecast analysis with energy-saving suggestions.

    This function merges a date-specific CO2 emissions forecast, analysis against EU standards, and data-driven trends into a comprehensive prompt. It aims to guide the GPT model in generating actionable energy-saving recommendations based on the categorized CO2 emission trends for the specified date.

    Args:
        date (str): The date for which the CO2 emissions forecast and analysis are provided.
        eu_summary_text (str): A summary of the CO2 emissions analysis in relation to EU standards.
        quantile_summary_text (str): A summary of CO2 emissions based on data trends and quantile analysis.

    Returns:
        str: A complete prompt for the GPT model, structured to elicit energy-saving actions tailored to the emissions forecast and trend analysis.
    """
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
    """
    Summarizes or generates content based on a given prompt using the OpenAI GPT model.

    This function interacts with the OpenAI API to submit a prompt for completion or summarization, relying on the GPT-3.5-turbo model. It's designed to provide extended content generation, such as summarizing data analyses, generating reports, or offering recommendations.

    Args:
        prompt (str): The input text prompt to guide the GPT model's content generation.

    Returns:
        str: The text generated by the GPT model in response to the prompt, or an error message if the API call fails.
    """
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


def submit_energy_query_and_handle_response(carbon_data, user_query):
    """
    Generates a personalized advice prompt for an AI energy specialist based on carbon intensity data and user's question.

    Args:
        carbon_data (str): A string summarizing the carbon intensity data for the current day, formatted as "Low: HH:MM-HH:MM, Medium: HH:MM-HH:MM, High: HH:MM-HH:MM".
        user_query (str): The question asked by the user, seeking advice on energy consumption for a specific device or activity.

    Returns:
        str: The AI model's generated response, offering personalized advice on energy consumption based on the provided carbon intensity data and the user's question.
    """

    # carbon_data = "Low: 00:11-06:00, Medium: 06:01-18:00, High: 18:01-23:59"  # Example format for carbon intensity data
    structure = (
        "🌱 Carbon Intensity Periods Today: {carbon_data}\n"
        "🔋 Device Recommendation: Given the energy consumption characteristics of the devices mentioned (e.g., laundry machines, EV chargers, kettles), here is our advice:\n"
        "- 🟢 Low Carbon Period: This is the ideal time for using high-energy consumption devices. We strongly recommend scheduling usage during these periods to minimize your carbon footprint.\n"
        "- 🟡 Medium Carbon Period: If it is not feasible to use your devices during the low carbon period, medium periods are an acceptable alternative. However, preference should always be given to low carbon periods when possible.\n"
        "- 🔴 High Carbon Period: We recommend avoiding the use of energy-intensive devices during high carbon periods to prevent contributing to peak demand and higher carbon emissions.\n"
        "Our goal is to guide you towards making energy consumption choices that are both efficient and environmentally friendly."
    )

    msg_sys = (
        "You are an AI energy specialist. Your role is to provide users with advice on optimizing their energy consumption "
        "based on carbon intensity periods: low, medium, and high. Here is the carbon intensity summary for today: "
        f"{carbon_data}. "
        "Our recommendations are designed to align with sustainable energy usage practices:\n"
        "1. High-energy consumption devices are best used during low carbon periods.\n"
        "2. Medium carbon periods can be considered for less critical usage if low periods are not practical, but with a preference for low periods.\n"
        "3. High carbon periods should be avoided for energy-intensive devices to reduce environmental impact.\n"
        "Follow this guidance to make informed decisions about when to use your devices, aiming for the most sustainable outcomes."
        + structure
    )

    # Note: The `structure` variable is meant to show how the response should be formatted. In practice,
    # you would replace placeholders like `{carbon_data}` dynamically based on actual data and the specific user query.

    # Example user question for clarity
    msg_user = user_query  # "laundary?"

    # Example setup for calling the API with the structured system message and a user query
    messages = [
        {"role": "system", "content": msg_sys},
        {"role": "user", "content": msg_user},
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
    """
    Extracts a specific section from a larger text, focusing on energy-saving actions.

    This function searches for a predefined keyword within a given text to locate and extract the section dedicated to energy-saving actions. It handles variations in section formatting by looking for possible section end markers.

    Args:
        text (str): The complete text from which the energy-saving actions section will be extracted.

    Returns:
        str: The extracted text section that describes energy-saving actions, or an empty string if the section cannot be found.
    """
    start_keyword = "💡 Energy-Saving Actions"
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


def create_fuel_mix_prompt(date, fuel_mix_data, net_import_status):
    """
    Generates a structured prompt for reporting on fuel mix data, including net import or export status, tailored for a specific date.

    This function formats the fuel mix data and net import/export status into a comprehensive prompt. It aims to facilitate the generation of a report that summarizes the energy system's status over the last 24 hours, highlighting the contribution of each fuel source to the overall mix.

    Args:
        date (str): The date for which the fuel mix data is being reported.
        fuel_mix_data (pd.DataFrame or similar structure): The data containing fuel mix percentages and values for each energy source.
        net_import_status (str): The status indicating whether the region is 'importing' or 'exporting' energy.

    Returns:
        str: A detailed prompt including instructions for generating a report based on the fuel mix data and net import/export status.
    """
    # Preparing fuel mix data string
    # Correcting the list comprehension to match the data structure

    if net_import_status == "importing":
        fuel_mix_details = "\n".join(
            [
                f"- {fuel_mix_data['FieldName'][i]}: {fuel_mix_data['Value'][i]} MWh ({fuel_mix_data['Percentage'][i]:.1f}%)"
                for i in range(len(fuel_mix_data["FieldName"]))
            ]
        )
        prompt_text = (
            f"📅 Date: {date}\n"
            f"🔋 Fuel Mix Data (MWh & Percentage):\n\n"
            f"{fuel_mix_details}\n\n"
            "Based on the above data, write a short report about the status of the energy system over the last 24 hours. "
            "Please summarize the contribution of each fuel source to the overall mix and any notable trends. "
            "Use the following structure for your response, incorporating the specified emojis to highlight each fuel source:\n\n"
            "📋 Fuel Mix Status:\n"
            "- 🪨 Coal: [percentage]%\n"
            "- 🌬️ Gas: [percentage]%\n"
            "- ⚡ Net Import: [percentage]%\n"
            "- 🛢️ Other Fossil: [percentage]%\n"
            "- 🌿 Renewables: [percentage]%\n\n"
            "Note: Replace [percentage] with the actual percentages from the data. "
            "Avoid using asterisks (*) in your response and stick to the names and format provided."
        )
    elif net_import_status == "exporting":
        export_value = fuel_mix_data.loc[
            fuel_mix_data["FieldName"] == "Net Import", "Value"
        ].values[0]
        filtered_fuel_mix_data = fuel_mix_data[
            fuel_mix_data["FieldName"] != "Net Import"
        ]
        fuel_mix_details = "\n".join(
            [
                f"- {filtered_fuel_mix_data['FieldName'][idx]}: {filtered_fuel_mix_data['Value'][idx]} MWh ({filtered_fuel_mix_data['Percentage'][idx]:.1f}%)"
                for idx in filtered_fuel_mix_data.index  # Use the actual indices
            ]
        )

        prompt_text = (
            f"📅 Date: {date}\n"
            f"🔋 Fuel Mix Data (MWh & Percentage):\n\n"
            f"{fuel_mix_details}\n\n"
            "Based on the above data, write a short report about the status of the energy system over the last 24 hours. "
            "Please summarize the contribution of each fuel source to the overall mix and any notable trends. "
            "Use the following structure for your response, incorporating the specified emojis to highlight each fuel source:\n\n"
            "📋 Fuel Mix Status:\n"
            "- 🪨 Coal: [percentage]%\n"
            "- 🌬️ Gas: [percentage]%\n"
            "- 🛢️ Other Fossil: [percentage]%\n"
            "- 🌿 Renewables: [percentage]%\n\n"
            f"- ⚡ Ireland is currently exporting electricity to the UK, with the average export being {export_value} MWh over the last 24 hours. \n"
            "Note: Replace [percentage] with the actual percentages from the data. "
            "Avoid using asterisks (*) in your response and stick to the names and format provided."
        )

    return prompt_text


def create_wind_demand_prompt(demand_stats, wind_stats):
    """
    Generates a structured report summarizing the electricity demand and wind generation over the current day.

    This function creates a report detailing the average, minimum, and maximum electricity demand and wind generation,
    including the times those minimum and maximum values occurred. It highlights the contribution of wind generation to
    meeting the electricity demand, emphasizing the dynamics of the power system from the start of the current day until now.

    Args:
        demand_stats (dict): A dictionary containing statistics (mean, min, max, time of min, time of max) for electricity demand.
        wind_stats (dict): A dictionary containing statistics (mean, min, max, time of min, time of max) for wind generation.

    Returns:
        str: A formatted string that provides a comprehensive report on the electricity system's performance,
             specifically focusing on demand and wind generation, with an emphasis on wind's contribution to the electricity demand.
    """

    prompt_text = (
        "As of today, the performance of the electricity system is summarized as follows:\n\n"
        "- ⚡ **Electricity Demand**: The average demand was {average_demand} MW, with a minimum of {min_demand} MW recorded at {time_min_demand} "
        "and a maximum of {max_demand} MW observed at {time_max_demand}.\n"
        "- 🌬️ **Wind Generation**: In terms of wind generation, the average output stood at {average_wind} MW. "
        "The lowest generation reached {min_wind} MW at {time_min_wind}, while the peak generation was {max_wind} MW at {time_max_wind}.\n"
        "- 💨 **Wind's Contribution**: On average, wind generation has contributed {wind_percentage}% of the total electricity demand.\n\n"
        "This report highlights the power system's dynamics from the start of today until now, emphasizing the significant contribution of wind 🍃 to meeting the electricity demand."
    ).format(
        average_demand=round(demand_stats["Mean"], 2),
        min_demand=round(demand_stats["Min"], 2),
        time_min_demand=demand_stats["Time of Min"].strftime("%H:%M"),
        max_demand=round(demand_stats["Max"], 2),
        time_max_demand=demand_stats["Time of Max"].strftime("%H:%M"),
        average_wind=round(wind_stats["Mean"], 2),
        min_wind=round(wind_stats["Min"], 2),
        time_min_wind=wind_stats["Time of Min"].strftime("%H:%M"),
        max_wind=round(wind_stats["Max"], 2),
        time_max_wind=wind_stats["Time of Max"].strftime("%H:%M"),
        wind_percentage=round((wind_stats["Mean"] / demand_stats["Mean"]) * 100, 2),
    )

    return prompt_text


def generate_voice(text):
    """
    Generates an audio file from the given text using a specified voice and model via an external API.

    This function converts text into spoken audio, utilizing a voice synthesis API to produce the audio in a specified format. The function assumes access to an external service (e.g., ElevenLabs API) for voice synthesis.

    Args:
        text (str): The text to be converted into speech.

    Returns:
        bytes: The generated audio content in the specified format (e.g., MP3), ready to be played or saved. The return type and handling might vary based on the API's response.
    """
    return generate(
        text=text,
        voice="Callum",
        model="eleven_multilingual_v1",
        output_format="mp3_44100_128",
        api_key=ELEVEN_API_KEY,
    )
