import typing

import actions
from actions import ACTIONS
import cards
from cards import _calculate_max_value, _calculate_p_win, rank_to_cards
from exceptions import ExceededValueError, InsufficientRaiseError, MinRaiseError
# from pokerapp import Deal
import player_status


class Player:
    TYPES = {'HUMAN': 1, 'BOT': -1}
    ROLES = ['DEALER', 'LITTLE_BLIND', 'BIG_BLIND', 'NAN']
    OPTIONS = ('CHECK', 'CALL', 'RAISE', 'FOLD', 'ALL-IN')
    STATUS = {player_status.FOLD: 'FOLD', player_status.ACTIVE: 'ACTIVE',
              player_status.ALL_IN: 'ALL-IN'}

    def __init__(self, is_bot: bool, player_id: int, wealth: int, name: str = None) -> None:
        """
        Статус игрока может принимать целое число от 0 до 2, где
            0 - игрок не участвует в раздаче (сбросил карты или не имеет
            фишек на начало раздачи);
            1 - игрок полноценно участвует в раздаче;
            2 - игрок находится в состоянии ва-банк.

        :param is_bot:
        :param player_id:
        :param wealth:
        :param name:
        """
        self.status = player_status.ACTIVE
        self.is_bot = is_bot
        self.player_id = player_id
        self.name = name
        self._is_dealer = False
        self.wealth = wealth
        self.possible_actions = list(self.OPTIONS)
        self.current_bid = 0
        self.role = 'NAN'
        self.hand = None
        self.ambition = 0
        self.wealth_change = 0

    def give_hand(self, two_cards):
        self.hand = two_cards

    def calculate_p_win(self, players_count, table=None):
        if table:
            table = list(table)
        return _calculate_p_win(list(self.hand), players_count, table, n=50000)

    def p_win(self, deal):
        return self.calculate_p_win(
            deal.active_players_count + deal.all_in_players_count,
            deal.table if deal.table else None
        )

    def set_role(self, role: str = 'NAN'):
        if role in self.ROLES:
            self.role = role
        else:
            self.role = 'NAN'

    def set_dealer(self):
        self._is_dealer = True

    @property
    def is_little_blind(self):
        return self.role == 'LITTLE_BLIND'

    @property
    def is_big_blind(self):
        return self.role == 'BIG_BLIND'

    @property
    def is_dealer(self):
        return self._is_dealer

    def action(self, deal, act: str, value: int = 0):
        """

        :param deal: раздача;
        :param act: действие из списка: 'FOLD', 'CHECK', 'CALL', 'RAISE',
            'ALL-IN', 'BLIND';
        :param value:
        :return:
        """
        if not value:
            value = self.current_bid
        if act == actions.FOLD:
            self.status = player_status.FOLD
        elif act == actions.BLIND:
            value = min(value, self.wealth)
            self.current_bid = value
            deal.bank += value
            self.wealth_change -= value
        else:
            if act == actions.CALL:
                value = min(deal.current_bid, self.wealth)
            elif act == actions.ALL_IN:
                value = self.wealth
            elif value > self.wealth:
                raise ExceededValueError()
            if all((
                act == actions.RAISE,
                value < deal.current_bid + deal.blind,
                value < self.wealth
            )):
                raise MinRaiseError()
        deal.bank += (value - self.current_bid)
        self.wealth_change -= (value - self.current_bid)
        self.current_bid = value
        deal.current_bid = max(deal.current_bid, self.current_bid)
        if value == self.wealth:
            self.status = player_status.ALL_IN
            deal.active_players_count -= 1
            deal.all_in_players_count += 1

    def info(self, deal):
        return '\n'.join([
            str(self),
            'Wealth: {}; Status: {}; Current bid: {}; Role: {}'.format(
                self.wealth,
                self.STATUS[self.status],
                self.current_bid,
                self.role,
                # self.p_win(deal)
            ),
            str(cards.Cards([cards.Card(*card) for card in self.hand]))
        ])

    def summary(self, deal):
        return rank_to_cards(self.combination(deal))

    def show_hand(self):
        print(cards.Cards([cards.Card(*card) for card in self.hand]))

    def combination(self, deal):
        return _calculate_max_value(list(self.hand) + list(deal.table))

    def __repr__(self):
        return f'Player({self.name})'
