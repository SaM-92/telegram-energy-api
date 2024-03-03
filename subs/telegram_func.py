from telegram import Update
from telegram.ext import (
    ContextTypes,
)
from subs.energy_api import *
from subs.openai_script import *
from io import BytesIO


async def send_co2_intensity_plot(
    update: Update, context: ContextTypes.DEFAULT_TYPE, df_
):
    """
    Asynchronously sends a CO2 intensity trend plot to a chat in Telegram.

    This function generates a visualization of today's CO2 emission trends and intensity levels, highlighting expected changes throughout the day. It then sends this visualization to a specified chat, along with a caption explaining the plot.

    Args:
        update (Update): The update object representing the incoming update.
        context (ContextTypes.DEFAULT_TYPE): The context object provided by the python-telegram-bot library, used for sending replies.
        df_ (pd.DataFrame): A DataFrame containing the CO2 intensity data to be visualized.

    """

    caption_text = (
        "🎨 This visualisation presents today's CO2 emission trends and intensity levels, "
        "emphasizing expected changes over the course of the day. The blue line delineates the emission trend, accompanied by "
        "color-coded circles indicating value intensity at specific points. Additionally, colored circles positioned at the bottom "
        "of the image correspond to intensity levels at 30-minute intervals—green signifies low intensity, orange denotes medium, "
        "and red indicates high intensity. This guide is designed to assist in planning energy usage with environmental impact in mind."
    )

    chat_id = update.effective_chat.id

    # Call the function to generate the plot
    plt = co2_plot_trend(df_)

    # Save the plot to a BytesIO buffer
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()  # Make sure to close the plot to free up memory

    # Send the photo
    await context.bot.send_photo(chat_id=chat_id, photo=buf, caption=caption_text)


def carbon_forecast_intensity_prompts():
    """
    Generates prompts and data for CO2 intensity forecasts, including analysis and visualization preparation.

    Fetches CO2 forecast data, performs intensity analysis, categorizes emission periods, and prepares data for generating GPT prompts and visualizations. If any data retrieval or processing step fails, it returns None for all output values.

    Returns:
        tuple: Contains the today's date, EU standards summary text, quantile-based summary text, and a DataFrame prepared for trend analysis and visualization, or None values if data retrieval fails.
    """
    df_carbon_forecast_indexed = None
    co2_stats_prior_day = None
    df_carbon_intensity_recent = None
    # user_first_name
    # Proceed with your existing logic here...
    df_carbon_forecast_indexed = carbon_api_forecast()
    co2_stats_prior_day, df_carbon_intensity_recent = carbon_api_intensity()
    # Check if either API call failed
    if (
        df_carbon_forecast_indexed is None
        or co2_stats_prior_day is None
        or df_carbon_intensity_recent is None
    ):
        return None, None, None, None

    # Exit the function early since we can't proceed without the data
    else:
        # df_carbon_forecast_indexed = carbon_api_forecast()
        # co2_stats_prior_day, df_carbon_intensity_recent = carbon_api_intensity()
        df_ = status_classification(df_carbon_forecast_indexed, co2_stats_prior_day)
        # data analysis & adding category per hours
        summary_text, df_with_trend = find_optimized_relative_periods(df_)
        today_date = df_with_trend.index[0].strftime("%d/%m/%Y")
        eu_summary_text = optimize_categorize_periods(df_with_trend)
        quantile_summary_text, df_with_trend_ = find_optimized_relative_periods(
            df_with_trend
        )  # Generate this based on your DataFrame
        return today_date, eu_summary_text, quantile_summary_text, df_with_trend


async def telegram_carbon_intensity(update, context, user_first_name):
    """
    Sends CO2 intensity data and energy-saving tips to the user via a Telegram bot.

    This async function retrieves CO2 intensity forecasts and generates recommendations based on these forecasts. It notifies the user if data cannot be fetched and provides energy-saving tips and visual data representations when available.

    Args:
        update (telegram.Update): Contains incoming update details.
        context (telegram.ext.CallbackContext): Holds methods for bot interactions.
        user_first_name (str): User's first name for personalized messaging.

    Returns:
        None: Directly sends messages and data visualizations to the user.
    """

    today_date, eu_summary_text, quantile_summary_text, df_with_trend = (
        carbon_forecast_intensity_prompts()
    )
    if (
        eu_summary_text is None
        or quantile_summary_text is None
        or df_with_trend is None
    ):
        await update.message.reply_html(
            f"Sorry, {user_first_name} 😔. We're currently unable to retrieve the necessary data due to issues with the <a href='https://www.smartgriddashboard.com'>EirGrid website</a> 🌐. Please try again later. We appreciate your understanding 🙏."
        )
        return  # Exit the function early since we can't proceed without the data
    else:

        prompt = create_combined_gpt_prompt(
            today_date, eu_summary_text, quantile_summary_text
        )

        # get generated prompt
        gpt_recom = opt_gpt_summarise(prompt)
        await update.message.reply_text(gpt_recom)
        if len(df_with_trend) > 1:
            await send_co2_intensity_plot(update, context, df_with_trend)
        # slice the energy saving actions part
        energy_saving_actions = get_energy_actions(gpt_recom)
        """ 
        # I stopped  voice gen due to cost issues
        audio_msg = generate_voice(energy_saving_actions)
        await context.bot.send_voice(
            update.effective_chat.id,
            audio_msg,
            caption="Here's your energy-saving tips 🎙️",
        )
        del audio_msg
        """


