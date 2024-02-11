import openai
import os
import datetime
from datetime import timedelta


def create_message(forecast_start_date, co2_values, user_name):
    class Message:
        def __init__(self, system, user):
            self.system = system
            self.user = user

    start_datetime = datetime.datetime.strptime(
        forecast_start_date, "%Y-%m-%d %H:%M:%S"
    )

    # Generate hours list based on the start_datetime and the length of co2_values
    hours = [
        (start_datetime + timedelta(minutes=30 * i)).strftime("%H:%M")
        for i in range(len(co2_values))
    ]

    time_with_co2 = ", ".join(
        f"{hour} (CO2: {value} g/kWh)" for hour, value in zip(hours, co2_values)
    )

    system_template = (
        f"Forecasted CO2 emissions data from {forecast_start_date}, updating every 30 minutes, is provided below. "
        f"Based on this, you are to give energy usage advice. Identify the most environmentally friendly hours "
        f"for energy consumption to minimize environmental impact. Use the format: Most environmental friendly hours hh:mm, "
        f"medium: hh:mm, and hours to avoid hh:mm. Consider high CO2 > 500, low CO2 < 250, and medium for values in between. "
        f"\n\nCO2 values and corresponding times are: {time_with_co2}"
        f"\n\nProvide advice on the optimal time periods for energy consumption, do not need to give CO2 values to users."
        f"\n\n start with greeting user {user_name}, based on time {forecast_start_date} "
    )

    user_template = "When are the best and worst time periods, on average, to use energy today from the environmental impact perspective in format of hour:minute?"

    system = system_template
    user = user_template

    m = Message(system=system, user=user)
    return m


def opt_gpt_summarise(df_):
    # Ensure your API key is correctly set in your environment variables
    openai.api_key = os.getenv("OPENAI_API_KEY")

    # Construct the messages
    msg = create_message(
        forecast_start_date=str(df_.index[0]),
        co2_values=df_.Value.values,
        user_name="Saeed",
    )

    messages = [
        {"role": "system", "content": msg.system}
        # {"role": "user", "content": msg.user},
    ]

    try:
        # Making the API call
        response = openai.chat.completions.create(
            model="gpt-3.5-turbo",  # or "gpt-3.5-turbo" based on your subscription
            messages=messages,
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
