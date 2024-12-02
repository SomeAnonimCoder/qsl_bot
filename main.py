from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup

import mysql.connector
from geopy.point import Point
from datetime import datetime

# Database connection
db_config = {
    "host": "localhost",
    "user": "bot_user",
    "password": "your_password",
    "database": "TelegramBot"
}


def db_connection():
    return mysql.connector.connect(**db_config)

# /start Command: Register user
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.message.from_user.id
    username = update.message.from_user.username

    if not username:
        await update.message.reply_text("You need a Telegram username to register!")
        return

    conn = db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO Users (username, telegram_id) VALUES (%s, %s)",
            (username, telegram_id)
        )
        conn.commit()
        await update.message.reply_text(
            f"Welcome, {username}! You have been registered.\n\n"
            "Use the following commands to interact with the bot:\n"
            "- /logcontact: Log a contact with geolocation.\n"
            "- /logswl: Log a single-way contact with geolocation.\n"
            "- /change_username: Change your registered username.\n"
            "- /help: Get detailed information about commands."
        )
    except mysql.connector.errors.IntegrityError:
        await update.message.reply_text("You are already registered!")
    finally:
        cursor.close()
        conn.close()

# /help Command: Provide detailed descriptions
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
            "Use the following commands to interact with the bot:\n"
            "- /logcontact: Log a contact with geolocation.\n"
            "- /logswl: Log a single-way contact with geolocation.\n"
            "- /change_username: Change your registered username.\n"
            "- /help: Get detailed information about commands."
    )
    await update.message.reply_text(help_text)

# /logcontact Command: Log a contact with geolocation and band selection
async def log_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch other users for selection
    cursor.execute("SELECT username FROM Users WHERE telegram_id != %s", (update.message.from_user.id,))
    users = cursor.fetchall()
    cursor.execute("SELECT band_name FROM Bands")  # Get available bands
    bands = cursor.fetchall()
    cursor.close()
    conn.close()

    if not users:
        await update.message.reply_text("No other users registered to log a contact with.")
        return

    usernames = [user["username"] for user in users]
    band_names = [band["band_name"] for band in bands]

    # Provide keyboard for user selection
    keyboard = [[KeyboardButton(username)] for username in usernames]
    keyboard.append([KeyboardButton("Cancel")])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    context.user_data["state"] = "WAITING_FOR_CONTACT_SELECTION"
    context.user_data["bands"] = band_names  # Store available bands

    await update.message.reply_text("Who did you make the contact with?", reply_markup=reply_markup)

# Handle the contact selection
async def handle_contact_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "WAITING_FOR_CONTACT_SELECTION":
        return

    contact_with_username = update.message.text
    if contact_with_username.lower() == "cancel":
        await update.message.reply_text("Contact logging canceled.")
        context.user_data.clear()
        return

    # After selecting user, prompt for band selection
    band_keyboard = [[KeyboardButton(band)] for band in context.user_data["bands"]]
    band_keyboard.append([KeyboardButton("Cancel")])

    reply_markup = ReplyKeyboardMarkup(band_keyboard, one_time_keyboard=True, resize_keyboard=True)
    context.user_data["contact_with"] = contact_with_username
    await update.message.reply_text("Please select the band for this contact.", reply_markup=reply_markup)
    context.user_data["state"] = "WAITING_FOR_BAND_SELECTION"

# Handle the band selection for the contact
async def handle_band_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print('here!')
    if context.user_data.get("state") != "WAITING_FOR_BAND_SELECTION":
        return

    selected_band = update.message.text
    print(selected_band)
    if selected_band.lower() == "cancel":
        await update.message.reply_text("Band selection canceled.")
        context.user_data.clear()
        return

    # Fetch the band ID from the database
    conn = db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM Bands WHERE band_name = %s", (selected_band,))
    band = cursor.fetchone()

    if band:
        context.user_data["band_id"] = band[0]
        # Proceed to geolocation request
        await update.message.reply_text("Please share your geolocation for this contact.", reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("Share Location", request_location=True)]],
            one_time_keyboard=True,
            resize_keyboard=True
        ))
        context.user_data["state"] = "WAITING_FOR_CONTACT_LOCATION"
    else:
        print(selected_band)
        await update.message.reply_text("Invalid band selection. Please try again.")
    cursor.close()
    conn.close()

