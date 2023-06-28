import collections
import logging
import logging.config
import os

import requests

from telegram import ReplyKeyboardMarkup
from telegram.ext import (CommandHandler, Filters,
                          MessageHandler, Updater)

from cards import _calculate_p_win, Card, SUIT, SUIT_R, VALUE, VALUE_R
from config import LOGGING_CONFIG, TELEGRAM_TOKEN



logger = logging.getLogger(__name__)


class State:
    def __init__(self):
        self.users = {}


class PokerBot(object):
    def __init__(self, token):
        self.updater = Updater(token=token)

        self.updater.dispatcher.add_handler(
            CommandHandler('start', self.wake_up)
        )
        self.updater.dispatcher.add_handler(
            CommandHandler('calculate', self.init_calculation)
        )
        self.updater.dispatcher.add_handler(
            MessageHandler(Filters.text, self.message_handler)
        )
        self.cache = {}
        self.state = State()

    def start(self):
        self.updater.start_polling()

    def message_handler(self, update, context):
        chat_id = update.message.chat_id
        incoming_message = update.message.text
        logging.info(f'{chat_id}, {incoming_message}')
        if not self.state.users.get(chat_id):
            return self.init_calculation(update, context)

        state = self.state.users[chat_id].get('step') or 0
        cards = [
            v + suit for v in [str(i) for i in range(2, 11)] + list('JQKA')
            for suit in ['\u2664', '\u2665', '\u2666', '\u2667']
        ]
        if state == 0:
            if incoming_message == '>>':
                button = ReplyKeyboardMarkup(
                    [
                        [v + suit for v in ['10'] + list('JQKA')]
                        for suit in ['\u2664', '\u2665', '\u2666', '\u2667']
                    ] + [['<<']],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                    remove_keyboard=True
                )
                context.bot.send_message(
                    chat_id=chat_id,
                    text='Выберите первую карту',
                    reply_markup=button
                )
            elif incoming_message == '<<':
                button = ReplyKeyboardMarkup(
                    [
                        [v + suit for v in list('23456789')]
                        for suit in ['\u2664', '\u2665', '\u2666', '\u2667']
                    ] + [['>>']],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                    remove_keyboard=True
                )
                context.bot.send_message(
                    chat_id=chat_id,
                    text='Выберите первую карту',
                    reply_markup=button
                )
            elif incoming_message in cards:
                button = ReplyKeyboardMarkup(
                    [
                        [v + suit for v in list('23456789')]
                        for suit in ['\u2664', '\u2665', '\u2666', '\u2667']
                    ] + [['>>']],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                    remove_keyboard=True
                )
                context.bot.send_message(
                    chat_id=chat_id,
                    text='Выберите вторую карту',
                    reply_markup=button
                )
                self.state.users[chat_id]['step'] = 1
                logging.info(f'{chat_id}, step 1: {incoming_message}')
                self.state.users[chat_id]['1st_card'] = (
                    VALUE_R[incoming_message[:-1]], SUIT_R[incoming_message[-1]]
                )
        elif state == 1:
            if incoming_message == '>>':
                button = ReplyKeyboardMarkup(
                    [
                        [v + suit for v in ['10'] + list('JQKA')]
                        for suit in ['\u2664', '\u2665', '\u2666', '\u2667']
                    ] + [['<<']],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                    remove_keyboard=True
                )
                context.bot.send_message(
                    chat_id=chat_id,
                    text='Выберите вторую карту',
                    reply_markup=button
                )
            elif incoming_message == '<<':
                button = ReplyKeyboardMarkup(
                    [
                        [v + suit for v in list('23456789')]
                        for suit in ['\u2664', '\u2665', '\u2666', '\u2667']
                    ] + [['>>']],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                    remove_keyboard=True
                )
                context.bot.send_message(
                    chat_id=chat_id,
                    text='Выберите вторую карту',
                    reply_markup=button
                )
            elif incoming_message in cards:
                button = ReplyKeyboardMarkup(
                    [[str(i) for i in range(2, 9)]],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                    remove_keyboard=True
                )
                context.bot.send_message(
                    chat_id=chat_id,
                    text='Введите количество игроков',
                    reply_markup=button
                )
                self.state.users[chat_id]['step'] = 2
                logging.info(f'{chat_id}, step 2: {incoming_message}')
                self.state.users[chat_id]['2nd_card'] = (
                    VALUE_R[incoming_message[:-1]], SUIT_R[incoming_message[-1]]
                )
        elif state == 2:
            if incoming_message in [str(i) for i in range(2, 9)]:
                button = ReplyKeyboardMarkup(
                    [[str(i) for i in range(0, 4)]],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                    remove_keyboard=True
                )
                context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        'Выберите стадию игры:\n0 - пре-флоп (на столе нет карт)\n'
                        '1 - флоп (на столе 3 карты)\n2 - тёрн (на столе 4 карты)\n'
                        '3 - ривер (на столе 5 карт)'
                    ),
                    reply_markup=button
                )
                self.state.users[chat_id]['step'] = 3
                logging.info(f'{chat_id}, step 3. Игроков {incoming_message}')
                self.state.users[chat_id]['n_players'] = int(incoming_message)

                self.state.users[chat_id]['turn'] = None
                self.state.users[chat_id]['river'] = None
        elif state == 3:
            if incoming_message == '0':
                context.bot.send_message(chat_id=chat_id, text=f'Производится расчет...')
                p = _calculate_p_win(
                    (self.state.users[chat_id]['1st_card'], self.state.users[chat_id]['2nd_card']),
                    self.state.users[chat_id]['n_players']
                )
                text = 'Игроков: {}. Рука: {}{}. P = {:.04}%'.format(
                    self.state.users[chat_id]['n_players'],
                    Card(*self.state.users[chat_id]['1st_card']),
                    Card(*self.state.users[chat_id]['2nd_card']),
                    p
                )
                context.bot.send_message(
                    chat_id=chat_id,
                    text=text
                )
                logging.info(
                    '{}, step 3. Игроков {}. Стадия 0. Рука: {}{}. P = {:.04}%'.format(
                        chat_id,
                        self.state.users[chat_id]['n_players'],
                        Card(*self.state.users[chat_id]['1st_card']),
                        Card(*self.state.users[chat_id]['2nd_card']),
                        p
                    )
                )
                self.state.users[chat_id] = {}
                button = ReplyKeyboardMarkup(
                    [['/calculate']],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                    remove_keyboard=True
                )
                context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        'Если хотите продолжить, Вам нужно последовательно задать следующие параметры:\n'
                        '1. Первую карту в руке.\n2. Вторую карту в руке.\n'
                        '3. Количество игроков.\n4. Стадию игры, где 0 - пре-флоп '
                        '(на столе нет карт), 1 - флоп (на столе 3 карты), 2 - тёрн'
                        ' (на столе 4 карты), 3 - ривер (на столе 5 карт).\n'
                        '5. Поочередно указать все карты на столе, если они есть.\n'
                        '6. Указать другие карты, которые вам известны - они будут '
                        'убраны из генерации.'
                    ),
                    reply_markup=button
                )
            elif incoming_message in ('1', '2', '3'):
                self.state.users[chat_id]['stage'] = int(incoming_message)
                self.state.users[chat_id]['step'] = 4
                self.state.users[chat_id]['table'] = []
                button = ReplyKeyboardMarkup(
                    [
                        [v + suit for v in list('23456789')]
                        for suit in ['\u2664', '\u2665', '\u2666', '\u2667']
                    ] + [['>>']],
                    resize_keyboard=True,
                    one_time_keyboard=True,
                    remove_keyboard=True
                )
                context.bot.send_message(
                    chat_id=chat_id,
                    text='Выберите карту',
                    reply_markup=button
                )
        elif state == 4:
            if len(self.state.users[chat_id]['table']) < self.state.users[chat_id]['stage'] + 2:
                if incoming_message == '>>':
                    button = ReplyKeyboardMarkup(
                        [
                            [v + suit for v in ['10'] + list('JQKA')]
                            for suit in ['\u2664', '\u2665', '\u2666', '\u2667']
                        ] + [['<<']],
                        resize_keyboard=True,
                        one_time_keyboard=True,
                        remove_keyboard=True
                    )
                    context.bot.send_message(
                        chat_id=chat_id,
                        text='Выберите вторую карту',
                        reply_markup=button
                    )
                elif incoming_message == '<<':
                    button = ReplyKeyboardMarkup(
                        [
                            [v + suit for v in list('23456789')]
                            for suit in ['\u2664', '\u2665', '\u2666', '\u2667']
                        ] + [['>>']],
                        resize_keyboard=True,
                        one_time_keyboard=True,
                        remove_keyboard=True
                    )
                    context.bot.send_message(
                        chat_id=chat_id,
                        text='Выберите вторую карту',
                        reply_markup=button
                    )
                elif incoming_message in cards:
                    self.state.users[chat_id]['table'] += [
                        (VALUE_R[incoming_message[:-1]], SUIT_R[incoming_message[-1]])
                    ]
                    if len(self.state.users[chat_id]['table']) == self.state.users[chat_id]['stage'] + 2:
                        context.bot.send_message(chat_id=chat_id, text=f'Производится расчет...')
                        p = _calculate_p_win(
                            (self.state.users[chat_id]['1st_card'], self.state.users[chat_id]['2nd_card']),
                            self.state.users[chat_id]['n_players'], self.state.users[chat_id]['table']
                        )
                        text = 'Игроков: {}. Рука: {}{}. Стол: {}.\nP = {:.04}%'.format(
                            self.state.users[chat_id]['n_players'],
                            Card(*self.state.users[chat_id]['1st_card']),
                            Card(*self.state.users[chat_id]['2nd_card']),
                            ''.join([str(Card(*i)) for i in self.state.users[chat_id]['table']]),
                            p
                        )
                        context.bot.send_message(
                            chat_id=chat_id,
                            text=text
                        )
                        logging.info(
                            '{}, step 3. Игроков {}. Стадия {}. Рука: {}{}. Стол: {}. P = {:.04}%'.format(
                                chat_id,
                                self.state.users[chat_id]['n_players'],
                                self.state.users[chat_id]['stage'],
                                Card(*self.state.users[chat_id]['1st_card']),
                                Card(*self.state.users[chat_id]['2nd_card']),
                                ''.join([str(Card(*i)) for i in self.state.users[chat_id]['table']]),
                                p
                            )
                        )
                        self.state.users[chat_id] = {}
                        button = ReplyKeyboardMarkup(
                            [['/calculate']],
                            resize_keyboard=True,
                            one_time_keyboard=True,
                            remove_keyboard=True
                        )
                        context.bot.send_message(
                            chat_id=chat_id,
                            text=(
                                'Если хотите продолжить, Вам нужно последовательно задать следующие параметры:\n'
                                '1. Первую карту в руке.\n2. Вторую карту в руке.\n'
                                '3. Количество игроков.\n4. Стадию игры, где 0 - пре-флоп '
                                '(на столе нет карт), 1 - флоп (на столе 3 карты), 2 - тёрн'
                                ' (на столе 4 карты), 3 - ривер (на столе 5 карт).\n'
                                '5. Поочередно указать все карты на столе, если они есть.\n'
                                '6. Указать другие карты, которые вам известны - они будут '
                                'убраны из генерации.'
                            ),
                            reply_markup=button
                        )
                    else:
                        button = ReplyKeyboardMarkup(
                            [
                                [v + suit for v in list('23456789')]
                                for suit in ['\u2664', '\u2665', '\u2666', '\u2667']
                            ] + [['>>']],
                            resize_keyboard=True,
                            one_time_keyboard=True,
                            remove_keyboard=True
                        )
                        context.bot.send_message(
                            chat_id=chat_id,
                            text='Выберите карту',
                            reply_markup=button
                        )

    def wake_up(self, update, context):
        chat_id = update.message.chat_id
        print(update.message)
        print(self.state)
        logging.info(f'{chat_id}, {update.message.text}')
        # удаляем состояние текущего чата, если оно есть
        self.state.users.pop(chat_id, None)
        self.state.users[chat_id] = {}
        name = update.message.chat.first_name
        last_name = update.message.chat.last_name
        button = ReplyKeyboardMarkup(
            [['/calculate']],
            resize_keyboard=True,
            one_time_keyboard=True,
            remove_keyboard=True
        )
        logging.info(f'Activated. {chat_id}: {name} {last_name}')

        context.bot.send_message(
            chat_id=chat_id,
            text=(
                'Вам нужно последовательно задать следующие параметры:\n'
                '1. Первую карту в руке.\n2. Вторую карту в руке.\n'
                '3. Количество игроков.\n4. Стадию игры, где 0 - пре-флоп '
                '(на столе нет карт), 1 - флоп (на столе 3 карты), 2 - тёрн'
                ' (на столе 4 карты), 3 - ривер (на столе 5 карт).\n'
                '5. Поочередно указать все карты на столе, если они есть.\n'
                '6. Указать другие карты, которые вам известны - они будут '
                'убраны из генерации.'
            ),
            reply_markup=button
        )

    def init_calculation(self, update, context):
        chat_id = update.message.chat_id
        logging.info(f'{chat_id}, {update.message.text}')
        self.state.users[chat_id] = {}
        self.state.users[chat_id]['step'] = 0
        button = ReplyKeyboardMarkup(
            [
                [v + suit for v in list('23456789')]
                for suit in ['\u2664', '\u2665', '\u2666', '\u2667'] #['♦️', '♥️', '♣️', '♠️'] # ['\u2664', '\u2665', '\u2666', '\u2667']
            ] + [['>>']],
            resize_keyboard=True,
            one_time_keyboard=True,
            remove_keyboard=True
        )
        context.bot.send_message(
            chat_id=chat_id,
            text='Выберите первую карту',
            reply_markup=button
        )


if __name__ == '__main__':
    logging.config.dictConfig(LOGGING_CONFIG)
    poker_bot = PokerBot(TELEGRAM_TOKEN)
    poker_bot.start()
