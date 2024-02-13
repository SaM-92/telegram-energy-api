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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
Telegram_energy_api = os.environ.get("Telegram_energy_api")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define conversation states
SELECT_OPTION = 0
TIME_COLUMN_SELECTED = 1


async def send_co2_intensity_plot(
    update: Update, context: ContextTypes.DEFAULT_TYPE, df_
):
    chat_id = update.effective_chat.id

    # Call the function to generate the plot
    plt = co2_int_plot(df_)

    # Save the plot to a BytesIO buffer
    buf = BytesIO()
    plt.savefig(buf, format="png", facecolor="black")
    buf.seek(0)
    plt.close()  # Make sure to close the plot to free up memory

    # Send the photo
    await context.bot.send_photo(chat_id=chat_id, photo=buf)


async def energy_api_func(update: Update, context: CallbackContext):

    user_first_name = update.message.from_user.first_name

    await update.message.reply_text(
        f"""Thank you! \n 🚀 We are now processing your request and we will get back to you shortly. \n ⏱️ It takes up to 10 seconds.. """
    )
    # Retrieve the text of the message sent by the user. This is assumed to be the column name
    # the user has selected.
    user_selected_option = update.message.text

    # Store the selected column name in the context's user_data dictionary.
    # This is a way to persist user-specific data across different states of the conversation.
    # The key 'selected_option' is used to store and later retrieve the user's choice.
    context.user_data["selected_option"] = user_selected_option

    # Store the selected time column
    # Retrieve the user_data dictionary from the context.
    # This dictionary holds data specific to the current user and can be accessed across
    # different states in the conversation.
    user_data = context.user_data

    # Retrieve the DataFrame stored in user_data. The key 'data_frame' should have been set
    # in a previous step of the conversation where the user uploaded their data.

    # Retrieve the selected time column name from user_data.
    # This should be the same as 'user_selected_column', and it's the column name
    # chosen by the user for further data processing.
    selected_option_user = user_data.get("selected_option")

    # Inform the user that the time column has been selected
    await update.message.reply_text(
        f"I understand that you have selected: {selected_option_user}"
    )

    chat_id = update.effective_chat.id

    if selected_option_user == "Carbon intensity":
        df_carbon_forecast_indexed = carbon_api_forecast()
        co2_stats_prior_day, df_carbon_intensity_recent = carbon_api_intensity()
        df_ = status_classification(df_carbon_forecast_indexed, co2_stats_prior_day)
        # Specify the chat ID of the recipient (could be a user or a group)
        # Send the image stored in buffer
        date = str(df_.index[0])
        eu_summary_text = optimize_categorize_periods(df_)
        quantile_summary_text = find_optimized_relative_periods(
            df_
        )  # Generate this based on your DataFrame
        prompt = create_combined_gpt_prompt(
            date, eu_summary_text, quantile_summary_text
        )
        gpt_recom = opt_gpt_summarise(prompt)
        await update.message.reply_text(gpt_recom)
        await send_co2_intensity_plot(update, context, df_)

    else:
        await update.message.reply_text(
            f"Sorry {user_first_name}! 🤖 We are still working on this feature. Please try again later."
        )

    # End the conversation
    next_state = user_data.get("next_state", ConversationHandler.END)
    return next_state


async def energy_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = update.message.from_user.first_name
    options = [
        "Carbon intensity"
        # ,
        # "Renewable energy status [Under Deveoplment]",
        # "Price of electricity (wholesale market) [Under Deveoplment]",
    ]
    # Create a custom keyboard with the column names
    keyboard = [[option] for option in options]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    # send the list of options and ask the user to select one
    await update.message.reply_text(
        "I'm here to help you with energy insights. Which category would you like more information about?",
        reply_markup=reply_markup,
    )
    # Set the conversation state to SELECT_COLUMN
    context.user_data["next_state"] = SELECT_OPTION
    return SELECT_OPTION


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"{user_first_name}!! 😃 Use the command /energy_status to kick off your inquiry!"
    )


# Define a custom filter function to check for documents
def is_document(update: Update):
    return update.message.document is not None


# Create a custom filter function to exclude specific commands
def is_not_command(update):
    logging.info("is_not_command function called")
    result = update.message.text not in ("/cancel", "/start")
    logging.info(f"is_not_command result: {result}")
    return result


async def help_command(update: Update, context: CallbackContext) -> None:
    # user_first_name = update.message.from_user.first_name
    await update.message.reply_text(
        "🔍 Need help getting started? Here’s how to use me: \n\n"
        "Use the command /energy_status to kick off your inquiry. I’ll guide you through a simple selection process to understand your needs. "
        "Based on real-time data analysis, I'll provide energy usage recommendations to help you be more eco-friendly. "
        "Additionally, you’ll receive a colour-coded image to visually guide you in scheduling your day’s energy consumption efficiently. "
        "With my help, you can make your energy usage as green as possible!"
    )


async def about_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "🤖 Welcome to the CleanEnergyBot, your go-to source for electricity insights in Ireland! "
        "Currently exclusive to Ireland, this bot leverages real-time data from EirGrid, the entity tasked "
        "with electricity delivery across the country. Our latest version offers an insightful analysis of CO2 "
        "emissions forecasts for today, comparing these figures with yesterday's values and EU standard rates. "
        "Through detailed data analysis and supported by the advanced capabilities of GPT-3, our bot provides "
        "tailored recommendations on the most efficient times for energy usage. It makes your energy decisions stronger with "
        "smart insights and helps you contribute to a more sustainable future."
    )


def main() -> None:
    """
    Entry point of the program.
    Initialises the application and sets up the handlers.

    This function creates an Application instance, sets up the conversation handlers,
    and starts the bot to listen for incoming messages and commands.
    """
    token = Telegram_energy_api  # os.environ.get("Telegram_energy_api")
    # Create the Application instance
    application = Application.builder().token(token).build()

    SELECT_OPTION = 0
    # Create a ConversationHandler for handling the file upload and column selection
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("energy_status", energy_status),
            # MessageHandler(filters.Document.ALL, doc_handler),
        ],
        states={
            SELECT_OPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, energy_api_func)
            ],
        },
        fallbacks=[],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))

    application.run_polling()


if __name__ == "__main__":
    main()
