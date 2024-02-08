import openai
import os


def create_message(forecast_start_date, co2_values):
    class Message:
        def __init__(self, system, user):
            self.system = system
            self.user = user

    co2_values_str = ", ".join(str(value) for value in co2_values)
    system_template = (
        f"The following data is about the forecasted CO2 emissions starting from {forecast_start_date} "
        f"until the end of today with a step of 30 minutes. Each value represents the CO2 intensity in grams per kWh. "
        f"Based on the forecasted CO2 emissions data, we aim to provide simple and actionable energy usage advice."
        f"The CO2 emissions vary throughout the day, given pattern in data, when would be the optimal times for energy consumption to minimize environmental impact?"
        f"\n\nCO2 values are: {co2_values_str}"
    )

    user_template = "When is the best and worst time to use energy today?"

    system = system_template
    user = user_template

    m = Message(system=system, user=user)
    return m


# Example usage
msg = create_message(
    forecast_start_date="2024-02-08 22:00:00", co2_values=[10, 12, 13, 14, 15, 16]
)


messages = [
    {"role": "system", "content": msg.system}
    # {"role": "user", "content": msg.user},
]


def opt_gpt_summarise():
    # Ensure your API key is correctly set in your environment variables
    openai.api_key = os.getenv("OPENAI_API_KEY")

    # Construct the messages
    msg = create_message(
        forecast_start_date="2024-02-08 22:00:00", co2_values=[10, 12, 13, 14, 15, 16]
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
