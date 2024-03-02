import logging
import os
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
from subs.telegram_func import telegram_carbon_intensity
from dotenv import load_dotenv

# add vars to azure
# Load environment variables from .env file
load_dotenv()
Telegram_energy_api = os.environ.get("Telegram_energy_api")
CHANNEL_ID_FOR_FEEDBACK = os.environ.get("CHANNEL_ID_FOR_FEEDBACK")
ELEVEN_API_KEY = os.environ.get("ELEVEN_API_KEY")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define conversation states
# SELECT_OPTION = 0
TIME_COLUMN_SELECTED = 1
# FOLLOW_UP = 0
SELECT_OPTION, FOLLOW_UP, FEEDBACK = range(3)


# async def send_co2_intensity_plot(
#     update: Update, context: ContextTypes.DEFAULT_TYPE, df_
# ):

#     caption_text = (
#         "🎨 This visualisation presents today's CO2 emission trends and intensity levels, "
#         "emphasizing expected changes over the course of the day. The blue line delineates the emission trend, accompanied by "
#         "color-coded circles indicating value intensity at specific points. Additionally, colored circles positioned at the bottom "
#         "of the image correspond to intensity levels at 30-minute intervals—green signifies low intensity, orange denotes medium, "
#         "and red indicates high intensity. This guide is designed to assist in planning energy usage with environmental impact in mind."
#     )

#     chat_id = update.effective_chat.id

#     # Call the function to generate the plot
#     plt = co2_plot_trend(df_)

#     # Save the plot to a BytesIO buffer
#     buf = BytesIO()
#     plt.savefig(buf, format="png")
#     buf.seek(0)
#     plt.close()  # Make sure to close the plot to free up memory

#     # Send the photo
#     await context.bot.send_photo(chat_id=chat_id, photo=buf, caption=caption_text)


async def energy_api_func(update: Update, context: CallbackContext):

    user_first_name = update.message.from_user.first_name

    await update.message.reply_text(
        """Thank you! \n 🚀 We are now processing your request and we will get back to you shortly. \n ⏱️ It takes up to 10 seconds.. """
    )

    user_selected_option = update.message.text

    context.user_data["selected_option"] = user_selected_option

    user_data = context.user_data

    selected_option_user = user_data.get("selected_option")

    chat_id = update.effective_chat.id

    if selected_option_user == "Carbon intensity":
        await telegram_carbon_intensity(update, context, user_first_name)
        # df_carbon_forecast_indexed = None
        # co2_stats_prior_day = None
        # df_carbon_intensity_recent = None

        # # Proceed with your existing logic here...
        # df_carbon_forecast_indexed = carbon_api_forecast()
        # co2_stats_prior_day, df_carbon_intensity_recent = carbon_api_intensity()
        # # Check if either API call failed
        # if (
        #     df_carbon_forecast_indexed is None
        #     or co2_stats_prior_day is None
        #     or df_carbon_intensity_recent is None
        # ):
        #     await update.message.reply_html(
        #         f"Sorry, {user_first_name} 😔. We're currently unable to retrieve the necessary data due to issues with the <a href='https://www.smartgriddashboard.com'>EirGrid website</a> 🌐. Please try again later. We appreciate your understanding 🙏."
        #     )

        #     return  # Exit the function early since we can't proceed without the data
        # else:
        #     # df_carbon_forecast_indexed = carbon_api_forecast()
        #     # co2_stats_prior_day, df_carbon_intensity_recent = carbon_api_intensity()
        #     df_ = status_classification(df_carbon_forecast_indexed, co2_stats_prior_day)
        #     # data analysis & adding category per hours
        #     summary_text, df_with_trend = find_optimized_relative_periods(df_)
        #     today_date = df_with_trend.index[0].strftime("%d/%m/%Y")
        #     eu_summary_text = optimize_categorize_periods(df_with_trend)
        #     quantile_summary_text, df_with_trend_ = find_optimized_relative_periods(
        #         df_with_trend
        #     )  # Generate this based on your DataFrame

        #     prompt = create_combined_gpt_prompt(
        #         today_date, eu_summary_text, quantile_summary_text
        #     )

        #     # get generated prompt
        #     gpt_recom = opt_gpt_summarise(prompt)
        #     # slice the energy saving actions part
        #     energy_saving_actions = get_energy_actions(gpt_recom)
        #     audio_msg = generate_voice(energy_saving_actions)
        #     await context.bot.send_voice(
        #         update.effective_chat.id,
        #         audio_msg,
        #         caption="Here's your energy-saving tips 🎙️",
        #     )
        #     await update.message.reply_text(gpt_recom)
        #     if len(df_with_trend) > 1:
        #         await send_co2_intensity_plot(update, context, df_with_trend)
        #     del audio_msg

    else:
        await update.message.reply_text(
            f"Sorry {user_first_name}! 🤖 We are still working on this feature. Please try again later."
        )

    # End the conversation
    # next_state = user_data.get("next_state", ConversationHandler.END)
    # Decide the next state dynamically and store it in context.user_data
    # context.user_data["next_state_2"] = FOLLOW_UP  # Or some other state based on logic
    # After processing, directly inform the user of the next steps.
    options_keyboard = [["Start Over", "End Conversation", "Provide Feedback"]]
    reply_markup = ReplyKeyboardMarkup(options_keyboard, one_time_keyboard=True)

    await update.message.reply_text(
        "We've processed your request. What would you like to do next?",
        reply_markup=reply_markup,
    )

    # Now, instead of automatically returning FOLLOW_UP, you wait for the user's response
    # to either 'Start Over' or 'End Conversation'.
    # This requires handling these responses in the FOLLOW_UP state.
    return FOLLOW_UP


