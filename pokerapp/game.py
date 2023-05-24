import random
import typing

import cards
from player import Player
from exceptions import ExceededValueError, InsufficientRaiseError, MinRaiseError


class Deal:
    """
    Объект - раздача.
    Параметры:
    :players: участвующие игроки - все игроки, участвующие в игре и имеющие
        положительный баланс.
    :small_blind_rate: обязательная ставка игрока, начинающего торги. Равна
        половине минимального шага изменения ставки в раунде.
    :limit: максимальное количество активного повышения ставки в игре -
        ограничение на количество торгов в рамках одного раунда сдачи.
    :bot_limit: максимальное количество активного повышения ставки в игре
        для игрока-бота.
    """

    def __new__(cls,
        players: typing.List[Player],
        small_blind_rate: int,
        limit: int = 10,
        bot_limit: int = 10
    ):
        self = object.__new__(cls)
        deck = cards._generate_deck()
        self.bank = 0
        self.current_bid = 0
        self.players = players
        self.stage = 0  # pre-flop
        self.limit = limit
        self.bot_limit = bot_limit

        # Назначаем игроков с Little и Big Blind
        self.players[0].set_role('LITTLE_BLIND')
        self.players[1].set_role('BIG_BLIND')
        self.players[-1].set_dealer()

        # Начальное количество участников сдачи
        players_count = len(self.players)
        self.active_players_count = players_count

        # Раздача карт
        cards_to_hands = {player: [] for player in range(players_count)}
        for _ in range(2):
            for player in range(players_count):
                cards_to_hands[player].append(deck.pop(0))
        self._deck = deck
        for player in range(players_count):
            players[player].give_hand(tuple(cards_to_hands[player]))

        # Обязательные ставки
        self.blind = small_blind_rate * 2
        self.players[0].action(self, 'RAISE', small_blind_rate)
        self.players[1].action(self, 'RAISE', self.blind)

        # Начало торгов
        self.trade_round = 0
        self.pre_flop()
        return self

    def action_query(self, player):
        # TODO: Переделать input на ТГ-бота
        actions = {'0': 'FOLD', '1': 'CHECK', '2': 'CALL', '3': 'RAISE', '4': 'ALL-IN'}
        msg = 'Текущая ставка: {}; Ваша текущая ставка: {}; blind: {}.\nВаш ход (0 - fold{}'
        is_valid = False
        while not is_valid:
            if self.trade_round == self.limit:
                action = input(msg.format(self.currend_bid, player.current_bid, self.blind, ', 1 - check, 2 - call): '))
                if action not in ('0', '1', '2'):
                    print('Введите число - один из предложенных варианов.')
                else:
                    is_valid = True
            elif self.current_bid > player.current_bid:
                action = input(msg.format(self.currend_bid, player.current_bid, self.blind,
                                          ', 2 - call, 3 - raise, 4 - all-in): '))
                if action not in ('0', '2', '3', '4'):
                    print('Введите число - один из предложенных варианов.')
                else:
                    is_valid = True
            else:
                action = input(msg.format(self.currend_bid, player.current_bid, self.blind,
                                          ', 1 - check, 2 - call, 3 - raise, 4 - all-in): '))
                if action not in ('0', '1', '2', '3', '4'):
                    print('Введите число - один из предложенных варианов.')
                else:
                    is_valid = True
        is_valid = False
        if action == '3':
            while not is_valid:
                bid = int(input(
                    f'Введите свою ставку (целое число от {self.blind} до {player.wealth}): '
                ))
                try:
                    player.action(self, actions[action], bid)
                    is_valid = True
                except ExceededValueError:
                    print('У Вас нет столько фишек.')
                except MinRaiseError:
                    print('Минимальное повышение равно blind.')
                except InsufficientRaiseError:
                    print('Ставка должна быть выше текущей ставки в игре.')
                except:
                    print('Что-то пошло не так, попробуйте еще раз.')
                else:
                    player.action(self, actions[action])

    def first_trading(self, players: typing.List[Player]) -> bool:
        for player in players:
            if player.status == 1:
                self.action_query(player)
        self.trade_round = + 1
        bids = set([player.current_bid for player in players if player.status == 1])
        return len(bids) == 1

    def trading(self):
        is_over = False
        while not is_over:
            for player in self.players:
                if player.status == 1:
                    self.action_query(player)
            self.trade_round = + 1
            bids = set([player.current_bid for player in self.players if player.status == 1])
            if len(bids) == 1:
                is_over = True

    def pre_flop(self):
        """
        В первом раунде торгов инициатором является игрок, правый от
        большого блайнда, в остальных раундах торговлю начинает первый
        игрок (малый блайнд).
        При этом если в сдаче участвует 2 игрока, торги также начинает малый
        блайнд.
        """
        if len(self.players) > 2:
            players = self.players[2:] + self.players[:2]
            if not self.first_trading(players):
                self.trading()
        else:
            self.trading()
        if self.active_players_count == 1:
           self.define_winner()
        else:
            self.show_flop()

    def show_flop(self):
        self._deck.pop(0)
        self.table = []
        for _ in range(3):
            self.table.append(self._deck.pop(0))
        self.trading()
        if self.active_players_count == 1:
            self.define_winner()
        else:
            self.show_turn()

    def show_turn(self):
        self._deck.pop(0)
        self.table.append(self._deck.pop(0))
        self.trading()
        if self.active_players_count == 1:
            self.define_winner()
        else:
            self.show_river()

    def show_river(self):
        self._deck.pop(0)
        self.table.append(self._deck.pop(0))
        self.trading()
        self.define_winner()

    def define_winner(self):
        pass


class Game:
    def init(self, players: list, small_blind_rate: int):
        self.deal = 0
        random.shuffle(players)
        self.players = players
        self.small_blind_rate = small_blind_rate
        self.new_deal()

    def new_deal(self):
        self.deal += 1
        self.players = [player for player in self.players if player.wealth > 0]
        deal = Deal(self.players, self.small_blind_rate)