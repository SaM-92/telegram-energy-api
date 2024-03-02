from telegram import Update
from telegram.ext import (
    ContextTypes,
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


async def pie_chart_fuel_mix(update, context, fuel_mix_eirgrid, current_time):
    # Adjusting colors to be less vibrant (more pastel-like)
    pastel_colors = {
        "Coal": "#3B3434",  # Coal - less vibrant gray
        "Gas": "#FF5733",  # Gas - less vibrant orange
        "Net Import": "#8648BD",  # Net Import - less vibrant blue
        "Other Fossil": "#F08080",  # Other Fossil - less vibrant red
        "Renewables": "#48BD5F",  # Renewables - less vibrant green
    }
    print(fuel_mix_eirgrid)
    # Mapping the pastel colors to the dataframe's FieldName
    pastel_pie_colors = [
        pastel_colors[field] for field in fuel_mix_eirgrid["FieldName"]
    ]
    custom_labels = [
        f'{row["FieldName"]}\n({row["Percentage"]:.1f}%)'
        for index, row in fuel_mix_eirgrid.iterrows()
    ]
    plt.figure(figsize=(7, 7))
    plt.pie(
        fuel_mix_eirgrid["Value"],
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
    fuel_mix_eirgrid = fuel_mix()
    descriptive_names = {
        "FUEL_COAL": "Coal",
        "FUEL_GAS": "Gas",
        "FUEL_NET_IMPORT": "Net Import",
        "FUEL_OTHER_FOSSIL": "Other Fossil",
        "FUEL_RENEW": "Renewables",
    }

    fuel_mix_eirgrid["FieldName"] = fuel_mix_eirgrid["FieldName"].map(descriptive_names)

    total = sum(fuel_mix_eirgrid["Value"])
    percentages = [(value / total) * 100 for value in fuel_mix_eirgrid["Value"]]
    fuel_mix_eirgrid["Percentage"] = percentages

    now = round_time(datetime.datetime.now())

    promopt_for_fuel_mix = create_fuel_mix_prompt(now, fuel_mix_eirgrid)
    # fuel_mix_response_from_gpt = opt_gpt_summarise(promopt_for_fuel_mix)

    # audio_msg = generate_voice(fuel_mix_response_from_gpt)

    # await context.bot.send_voice(
    #     update.effective_chat.id,
    #     audio_msg,
    #     caption="Here's fuel mix summary 🎙️",
    # )
    # await update.message.reply_text(fuel_mix_response_from_gpt)
    await pie_chart_fuel_mix(update, context, fuel_mix_eirgrid, now)
