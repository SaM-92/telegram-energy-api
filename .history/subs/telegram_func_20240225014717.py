import logging
import os
import pandas as pd
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CallbackContext,
)
from subs.energy_api import *
from subs.openai_script import *


async def send_co2_intensity_plot(
    update: Update, context: ContextTypes.DEFAULT_TYPE, df_
):

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


async def telegram_carbon_intensity(update, context, user_first_name):
    df_carbon_forecast_indexed = None
    co2_stats_prior_day = None
    df_carbon_intensity_recent = None
    user_first_name
    # Proceed with your existing logic here...
    df_carbon_forecast_indexed = carbon_api_forecast()
    co2_stats_prior_day, df_carbon_intensity_recent = carbon_api_intensity()
    # Check if either API call failed
    if (
        df_carbon_forecast_indexed is None
        or co2_stats_prior_day is None
        or df_carbon_intensity_recent is None
    ):
        await update.message.reply_html(
            f"Sorry, {user_first_name} 😔. We're currently unable to retrieve the necessary data due to issues with the <a href='https://www.smartgriddashboard.com'>EirGrid website</a> 🌐. Please try again later. We appreciate your understanding 🙏."
        )

        return  # Exit the function early since we can't proceed without the data
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

        prompt = create_combined_gpt_prompt(
            today_date, eu_summary_text, quantile_summary_text
        )

        # get generated prompt
        gpt_recom = opt_gpt_summarise(prompt)
        # slice the energy saving actions part
        energy_saving_actions = get_energy_actions(gpt_recom)
        audio_msg = generate_voice(energy_saving_actions)
        await context.bot.send_voice(
            update.effective_chat.id,
            audio_msg,
            caption="Here's your energy-saving tips 🎙️",
        )
        await update.message.reply_text(gpt_recom)
        if len(df_with_trend) > 1:
            await send_co2_intensity_plot(update, context, df_with_trend)
        del audio_msg


def telegram_fuel_mix(update, context, user_first_name):
    fuel_mix_eirgrid = fuel_mix()
    descriptive_names = {
        "FUEL_COAL": "Coal",
        "FUEL_GAS": "Gas",
        "FUEL_NET_IMPORT": "Net Import",
        "FUEL_OTHER_FOSSIL": "Other Fossil",
        "FUEL_RENEW": "Renewables",
    }

    fuel_mix_eirgrid["FieldName"] = fuel_mix_eirgrid["FieldName"].map(descriptive_names)