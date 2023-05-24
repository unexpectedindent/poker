import typing

import cards
from exceptions import ExceededValueError, InsufficientRaiseError, MinRaiseError


class Player:
    FOLD = 0
    ACTIVE = 1
    ALL_IN = 2
    TYPES = {'HUMAN': 1, 'BOT': -1}
    ROLES = ['DEALER', 'LITTLE_BLIND', 'BIG_BLIND', 'NAN']
    OPTIONS = ('CHECK', 'CALL', 'RAISE', 'FOLD', 'ALL-IN')
    STATUS = {0: 'FOLD', 1: 'ACTIVE', 2: 'ALL-IN'}

    def __init__(self, is_bot: bool, player_id: int, wealth: int, name: str = None) -> None:
        self.status = self.ACTIVE
        self.is_bot = is_bot
        self.player_id = player_id
        self.name = name
        self._is_dealer = False
        self.wealth = wealth
        self.round_state = 'wait'
        self.possible_actions = list(self.OPTIONS)
        self.current_bid = 0
        self.role = 'NAN'
        self.hand = None

    # @property
    # def hand(self):
    #     return self._get_hand()

    # def _get_hand(self):


    def give_hand(self, two_cards):
        self.hand = two_cards

    def calculate_p_win(self, players_count, table=None):
        if table:
            table = list(table)
        return cards._calculate_p_win(list(self.hand), players_count, table, n=100000)

    def set_role(self, role):
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

    def action(self, deal, act, value=0):
        if act == 'FOLD':
            self.status = self.FOLD
            # deal.players.remove(self)
            deal.active_players_count -= 1
        else:
            if act == 'CALL':
                value = min(deal.current_bid, self.wealth)
            elif act == 'ALL-IN':
                value = self.wealth
            if value == self.wealth:
                self.status = self.ALL_IN
                deal.active_players_count -= 1
            elif value > self.wealth:
                raise ExceededValue()
            elif self.current_bid + value < deal.current_bid + deal.blind:
                if not (
                        (self.is_little_blind and value == deal.blind // 2)
                        or (self.is_big_blind and value == deal.blind)
                ):
                    raise InsufficientRaiseError()
            elif value < deal.blind:
                raise MinRaiseError()
            deal.bank += value
            self.wealth -= value
            self.current_bid += value
            deal.current_bid = max(deal.current_bid, self.current_bid)

    def info(self):
        return str(self) + '\nWealth: {}; Status: {}; Bid: {}; Role: {}'.format(self.wealth, self.STATUS[self.status],
                                                                                self.current_bid, self.role)

    def __repr__(self):
        return f'Player({self.name})'

