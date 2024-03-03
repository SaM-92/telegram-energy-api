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
from subs.telegram_func import (
    telegram_carbon_intensity,
    telegram_fuel_mix,
    telegram_personalised_handler,
)
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
SELECT_OPTION, FOLLOW_UP, FEEDBACK, ASK_PLAN, FOLLOW_UP_CONVERSATION = range(5)


async def energy_api_func(update: Update, context: CallbackContext):
    """
    Processes user requests for energy-related information via a Telegram bot and replies with relevant data or status updates.

    This asynchronous function handles user queries for carbon intensity or fuel mix information. Upon receiving a request, it acknowledges receipt and processes the request based on the user's selected option. It supports dynamic user interactions by maintaining state and offering follow-up actions.

    Args:
        update (Update): Contains the incoming update data, including the user's message and chat information.
        context (CallbackContext): Holds context-specific data like user data for state management between interactions.

    Returns:
        This function sends messages directly to the Telegram chat.
        Returns a status code indicating the next step in the conversation flow, such as FOLLOW_UP for continuing interaction.
    """

    user_first_name = update.message.from_user.first_name

    await update.message.reply_text(
        """Thank you! \n 🚀 We are now processing your request and we will get back to you shortly. \n ⏱️ It takes up to 10 seconds.. """
    )

    user_selected_option = update.message.text

    context.user_data["selected_option"] = user_selected_option

    user_data = context.user_data

    selected_option_user = user_data.get("selected_option")

    chat_id = update.effective_chat.id

    if selected_option_user == "🌍 Carbon intensity":
        await telegram_carbon_intensity(update, context, user_first_name)
    elif selected_option_user == "🔋 Fuel mix":
        await telegram_fuel_mix(update, context, user_first_name)
    else:
        await update.message.reply_text(
            f"Sorry {user_first_name}! 🤖 We are still working on this feature. Please try again later."
        )

    options_keyboard = [
        [
            "✨ Personalised Recommendations",
            "🔄 Start Over",
            "🔚 End Conversation",
            "💬 Provide Feedback",
        ]
    ]
    reply_markup = ReplyKeyboardMarkup(options_keyboard, one_time_keyboard=True)

    await update.message.reply_text(
        "We've processed your request. What would you like to do next?",
        reply_markup=reply_markup,
    )

    return FOLLOW_UP


async def energy_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = update.message.from_user.first_name
    options = [
        "🌍 Carbon intensity",
        "🔋 Fuel mix",
        # "💸 Price of electricity (wholesale market) [Under Development]",
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
    await update.message.reply_text("💬 Please type your feedback.")
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


async def personalised_recommendations_handler(
    update: Update, context: CallbackContext
) -> None:
    # Prompt the user to specify their plans or devices they intend to use
    await update.message.reply_text(
        "🔌💡 Wondering about the best time for laundry to save energy? Just mention the device or ask me—like when to do laundry? I'm here to guide you! 🌿👕"
    )
    return ASK_PLAN


async def planning_response_handler(update: Update, context: CallbackContext) -> int:
    # User's response to the planning question
    user_query = update.message.text
    # Check if there's an existing conversation context
    if "conversation_context" not in context.user_data:
        context.user_data["conversation_context"] = user_query
    else:
        # Append new question to existing context
        context.user_data["conversation_context"] += f"\n{user_query}"

    user_first_name = update.message.from_user.first_name
    # Logic to process the user's response and provide recommendations
    # Your recommendation logic here
    AI_response_to_query = await telegram_personalised_handler(
        update, context, user_first_name, context.user_data["conversation_context"]
    )
    await update.message.reply_text(AI_response_to_query)

    # Ask if they have any further questions
    await update.message.reply_text("Any further questions (Y/N)?")

    # Transition to another state or end the conversation
    return FOLLOW_UP_CONVERSATION


async def follow_up_handler(update: Update, context: CallbackContext) -> int:
    user_response = update.message.text.lower()

    if user_response in ["yes", "y"]:
        # Prompt for the next question
        await update.message.reply_text("What would you like to know next?")
        return ASK_PLAN
    else:
        await update.message.reply_text("Thank you for using our service. Goodbye!")
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
            CommandHandler(
                "personal_advice",
                personalised_recommendations_handler,
            ),
            CommandHandler("feedback", feedback_command),
            # MessageHandler(filters.Document.ALL, doc_handler),
        ],
        states={
            SELECT_OPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, energy_api_func)
            ],
            FOLLOW_UP: [
                MessageHandler(
                    filters.Regex("^✨ Personalised Recommendations$"),
                    personalised_recommendations_handler,
                ),
                MessageHandler(filters.Regex("^🔄 Start Over$"), start_over_handler),
                MessageHandler(
                    filters.Regex("^🔚 End Conversation$"), end_conversation_handler
                ),
                MessageHandler(filters.Regex("^💬 Provide Feedback$"), follow_up),
                # Add a fallback handler within FOLLOW_UP for unexpected inputs
                MessageHandler(filters.ALL, unexpected_input_handler),
            ],
            ASK_PLAN: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, planning_response_handler
                )
            ],
            FOLLOW_UP_CONVERSATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, follow_up_handler)
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
    application.add_handler(
        CommandHandler("personal_advice", personalised_recommendations_handler)
    )

    application.run_polling()


if __name__ == "__main__":
    main()
