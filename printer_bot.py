#!/bin/python3


import telegram
from telegram import Update, InlineKeyboardButton, \
    InlineKeyboardMarkup
from telegram.ext import Filters, Updater, CallbackContext, MessageHandler, \
    CommandHandler, CallbackQueryHandler
import os
import subprocess
import time
from env import *

settings = {
    ORIENTATION: Orientation.portrait,
    SCALE: '100%',
    COPIES: 1
}


def orientation_handler(update: Update, context: CallbackContext):
    buttons = [
        [
            InlineKeyboardButton(text='Portrait',
                                 callback_data=PORTRAIT)
        ],
        [
            InlineKeyboardButton(text='Landscape',
                                 callback_data=LANDSCAPE)
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    update.callback_query.answer()
    update.callback_query.edit_message_text(text='Choose orientation',
                                            reply_markup=keyboard)
    return SELECTING_ORIENTATION


def select_orientation(update: Update, context: CallbackContext):
    data = update.callback_query.data

    settings[ORIENTATION] = Orientation.portrait \
        if data == PORTRAIT \
        else Orientation.landscape

    return settings_handler(update, context)


def cancel_handler(update: Update, context: CallbackContext):
    return settings_handler(update, context)


def copies_handler(update: Update, context: CallbackContext):
    text = 'Type amount of copies you want to print:'

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text)
    return SETTING_COPIES


def set_copies(update: Update, context: CallbackContext):
    try:
        settings[COPIES] = int(update.message.text)
    except ValueError:
        update.message.reply_text('Please, enter integer number')

    return settings_handler(update, context)


def scale_handler(update: Update, context: CallbackContext):
    text = 'Type scale in percents like 100%:'

    update.callback_query.answer()
    update.callback_query.edit_message_text(text=text)

    return SETTING_SCALE


def set_scale(update: Update, context: CallbackContext):
    try:
        if not update.message.text.endswith('%'):
            raise ValueError
        settings[SCALE] = f'{int(update.message.text[:-1])}%'
    except ValueError:
        update.message.reply_text('Please, enter integer number with "%" sign')

    return settings_handler(update, context)


def settings_handler(update: Update, context: CallbackContext):
    buttons = [
        [
            InlineKeyboardButton(text=f'Change orientation:'
                                      f'(current: {settings[ORIENTATION]})',
                                 callback_data=SELECTING_ORIENTATION)
        ],
        [
            InlineKeyboardButton(text=f'Change number of copies'
                                      f'(current: {settings[COPIES]})',
                                 callback_data=SETTING_COPIES)
        ],
        [
            InlineKeyboardButton(text=f'Change scale'
                                      f'(current: {settings[SCALE]})',
                                 callback_data=SETTING_SCALE)
        ],
        [
            InlineKeyboardButton(text=f'Done',
                                 callback_data=PRINT)
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)
    if update.callback_query is not None:
        update.callback_query.edit_message_text(text='Choose setting to edit:',
                                                reply_markup=keyboard)
    else:
        update.message.reply_text(text='Choose setting to edit:',
                                  reply_markup=keyboard)

    return CHOOSE_SETTING


def choose_setting(update: Update, context: CallbackContext):
    states = {
        SETTING_SCALE: scale_handler,
        SETTING_COPIES: copies_handler,
        SELECTING_ORIENTATION: orientation_handler,
        PRINT: print_handler
    }
    return states[update.callback_query.data](update, context)


def settings_cancel_handler(update: Update, context: CallbackContext):
    return SETTINGS


def start_handler(update: Update, context: CallbackContext):
    buttons = [
        [
            InlineKeyboardButton(text='Settings', callback_data=SETTINGS)
        ]
    ]
    keyboard = InlineKeyboardMarkup(buttons)

    update.message.reply_text(text='What do you want to do?',
                              reply_markup=keyboard)
    return SETTINGS


def print_handler(update: Update, context: CallbackContext):
    text = 'Send document or picture to print.\n' \
           'Print /settings to go back to settings'
    update.callback_query.edit_message_text(text=text)

    return PRINT


def printer_await():
    command = 'lpq'
    while True:
        res = subprocess.run(
            args=command.split(),
            check=True,
            stdout=subprocess.PIPE,
            text=True
        )
        time.sleep(2)
        if res.stdout.find('printing') == -1:
            break


def print_document(update: Update, context: CallbackContext):
    print('printing doc')
    name = update.message.document.file_name

    if name.endswith('.docx'):
        print_docx(update.message.document)
    else:
        print_normal_file(update.message.document)

    return PRINT


def print_docx(document: telegram.Document):
    new_path = f'./tmp/{document.file_name.replace(" ", "_")}'

    open(new_path, 'wb').close()
    with open(new_path, 'wb') as f:
        document.get_file().download(out=f)
    try:
        command = f'libreoffice --pt CLP-320-Series {new_path}'

        res = subprocess.run(
            args=command.split(),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        print(res.stdout)
        print(res.stderr)
    except Exception as e:
        print(e)

    printer_await()
    os.remove(new_path)


def print_normal_file(document: telegram.Document):
    new_path = f'./tmp/{document.file_name.replace(" ", "_")}'

    open(new_path, 'wb').close()
    with open(new_path, 'wb') as f:
        document.get_file().download(out=f)
    try:
        orientation = 3 if settings[ORIENTATION] is Orientation.portrait else 4
        command = f'lpr -# {settings[COPIES]} ' \
                  f'-o orientaion-requested={orientation} ' \
                  f'-P CLP-320-Series ' \
                  f'{new_path}'

        res = subprocess.run(
            args=command.split(),
            check=True,
            stdout=subprocess.PIPE,
            text=True
        )
        print(res)
    except Exception as e:
        print(e)

    printer_await()
    os.remove(new_path)


def print_picture(update: Update, context: CallbackContext):
    print('printing pic')
    photos = update.message.photo
    photos: telegram.PhotoSize
    biggest_photo = max(photos, key=lambda photo: photo.file_size)
    print_photo(biggest_photo)

    return PRINT


def print_photo(photo: telegram.PhotoSize):
    new_path = f'./tmp/{photo.file_id.replace(" ", "_")}.jpg'

    open(new_path, 'wb').close()
    try:
        with open(new_path, 'wb') as f:
            photo.get_file().download(out=f)
    except Exception as e:
        print(e)
    try:
        orientation = 3 if settings[ORIENTATION] is Orientation.portrait else 4
        command = f'lpr -# {settings[COPIES]} ' \
                  f'-o orientaion-requested={orientation} ' \
                  f'-P CLP-320-Series ' \
                  f'{new_path}'

        res = subprocess.run(
            args=command.split(),
            check=True,
            stdout=subprocess.PIPE,
            text=True
        )
        print(res)
    except Exception as e:
        print(e)

    printer_await()

    os.remove(new_path)


def good_bye_handler(update: Update, context: CallbackContext):
    pass


def main():
    try:
        os.mkdir('./tmp')
    except FileExistsError:
        pass

    updater = Updater(token=TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    orientation_conv = CallbackQueryHandler(
        select_orientation,
        pattern=rf'^({PORTRAIT})|({LANDSCAPE})$'
    )

    copies_conv = MessageHandler(
        ~Filters.command,
        callback=set_copies
    )

    scale_conv = MessageHandler(
        ~Filters.command,
        callback=set_scale
    )

    print_pic = MessageHandler(Filters.photo,
                               callback=print_picture)
    print_doc = MessageHandler(Filters.document,
                               callback=print_document)
    back_to_settings = CommandHandler('settings',
                                      callback=settings_handler)

    settings_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(settings_handler,
                                 pattern=rf'^{SETTINGS}$')
        ],
        states={
            CHOOSE_SETTING: [
                CallbackQueryHandler(choose_setting,
                                     pattern=f'^({SETTING_SCALE})|'
                                             f'({SETTING_COPIES})|'
                                             f'({SELECTING_ORIENTATION})|'
                                             f'({PRINT})$')
            ],
            SETTING_SCALE: [scale_conv],
            SETTING_COPIES: [copies_conv],
            SELECTING_ORIENTATION: [orientation_conv],
            PRINT: [print_doc, print_pic, back_to_settings]
        },
        fallbacks=[
            CommandHandler('cancel', settings_cancel_handler)
        ],
        map_to_parents={
            SETTINGS: SETTINGS
        }
    )

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start_handler)
        ],
        states={
            SETTINGS: [
                settings_conv
            ]
        },
        fallbacks=[
            CommandHandler('cancel', good_bye_handler),
            settings_conv
        ]
    )

    dispatcher.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
