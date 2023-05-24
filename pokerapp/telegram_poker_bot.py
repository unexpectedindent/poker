import logging
import logging.config
import os

import requests

from telegram import ReplyKeyboardMarkup
from telegram.ext import (CommandHandler, Filters,
                          MessageHandler, Updater)

from config import LOGGING_CONFIG, TELEGRAM_TOKEN


logger = logging.getLogger(__name__)


def wake_up(update, context):
    chat = update.effective_chat
    name = update.message.chat.first_name
    button = ReplyKeyboardMarkup(
        [['/Calculate']],
        rresize_keyboard=True,
        one_time_keyboard=True,
        remove_keyboard=True
    )
    logging.info(f'Activated. {chat.id} {name}')

    context.bot.send_message(
        chat_id=chat.id,
        text='Хотите рассчитать вероятность не проиграть раздачу?',
        reply_markup=button
    )


def first_card(update, context):
    chat = update.effective_chat
    button = ReplyKeyboardMarkup(
        [
            [v + suit for v in [str(i) for i in range(2, 11)]]
            for suit in ['\u2664', '\u2665', '\u2666', '\u2667']
        ] + [['>>']],
        rresize_keyboard=True,
        one_time_keyboard=True,
        remove_keyboard=True
    )
    logging.info(f'Selection suit. {chat.id}')
    context.bot.send_message(
        chat_id=chat.id,
        text='Выберите первую карту в руке',
        reply_markup=button
    )


def second_card(update, context):
    chat = update.effective_chat
    button = ReplyKeyboardMarkup(
        [
            [v + suit for v in [str(i) for i in range(2, 11)]]
            for suit in ['\u2664', '\u2665', '\u2666', '\u2667']
        ] + [['>>']],
        rresize_keyboard=True,
        one_time_keyboard=True,
        remove_keyboard=True
    )
    logging.info(f'Selection suit. {chat.id}')

    context.bot.send_message(
        chat_id=chat.id,
        text='Выберите вторую карту в руке',
        reply_markup=button
    )


def message_handler(update, context):
    if update.message.text == '>>':
        button = ReplyKeyboardMarkup(
            [
                [v + suit for v in list('JQKA')]
                for suit in ['\u2664', '\u2665', '\u2666', '\u2667']
            ] + [['<<']],
            rresize_keyboard=True,
            one_time_keyboard=True,
            remove_keyboard=True
        )
        chat = update.effective_chat
        context.bot.send_message(
            chat_id=chat.id,
            text='Выберите карту',
            reply_markup=button
        )
    elif update.message.text == '<<':
        chat = update.effective_chat
        button = ReplyKeyboardMarkup(
            [
                [v + suit for v in [str(i) for i in range(2, 11)]]
                for suit in ['\u2664', '\u2665', '\u2666', '\u2667']
            ] + [['>>']],
            rresize_keyboard=True,
            one_time_keyboard=True,
            remove_keyboard=True
        )
        logging.info(f'Selection suit. {chat.id}')

        context.bot.send_message(
            chat_id=chat.id,
            text='Выберите вторую карту в руке',
            reply_markup=button
        )


def main():
    updater = Updater(token=TELEGRAM_TOKEN)

    updater.dispatcher.add_handler(CommandHandler('start', wake_up))
    updater.dispatcher.add_handler(CommandHandler('Calculate', first_card))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, message_handler))
    # updater.dispatcher.add_handler(CommandHandler('3\u2664', second_card))

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    logging.config.dictConfig(LOGGING_CONFIG)
    main()