# Handle the geolocation for the contact
async def handle_contact_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "WAITING_FOR_CONTACT_LOCATION":
        return

    location = update.message.location
    context.user_data['location'] = location
    if not location:
        await update.message.reply_text("You need to share your location to log the contact.")
        return

    user_id = update.message.from_user.id
    contact_with_username = context.user_data["contact_with"]
    band_id = context.user_data["band_id"]
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    latitude = location.latitude
    longitude = location.longitude

    conn = db_connection()
    cursor = conn.cursor()

    # Fetch the contact user's ID
    cursor.execute("SELECT id FROM Users WHERE username = %s", (contact_with_username,))
    contact_with_id = cursor.fetchone()[0]


    # Confirm the contact details
    confirmation_text = (
        f"Confirm the contact details:\n"
        f"Contact With: {contact_with_username}\n"
        f"Band: {context.user_data['bands'][band_id-1]}\n"
        f"Location: ({latitude}, {longitude})\n"
        f"Timestamp: {timestamp}\n\n"
        "Type 'Confirm' to log this contact, or 'Cancel' to discard."
    )
    keyboard = [
        [KeyboardButton('Confirm')],
        [KeyboardButton('Cancel')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(confirmation_text, reply_markup=reply_markup)

    context.user_data["state"] = "WAITING_FOR_CONFIRMATION"
    cursor.close()
    conn.close()

# Confirm the log to database
async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("state") != "WAITING_FOR_CONFIRMATION":
        return

    user_id = update.message.from_user.id
    contact_with_username = context.user_data["contact_with"]
    band_id = context.user_data["band_id"]
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    latitude = context.user_data['location'].latitude
    longitude = context.user_data['location'].longitude

    conn = db_connection()
    cursor = conn.cursor()

    # Fetch the contact user's ID
    cursor.execute("SELECT id FROM Users WHERE username = %s", (contact_with_username,))
    contact_with_id = cursor.fetchone()[0]

    # Fetch the contact user's ID
    cursor.execute("SELECT id FROM Users WHERE telegram_id = %s", (user_id,))
    contact_from_id = cursor.fetchone()[0]

    user_input = update.message.text.lower()
    if user_input == "confirm":
        conn = db_connection()
        cursor = conn.cursor()

        # Insert contact log with band and location
        cursor.execute(
            "INSERT INTO Contacts (user_id, contact_with_id, timestamp, location, band_id) "
            "VALUES (%s, %s, %s, POINT(%s, %s), %s)",
            (contact_from_id, contact_with_id, timestamp, latitude, longitude, band_id)
        )
        conn.commit()
        await update.message.reply_text("Contact logged successfully!")
        cursor.close()
        conn.close()

    elif user_input == "cancel":
        await update.message.reply_text("Contact logging canceled.")
        context.user_data.clear()

    else:
        await update.message.reply_text("Invalid response. Type 'Confirm' to log or 'Cancel' to discard.")

    context.user_data.clear()

# /logswl Command: Log a single-way contact with geolocation and band selection
async def log_swl(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = db_connection()
    cursor = conn.cursor(dictionary=True)

    # Fetch other users for selection
    cursor.execute("SELECT username FROM Users WHERE telegram_id != %s", (update.message.from_user.id,))
    users = cursor.fetchall()
    cursor.execute("SELECT band_name FROM Bands")  # Get available bands
    bands = cursor.fetchall()
    cursor.close()
    conn.close()

    if not users:
        await update.message.reply_text("No other users registered to log a SWL with.")
        return

    usernames = [user["username"] for user in users]
    band_names = [band["band_name"] for band in bands]

    # Provide keyboard for user selection
    keyboard = [[KeyboardButton(username)] for username in usernames]
    keyboard.append([KeyboardButton("Cancel")])
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    context.user_data["state"] = "WAITING_FOR_SWL_SELECTION"
    context.user_data["bands"] = band_names  # Store available bands

    await update.message.reply_text("Who did you make the one-way contact with?", reply_markup=reply_markup)

# Handle the SWL contact selection
async def handle_swl_contact_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print('handle_swl_contact_selection')

    if context.user_data.get("state") != "WAITING_FOR_SWL_SELECTION":
        return

    contact_with_username = update.message.text
    if contact_with_username.lower() == "cancel":
        await update.message.reply_text("SWL logging canceled.")
        context.user_data.clear()
        return

    # After selecting user, prompt for band selection
    band_keyboard = [[KeyboardButton(band)] for band in context.user_data["bands"]]
    band_keyboard.append([KeyboardButton("Cancel")])

    reply_markup = ReplyKeyboardMarkup(band_keyboard, one_time_keyboard=True, resize_keyboard=True)
    context.user_data["contact_with"] = contact_with_username

    await update.message.reply_text("Please select the band for this SWL.", reply_markup=reply_markup)
    context.user_data["state"] = "WAITING_FOR_SWL_BAND_SELECTION"

# Handle the band selection for the SWL
async def handle_swl_band_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print('handle_swl_band_selection')
    if context.user_data.get("state") != "WAITING_FOR_SWL_BAND_SELECTION":
        return

    selected_band = update.message.text
    if selected_band.lower() == "cancel":
        await update.message.reply_text("Band selection canceled.")
        context.user_data.clear()
        return

    # Fetch the band ID from the database
    conn = db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id FROM Bands WHERE band_name = %s", (selected_band,))
    band = cursor.fetchone()

    if band:
        context.user_data["band_id"] = band[0]
        # Proceed to geolocation request
        await update.message.reply_text("Please share your geolocation for this SWL.", reply_markup=ReplyKeyboardMarkup(
            [[KeyboardButton("Share Location", request_location=True)]],
            one_time_keyboard=True,
            resize_keyboard=True
        ))
        context.user_data["state"] = "WAITING_FOR_SWL_LOCATION"
    else:
        await update.message.reply_text("Invalid band selection. Please try again.")
    cursor.close()
    conn.close()

# Handle the geolocation for the SWL
async def handle_swl_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print('handle_swl_location')
    if context.user_data.get("state") != "WAITING_FOR_SWL_LOCATION":
        return

    location = update.message.location
    if not location:
        await update.message.reply_text("You need to share your location to log the SWL.")
        return

    user_id = update.message.from_user.id
    contact_with_username = context.user_data["contact_with"]
    band_id = context.user_data["band_id"]
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    latitude = location.latitude
    longitude = location.longitude
    context.user_data['location'] = location

    conn = db_connection()
    cursor = conn.cursor()

    # Fetch the contact user's ID
    cursor.execute("SELECT id FROM Users WHERE username = %s", (contact_with_username,))
    contact_with_id = cursor.fetchone()[0]

    # Confirm the SWL details
    confirmation_text = (
        f"Confirm the SWL details:\n"
        f"One-Way Contact With: {contact_with_username}\n"
        f"Band: {context.user_data['bands'][band_id-1]}\n"
        f"Location: ({latitude}, {longitude})\n"
        f"Timestamp: {timestamp}\n\n"
        "Type 'Confirm' to log this SWL, or 'Cancel' to discard."
    )
    keyboard = [
        [KeyboardButton('Confirm')],
        [KeyboardButton('Cancel')]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

    await update.message.reply_text(confirmation_text, reply_markup=reply_markup)

    context.user_data["state"] = "WAITING_FOR_SWL_CONFIRMATION"
    cursor.close()
    conn.close()

# Confirm the log to database for SWL
async def handle_swl_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print('handle_swl_confirmation')
    if context.user_data.get("state") != "WAITING_FOR_SWL_CONFIRMATION":
        return
    user_input = update.message.text.lower()

    if user_input == "confirm":
        conn = db_connection()
        cursor = conn.cursor()
        user_id = update.message.from_user.id
        contact_with_username = context.user_data["contact_with"]
        band_id = context.user_data["band_id"]
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        latitude = context.user_data['location'].latitude
        longitude = context.user_data['location'].longitude
        # Fetch the contact user's ID
        cursor.execute("SELECT id FROM Users WHERE telegram_id = %s", (user_id,))
        contact_from_id = cursor.fetchone()[0]



        # Fetch the contact user's ID
        cursor.execute("SELECT id FROM Users WHERE username = %s", (contact_with_username,))
        contact_with_id = cursor.fetchone()[0]

        # Insert SWL log with band and location
        cursor.execute(
            "INSERT INTO SWL (user_id, contact_with_id, timestamp, location, band_id) "
            "VALUES (%s, %s, %s, POINT(%s, %s), %s)",
            (contact_from_id, contact_with_id, timestamp, latitude, longitude, band_id)
        )
        conn.commit()
        await update.message.reply_text("SWL logged successfully!")
        cursor.close()
        conn.close()

    elif user_input == "cancel":
        await update.message.reply_text("SWL logging canceled.")
        context.user_data.clear()

    else:
        await update.message.reply_text("Invalid response. Type 'Confirm' to log or 'Cancel' to discard.")

    context.user_data.clear()



async def handle_texts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_contact_selection(update, context)
    print('1')
    await handle_band_selection(update, context)
    print('2')
    await handle_confirmation(update, context)
    print('3')

    await handle_swl_contact_selection(update, context)
    print('4')
    await handle_swl_band_selection(update, context)
    print('5')
    await handle_swl_confirmation(update, context)
    print('6')
    


async def handle_locations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await handle_swl_location(update, context)
    print('l1')
    await handle_contact_location(update, context)
    print('l1')


# Adding command handlers to the application
def main():
    TOKEN = "1271390159:AAESblwx1Yg4ZHZG5AxPweQG07m5pN8YL6w"
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("logcontact", log_contact))
    application.add_handler(CommandHandler("logswl", log_swl))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.LOCATION, handle_locations))
    application.add_handler(MessageHandler(filters.TEXT, handle_texts))

    application.run_polling()

if __name__ == "__main__":
    main()
