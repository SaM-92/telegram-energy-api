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
from subs.data_loader import (
    process_data_for_analysis,
    process_uploaded_file,
    convert_time,
    process_time_resolution_and_duplicates,
    display_column_statistics,
)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define conversation states
SELECT_COLUMN = 0
TIME_COLUMN_SELECTED = 1


async def process_and_resample_data(update: Update, context: CallbackContext):
    """
    Handles the processing and resampling of uploaded time series data.

    This function is triggered when the user selects a time column for the uploaded data.
    It performs data preprocessing, including handling missing values and resampling the data
    to an hourly resolution. The function also sends back the processed data to the user along with
    some basic statistics.

    Args:
        update (telegram.Update): The incoming update from the user.
        context (telegram.ext.CallbackContext): The context for the conversation.

    Returns:
        int: The next state in the conversation flow.
    """
    user_first_name = update.message.from_user.first_name

    await update.message.reply_text(
        f"""Thank you {user_first_name}! 🤖 We are now processing your data 
        and will send it back to you shortly."""
    )
    # Retrieve the text of the message sent by the user. This is assumed to be the column name
    # the user has selected.
    user_selected_column = update.message.text

    # Store the selected column name in the context's user_data dictionary.
    # This is a way to persist user-specific data across different states of the conversation.
    # The key 'selected_time_column' is used to store and later retrieve the user's choice.
    context.user_data["selected_time_column"] = user_selected_column

    # Store the selected time column
    # Retrieve the user_data dictionary from the context.
    # This dictionary holds data specific to the current user and can be accessed across
    # different states in the conversation.
    user_data = context.user_data

    # Retrieve the DataFrame stored in user_data. The key 'data_frame' should have been set
    # in a previous step of the conversation where the user uploaded their data.
    # If 'data_frame' was not set, df will be None.
    df = user_data.get("data_frame")

    # Retrieve the selected time column name from user_data.
    # This should be the same as 'user_selected_column', and it's the column name
    # chosen by the user for further data processing.
    selected_time_column = user_data.get("selected_time_column")

    # Inform the user that the time column has been selected
    await update.message.reply_text(
        f"I understand that you have selected: {selected_time_column}"
    )

    # Process data for further analysis with the selected time column
    if df is not None and selected_time_column:
        # Process data for further analysis using the selected time column
        (
            df_read,
            skip_invalid_row,
            first_invalid_row_time,
        ) = process_data_for_analysis(df, selected_time_column)

        # I hard coded the selected_option_missing_values, but it can be a user input
        selected_option_missing_values = "Interpolate"
        # Deal with missing values
        df_read = process_uploaded_file(df_read, selected_option_missing_values)

        # await update.message.reply_text(" Now it's the time for resampling data  ⏰")

        # Set the time resolution, again hard coded, but it can be a user input
        time_resolution_number = 1
        time_resolution_unit = "hours"

        #  Apply the function to your DataFrame
        df_read = convert_time(df_read, selected_time_column)

        # Apply the function to the dataframe to resample it
        df_read = process_time_resolution_and_duplicates(
            df_read,
            selected_time_column,
            time_resolution_number,
            time_resolution_unit,
            skip_invalid_row,
            first_invalid_row_time,
        )

        # head_string = df_read.head().to_string()
        # await update.message.reply_text(f"Head of the DataFrame:\n\n{head_string}")

        # Send back the processed csv file to the user
        if df_read is not None:
            # Save the processed DataFrame to a CSV file
            output_file_path = "processed_data.csv"
            df_read.to_csv(output_file_path, index="True")
            statistics_text = display_column_statistics(df_read)
            await update.message.reply_text(statistics_text, parse_mode="MarkdownV2")
            # Call the display_column_statistics function
            display_column_statistics(df_read)

            # Send the CSV file back to the user
            with open(output_file_path, "rb") as file:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id, document=file
                )
            await update.message.reply_text("Please Download the processed data 📥")

    # End the conversation
    next_state = user_data.get("next_state", ConversationHandler.END)
    return next_state


async def doc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    document = update.message.document
    if document:
        # Get file ID
        file_id = document.file_id
        logger.info(f"FILE ID:  {file_id}")

        # Get file information
        new_file = await context.bot.get_file(file_id)

        # Construct file download URL
        file_url = (
            f"https://api.telegram.org/file/bot{context.bot.token}/{new_file.file_path}"
        )

        logger.info(f"Downloading file from: {file_url}")

        if "https://" in file_url:
            # Extract the relative file path part
            file_path_part = file_url.split("https://")[2].split("/")[-1]
            file_url_files = f"https://api.telegram.org/file/bot{context.bot.token}/documents/{file_path_part}"

        # Read the CSV file into a pandas DataFrame
        try:
            df = pd.read_csv(file_url_files)

            # Store the DataFrame and column names in user_data
            context.user_data["data_frame"] = df
            column_names = df.columns.tolist()
            context.user_data["column_names"] = column_names

            # Create a custom keyboard with the column names
            keyboard = [[col] for col in column_names]
            reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)

            # Send the list of column names and instruct the user to select one
            await update.message.reply_text(
                "Please select the time column:", reply_markup=reply_markup
            )
            # await update.message.reply_text("Now, let's call select_column.")

            # Set the conversation state to SELECT_COLUMN
            context.user_data["next_state"] = SELECT_COLUMN
            return SELECT_COLUMN

        except Exception as e:
            await update.message.reply_text(f"Error reading file: {e}")
            return ConversationHandler.END


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_first_name = update.message.from_user.first_name
    await update.message.reply_text(
        f" Welcome {user_first_name}!! 😃 Please upload a CSV file, and be sure it has time column!"
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
    user_first_name = update.message.from_user.first_name
    await update.message.reply_text(
        f"{user_first_name}, you can use /start to begin the process. Send a time series data file for analysis in CSV format. "
        "The bot will process the data, interpolating missing values, and resample it to an hourly resolution."
        "You can then download the processed data file."
    )


async def about_command(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        " 🤖 This is a demo bot for time series data analysis. It processes uploaded data, "
        "takes care of missing values by linear interpolation, and changes the sample "
        "to an hourly resolution. It's primarily oriented around ENTSO-E dataset analysis. "
        "After processing, you can download a CSV file with 1-hour resolution data and receive a brief data analysis."
    )


def main() -> None:
    """
    Entry point of the program.
    Initialises the application and sets up the handlers.

    This function creates an Application instance, sets up the conversation handlers,
    and starts the bot to listen for incoming messages and commands.
    """
    token = os.environ.get("TELEGRAM_TOKEN")
    # Create the Application instance
    application = Application.builder().token(token).build()

    SELECT_COLUMN = 0
    # Create a ConversationHandler for handling the file upload and column selection
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            MessageHandler(filters.Document.ALL, doc_handler),
        ],
        states={
            SELECT_COLUMN: [
                MessageHandler(
                    filters.TEXT & ~filters.COMMAND, process_and_resample_data
                )
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