async def energy_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = update.message.from_user.first_name
    options = [
        "Carbon intensity",
        "Fuel mix",
        # "Price of electricity (wholesale market) [Under Deveoplment]",
    ]
    # Create a custom keyboard with the column names
    keyboard = [[option] for option in options]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

    # send the list of options and ask the user to select one
    await update.message.reply_text(
        "I'm here to help you with energy insights. Which category would you like more information about?💡🌍🔍",
        reply_markup=reply_markup,
    )
    # Set the conversation state to SELECT_COLUMN
    context.user_data["next_state"] = SELECT_OPTION
    return SELECT_OPTION


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = update.message.from_user.first_name
    welcome_message = (
        f"Hello, {user_first_name}! 😃 Welcome to the CleanEnergyBot, your go-to source for electricity insights in Ireland!\n\n"
        "Use the command /energy_status to check the current energy status. You can also use /feedback to provide feedback "
        "or /about to learn more about this bot and how it can help you make smarter energy decisions and contribute to a more sustainable future.\n\n"
        "What would you like to do today?"
    )
    await update.message.reply_text(welcome_message)


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


async def cancel(update: Update, context) -> int:
    """
    Sends a message that the conversation is canceled and ends the conversation asynchronously.
    """
    await update.message.reply_text("Operation canceled.")
    return ConversationHandler.END


async def start_over_handler(update: Update, context: CallbackContext) -> int:
    # Reset state or context as needed
    # context.user_data.clear()  # Uncomment if you want to clear user data

    # Inform the user and restart the conversation
    await update.message.reply_text(
        "Let's start over. Use /start to kick off your inquiry!"
    )
    return SELECT_OPTION  # Assuming SELECT_OPTION is the initial state of your conversation


async def end_conversation_handler(update: Update, context: CallbackContext) -> int:
    await update.message.reply_text(
        "Thank you for using our service. Have a great day! 💚 🌎"
    )
    return ConversationHandler.END


async def unexpected_input_handler(update: Update, context: CallbackContext) -> int:
    # Prompt the user again with the correct options or provide help
    await update.message.reply_text(
        "I didn't understand that. You can choose to 'Start Over' or 'End Conversation'."
    )
    # Return the same state to allow the user to make a choice again
    return FOLLOW_UP


async def follow_up(update: Update, context: CallbackContext) -> int:
    """
    Prompt users with options for further actions after completing an operation.

    This asynchronous function sends a message to users, suggesting they can either
    restart the process by using the /start command or seek additional support through /help.
    It signifies an open-ended pathway for users, ensuring they are not left at a dead-end
    after an action completes.
    """
    # Instructions including email and GitHub, and how to send feedback directly
    contact_message = (
        "Operation completed. 🎉 Feel free to use /start to explore other functionalities or /help if you require assistance.\n"
        "If you have feedback or need to contact me directly, here are the ways you can reach out:\n"
        "- Email: 📧 sam.misaqian@gmail.com\n"
        "- GitHub: 💻 https://github.com/SaM-92\n"
        "- LinkedIn: 🔗 https://www.linkedin.com/in/saeed-misaghian/\n"
        "Or you can send your feedback directly here by typing your message after /feedback."
    )
    await update.message.reply_text(contact_message)
    return ConversationHandler.END


async def feedback_command(update: Update, context: CallbackContext) -> int:
    logger.info("Entered feedback_command")
    await update.message.reply_text("Please type your feedback.")
    return FEEDBACK


async def feedback_text(update: Update, context: CallbackContext) -> int:
    logger.info("Entered feedback_text")
    feedback = update.message.text

    await context.bot.forward_message(
        chat_id=CHANNEL_ID_FOR_FEEDBACK,
        from_chat_id=update.effective_chat.id,
        message_id=update.message.message_id,
    )

    await update.message.reply_text("Thank you for your feedback! ✨")
    return ConversationHandler.END


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

    # SELECT_OPTION, FOLLOW_UP, FEEDBACK = range(3)  # Correctly define states

    # Create a ConversationHandler for handling the file upload and column selection
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CommandHandler("energy_status", energy_status),
            CommandHandler("feedback", feedback_command),
            # MessageHandler(filters.Document.ALL, doc_handler),
        ],
        states={
            SELECT_OPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, energy_api_func)
            ],
            FOLLOW_UP: [
                MessageHandler(filters.Regex("^(Start Over)$"), start_over_handler),
                MessageHandler(
                    filters.Regex("^(End Conversation)$"), end_conversation_handler
                ),
                MessageHandler(filters.Regex("^(Provide Feedback)$"), follow_up),
                # Add a fallback handler within FOLLOW_UP for unexpected inputs
                MessageHandler(filters.ALL, unexpected_input_handler),
            ],
            FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, feedback_text)],
        },
        fallbacks=[
            CommandHandler(
                "cancel", cancel
            ),  # Allows the user to cancel the conversation
        ],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))  # Global handler
    application.add_handler(
        CommandHandler("energy_status", energy_status)
    )  # Global handler
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("about", about_command))
    application.add_handler(CommandHandler("SocialMedia", follow_up))
    application.add_handler(CommandHandler("feedback", feedback_command))
    application.add_handler(
        CommandHandler("cancel", cancel)
    )  # Directly handle cancel command

    application.run_polling()


if __name__ == "__main__":
    main()