async def telegram_personalised_handler(update, context, user_first_name, user_query):

    today_date, eu_summary_text, quantile_summary_text, df_with_trend = (
        carbon_forecast_intensity_prompts()
    )
    if (
        eu_summary_text is None
        or quantile_summary_text is None
        or df_with_trend is None
    ):
        await update.message.reply_html(
            f"Sorry, {user_first_name} 😔. We're currently unable to retrieve the necessary data due to issues with the <a href='https://www.smartgriddashboard.com'>EirGrid website</a> 🌐. Please try again later. We appreciate your understanding 🙏."
        )
        return  # Exit the function early since we can't proceed without the data
    else:

        response_of_gpt = submit_energy_query_and_handle_response(
            quantile_summary_text, user_query
        )

        return response_of_gpt


async def pie_chart_fuel_mix(update, context, df, net_import_status, current_time):
    """
    Generates and sends a pie chart visualizing the fuel mix for energy generation, adjusted by the net import status, to a Telegram chat.

    Args:
        update (telegram.Update): The update object, containing information about the incoming update.
        context (telegram.ext.CallbackContext): The context object, providing access to Telegram's bot methods for responding.
        df (pd.DataFrame): A DataFrame containing the fuel mix data with columns 'FieldName' and 'Percentage'.
        net_import_status (str): A string indicating whether the region is 'importing' or 'exporting' energy, which affects the data representation.
        current_time (str): A string representing the current time or the time frame of the data being visualized, included in the chart's title.

    Returns:
        None: The function sends a pie chart directly to the Telegram chat and does not return any value.
    """

    # Adjusting colors to be less vibrant (more pastel-like)
    pastel_colors = {
        "Coal": "#3B3434",  # Coal - less vibrant gray
        "Gas": "#FF5733",  # Gas - less vibrant orange
        "Net Import": "#8648BD",  # Net Import - less vibrant blue
        "Other Fossil": "#F08080",  # Other Fossil - less vibrant red
        "Renewables": "#48BD5F",  # Renewables - less vibrant green
    }
    # print(fuel_mix_eirgrid)
    # Mapping the pastel colors to the dataframe's FieldName
    pastel_pie_colors = [pastel_colors[field] for field in df["FieldName"]]
    # Filter df based on net_import_status
    if net_import_status == "importing":
        pie_data = df
    elif net_import_status == "exporting":
        pie_data = df[df["FieldName"] != "Net Import"]
        # Update pastel_pie_colors to match the filtered data
        pastel_pie_colors = [pastel_colors[field] for field in pie_data["FieldName"]]

    # Generate custom_labels from the (potentially filtered) pie_data
    custom_labels = [
        f'{row["FieldName"]}\n({row["Percentage"]:.1f}%)'
        for index, row in pie_data.iterrows()
    ]
    plt.figure(figsize=(7, 7))
    plt.pie(
        pie_data["Percentage"],
        labels=custom_labels,
        startangle=140,
        colors=pastel_pie_colors,
        wedgeprops=dict(width=0.3),
    )
    plt.title(f"Fuel Mix (MWh) Distribution (%)- {current_time}")
    plt.axis("equal")  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.tight_layout()
    # plt.show()
    # Save the plot to a BytesIO buffer
    buf = BytesIO()
    plt.savefig(buf, format="png")
    buf.seek(0)
    plt.close()  # Make sure to close the plot to free up memory
    caption_text = "📊 Explore the diversity of Ireland energy sources: from the strength of 🌿 renewables to the power of 🌬️ gas and 🪨 coal, each plays a crucial role in our energy mix. A colorful snapshot of how we power our world!"
    # Send the photo
    chat_id = update.effective_chat.id
    await context.bot.send_photo(chat_id=chat_id, photo=buf, caption=caption_text)


async def telegram_fuel_mix(update, context, user_first_name):
    """
    Asynchronously responds to a Telegram command by providing information about the current fuel mix and net import status, alongside a visual pie chart.

    This function fetches the current fuel mix and net import status, generates a textual summary using GPT-based summarization, and sends this summary to the user. It also generates and sends a pie chart visualizing the fuel mix. If data retrieval fails, the user is informed via a message containing a link for further assistance.

    Args:
        update (telegram.Update): Object representing an incoming update.
        context (telegram.ext.CallbackContext): Context object for sending replies.
        user_first_name (str): The first name of the user, used to personalize the response.

    Returns:
        None: This function sends messages directly to the Telegram chat and does not return any value.
    """
    fuel_mix_eirgrid = None
    net_import_status = None

    fuel_mix_eirgrid, net_import_status = fuel_mix()

    if fuel_mix_eirgrid is None or net_import_status is None:
        await update.message.reply_html(
            f"Sorry, {user_first_name} 😔. We're currently unable to retrieve the necessary data due to issues with the <a href='https://www.smartgriddashboard.com'>EirGrid website</a> 🌐. Please try again later. We appreciate your understanding 🙏."
        )
        return
    else:

        now = round_time(datetime.datetime.now())

        promopt_for_fuel_mix = create_fuel_mix_prompt(
            now, fuel_mix_eirgrid, net_import_status
        )
        fuel_mix_response_from_gpt = opt_gpt_summarise(promopt_for_fuel_mix)

        await update.message.reply_text(fuel_mix_response_from_gpt)
        await pie_chart_fuel_mix(
            update, context, fuel_mix_eirgrid, net_import_status, now
        )
        """ 
        # I stopped  voice gen due to cost issues

        audio_msg = generate_voice(fuel_mix_response_from_gpt)

        await context.bot.send_voice(
            update.effective_chat.id,
            audio_msg,
            caption="Here's fuel mix summary 🎙️",
        )
        del audio_msg
        """
