import logging
import logging.config
import random
import typing

import actions
from actions import ACTIONS
from cards import _generate_deck, _calculate_max_value, Card, Cards
from config import LOGGING_CONFIG
import game_stage
from exceptions import ExceededValueError, InsufficientRaiseError, MinRaiseError
from player import Player
import player_status


logger = logging.getLogger(__name__)

# Описание логики игры
# 1. Генерация игры:
# 1.1. (Done) Игроки
# 1.1.1. (Done) Бот / не бот
# 1.1.2. (Done) id
# 1.1.3. (Done) Богатство
# 1.1.4. (Done) Имя
# 1.2. Настройки
# 1.2.1. (Done) Размер малого блайнда
# 1.2.2. Количество раздач до увеличения блайндов
# 1.2.3. Тип увеличения блайндов (фиксированные значения, увеличение на фиксированные значения, кратное увеличение)
# 1.2.4. Параметры увеличения блайндов
# 1.2.5. (Done) Ограничение на количество ре-рейзов при торговле на раздаче
# 1.2.6. Ограничение на количество раздач в игре
# 1.2.7. Ограничение на продолжительность игры по времени
# 2. Первая раздача


class Deal:
    """
    Объект - раздача.
    Параметры:
    :players: участвующие игроки - все игроки, участвующие в игре и имеющие
        положительный баланс.
    :small_blind_rate: обязательная ставка игрока, начинающего торги. Равна
        половине минимального шага изменения ставки в раунде.
    :limit: максимальное количество активного повышения ставки в игре -
        ограничение на количество торгов в рамках одного раунда раздачи.
    :bot_limit: максимальное количество активного повышения ставки в игре
        для игрока-бота.
    """

    def __new__(
        cls,
        players: typing.List[Player],
        small_blind_rate: int,
        raise_personal_limit: int | None = None,
        trade_rounds_limit: int | None = None
    ):
        self = object.__new__(cls)
        deck = _generate_deck()
        self.bank = 0
        self.current_bid = 0
        self.players = players

        self.raise_personal_limit = raise_personal_limit
        self.trade_rounds_limit = trade_rounds_limit
        self.raise_personal = {player: 0 for player in self.players}
        self.trade_rounds = 0

        # pre-flop
        self.stage = game_stage.PRE_FLOP
        self.table = []

        # Назначаем игроков с Little и Big Blind
        self.players[0].set_role('LITTLE_BLIND')
        self.players[1].set_role('BIG_BLIND')
        # self.players[-1].set_dealer()

        # Начальное количество участников раздачи
        players_count = len(self.players)
        self.active_players_count = players_count
        self.players_in_count = players_count
        self.all_in_players_count = 0
        self.folds_count = 0

        # Раздача карт
        cards_to_hands = {player: [] for player in range(players_count)}
        for _ in range(2):
            for player in range(players_count):
                cards_to_hands[player].append(deck.pop(0))
        self._deck = deck
        self.p_win = {}
        logging.info(f'Stage: {game_stage.STAGE[self.stage]}')
        for player_order, player in enumerate(self.players):
            player.give_hand(two_cards=tuple(cards_to_hands[player_order]))
            self.p_win[player] = player.p_win(self)
            logging.info(
                f'Player{player_order} {player.name}: wealth: {player.wealth}, '
                f'status: {player.STATUS[player.status]}, '
                f'hand: {Card(*player.hand[0])} {Card(*player.hand[1])}, '
                f'role: {player.role}, %win: {self.p_win[player]}%'
            )

        # Обязательные ставки
        self.blind = small_blind_rate * 2
        self.players[0].action(
            self, act=actions.BLIND, value=small_blind_rate
        )
        logging.info(
            f'Player {players[0].name}: order: 0, wealth: {players[0].wealth}, '
            f'hand: {Card(*players[0].hand[0])} {Card(*players[0].hand[1])}, '
            f'role: {players[0].role}, %win: {self.p_win[self.players[0]]}%, '
            f'action: SMALL BLIND, bid: {players[0].current_bid}, '
            f'wealth change: {players[0].wealth_change}'
        )
        logging.info(f'Bank: {self.bank}, current bid: {self.current_bid}')

        self.players[1].action(self, act=actions.BLIND, value=self.blind)
        logging.info(
            f'Player {players[1].name}: order: 1, wealth: {players[1].wealth}, '
            f'hand: {Card(*players[1].hand[0])} {Card(*players[1].hand[1])}, '
            f'role: {players[1].role}, %win: {self.p_win[self.players[1]]}%,  '
            f'action: BIG BLIND, bid: {players[1].current_bid}, '
            f'wealth change: {players[1].wealth_change}'
        )
        logging.info(f'Bank: {self.bank}, current bid: {self.current_bid}')
        # Начало торгов
        self.trade_round = 0
        self.pre_flop()
        self.winner = None
        return self

    def current_stats(self, player: Player):
        """
        Текущая ставка в игре; текущая ставка игрока; количество игроков, с
        которыми ведется торг; максимальная ставка, имеющая смысл
        :return:
        """
        pass

    def action_query(self, player: Player) -> None:
        """
        Запрос к игроку-пользователю (не боту) на действие.
        Функция
        :param player: объект игрока
        """
        # TODO: Переделать input на ТГ-бота
        # actions = {'0': 'FOLD', '1': 'CHECK', '2': 'CALL',
        #            '3': 'RAISE', '4': 'ALL-IN'}
        msg = ('Текущая ставка: {}; Ваша текущая ставка: {}; blind: {}.\n'
               'Ваш ход (')
        action = actions.FOLD
        is_valid = False

        # TODO: Переделать после тестов
        print(player.info(self))

        # Отпределяем ситуацию (fold доступен всегда):
        # 1. Доступен только all-in - у игрока фишек <= текущая ставка в
        # игре, текущая ставка игрока ниже текущей ставки в игре
        # 2. Доступны call и all-in - у игрока фишек <= текущая ставка в
        # игре + blind, текущая ставка игрока ниже текущей ставки в игре
        # 3. Доступен только call - текущая ставка игрока ниже текущей
        # ставки в игре, достигнут лимит (если он установлен) по количеству
        # повышений ставки (в игре, либо отдельным игроком), либо все
        # оставшиеся игроки имеют статус ALL_IN
        # 4. Доступны check, raise, all-in - текущая ставка игрока равна
        # текущей ставке в игре, лимит (если он установлен) по количеству
        # повышений ставки (в игре, либо отдельным игроком) не достигнут,
        # фишек у игрока больше, чем текущая ставка в игре + blind, остались
        # активные игроки, у которых количество фишек не меньше
        # 5. Доступны call, raise, all-in - текущая ставка игрока меньше
        # текущей ставки в игре, лимит (если он установлен) по количеству
        # повышений ставки (в игре, либо отдельным игроком) не достигнут,
        # фишек у игрока больше, чем текущая ставка в игре + blind, остались
        # активные игроки, у которых количество фишек не меньше
        # 6. Доступны call и raise - текущая ставка игрока меньше текущей
        # ставки в игре, лимит (если он установлен) по количеству повышений
        # ставки (в игре, либо отдельным игроком) не достигнут, фишек у
        # игрока больше, чем текущая ставка в игре + blind, остались
        # активные игроки, но у всех количество фишек меньше
        # 6. Доступны check и raise - текущая ставка игрока меньше текущей
        # ставки в игре, лимит (если он установлен) по количеству повышений
        # ставки (в игре, либо отдельным игроком) не достигнут, фишек у
        # игрока больше, чем текущая ставка в игре + blind, остались
        # активные игроки, но у всех количество фишек меньше
        # 7. Доступен только check - текущая ставка игрока равна текущей
        # ставке в игре, достигнут лимит (если он установлен) по количеству
        # повышений ставки (в игре, либо отдельным игроком), либо все
        # оставшиеся игроки имеют статус ALL_IN

        if player.current_bid < self.current_bid:
            # В этом блоке не доступен check, выбор из CALL, RAISE, ALL-IN
            if player.wealth <= self.current_bid:
                allow_actions = [actions.FOLD, actions.ALL_IN]
            elif (
                self.active_players_count == 1
                or (
                    self.raise_personal_limit is not None
                    and self.raise_personal == self.raise_personal_limit
                )
                or (
                    self.trade_rounds_limit is not None
                    and self.trade_round == self.trade_rounds_limit
                )
            ):
                allow_actions = [actions.FOLD, actions.CALL]
            elif (
                self.current_bid < player.wealth
                < self.current_bid + self.blind
            ):
                allow_actions = [actions.FOLD, actions.CALL, actions.ALL_IN]
            elif player.wealth > sorted(
                [plyr for plyr in self.players
                 if plyr.status == player_status.ACTIVE],
                reverse=True,
                key=lambda x: x.wealth
            )[1].wealth:
                allow_actions = [actions.FOLD, actions.CALL, actions.RAISE]
            else:
                allow_actions = [
                    actions.FOLD, actions.CALL, actions.RAISE, actions.ALL_IN
                ]
        else:
            # В этом блоке не доступен call, выбор из CHECK, RAISE, ALL-IN
            if (
                self.active_players_count == 1
                or (
                    self.raise_personal_limit is not None
                    and self.raise_personal == self.raise_personal_limit
                )
                or (
                    self.trade_rounds_limit is not None
                    and self.trade_round == self.trade_rounds_limit
                )
            ):
                allow_actions = [actions.FOLD, actions.CHECK]
            elif (
                self.current_bid < player.wealth
                < self.current_bid + self.blind
            ):
                allow_actions = [actions.FOLD, actions.CHECK, actions.ALL_IN]
            elif player.wealth > sorted(
                [plyr for plyr in self.players
                 if plyr.status == player_status.ACTIVE],
                reverse=True,
                key=lambda x: x.wealth
            )[1].wealth:
                allow_actions = [actions.FOLD, actions.CHECK, actions.RAISE]
            else:
                allow_actions = [
                    actions.FOLD, actions.CHECK, actions.RAISE, actions.ALL_IN
                ]
        msg += ', '.join(
            [act + ' - ' + ACTIONS[act] for act in allow_actions]
        )
        msg += '): '
        while not is_valid:
            action = input(msg.format(
                self.current_bid,
                player.current_bid,
                self.blind
            ))
            if action not in allow_actions:
                print('Введите число - один из предложенных варианов.')
            else:
                is_valid = True
        is_valid = False

        # При повышении ставки (raise) ввод нового значения и проверка его
        # корректности:
        if action == actions.RAISE:
            while not is_valid:
                second_richest_player_wealth = sorted(
                    [plyr for plyr in self.players
                     if plyr.status == player_status.ACTIVE],
                    reverse=True, key=lambda x: x.wealth
                )[1].wealth
                bid = int(input(
                    f'Введите свою ставку (целое число от {min(self.current_bid + self.blind, player.wealth)}'
                    f' до {min(player.wealth, second_richest_player_wealth)}): '
                ))
                try:
                    player.action(self, action, bid)
                    logging.info(
                        f'Player {player.name}: order: {self.players.index(player)}, wealth: {player.wealth}, '
                        f'hand: {Card(*player.hand[0])} {Card(*player.hand[1])}, '
                        f'role: {player.role}, %win: {self.p_win[player]}%, '
                        f'action: RISE, bid: {player.current_bid}, '
                        f'wealth change: {player.wealth_change}'
                    )
                    logging.info(f'Bank: {self.bank}, current bid: {self.current_bid}')
                    is_valid = True
                except ExceededValueError:
                    print('У Вас нет столько фишек.')
                except MinRaiseError:
                    print('Минимальное повышение равно blind.')
                except InsufficientRaiseError:
                    print('Ставка должна быть выше текущей ставки в игре.')
                except Exception as err:
                    print('Что-то пошло не так, попробуйте еще раз.\n', err)
        else:
            player.action(self, action)
            logging.info(
                f'Player {player.name}: order: {self.players.index(player)}, wealth: {player.wealth}, '
                f'hand: {Card(*player.hand[0])} {Card(*player.hand[1])}, '
                f'role: {player.role}, %win: {self.p_win[player]}%, '
                f'action: {ACTIONS[action]}, bid: {player.current_bid}, '
                f'wealth change: {player.wealth_change}'
            )
            logging.info(f'Bank: {self.bank}, current bid: {self.current_bid}')
            if action == actions.FOLD:
                self.folds_count += 1
                self.players_in_count -= 1
                self.active_players_count -= 1
                for player in self.players:
                    if player.status != player_status.FOLD:
                        self.p_win[player] = player.p_win(self)

    def first_trading(self, players: typing.List[Player]) -> bool:
        for player in players:
            if player.status == player_status.ACTIVE:
                self.action_query(player)
        bids = set(
            [player.current_bid for player in self.players
             if player.status == player_status.ACTIVE]
        )
        return len(bids) == 1 and list(bids)[0] == self.current_bid

    def trading(self, players):
        active_players = [
            player for player in players if player.status == player_status.ACTIVE
        ]
        active_players_bids = [player.current_bid for player in active_players]

        player_index = 0
        while self.active_players_count > 0:
            player = active_players[player_index]
            self.action_query(player)
            if player.status != player_status.ACTIVE:
                active_players.pop(player_index)
                active_players_bids.pop(player_index)
                if (
                    len(set(active_players_bids)) == 1
                    and active_players_bids[0] == self.current_bid
                ):
                    break
            else:
                active_players_bids[player_index] = player.current_bid
                if (
                    len(set(active_players_bids)) == 1
                    and active_players_bids[0] == self.current_bid
                ):
                    break
                player_index += 1
                if player_index == self.active_players_count:
                    player_index = 0

    def pre_flop(self):
        """
        В первом раунде торгов инициатором является игрок, правый от
        большого блайнда, в остальных раундах торговлю начинает первый
        игрок (малый блайнд).
        При этом если в раздаче участвует 2 игрока, торги также начинает
        малый блайнд.
        """
        if len(self.players) > 2:
            players = self.players[2:] + self.players[:2]
        else:
            players = self.players
        is_over = self.first_trading(players)
        if not is_over:
            self.trading(players)
        if self.active_players_count <= 1 and self.all_in_players_count == 0:
            self.define_winner()
        else:
            self.show_flop()

    def show_flop(self):
        self.stage = game_stage.FLOP
        logging.info(f'Stage: {game_stage.STAGE[self.stage]}')
        self._deck.pop(0)
        for _ in range(3):
            self.table.append(self._deck.pop(0))
        logging.info(
            f'Table: {" ".join([str(Card(*card)) for card in self.table])}'
        )
        for player_order, player in enumerate(self.players):
            if player.status != player_status.FOLD:
                self.p_win[player] = player.p_win(self)
                logging.info(
                    f'Player{player_order} {player.name}: wealth: {player.wealth}, '
                    f'status: {player.STATUS[player.status]}, '
                    f'hand: {Card(*player.hand[0])} {Card(*player.hand[1])}, '
                    f'role: {player.role}, %win: {self.p_win[player]}%'
                )
        self.show_table()
        is_over = self.first_trading(self.players)
        if not is_over:
            self.trading(self.players)
        if self.active_players_count <= 1:
            self.define_winner()
        else:
            self.show_turn()

    def show_turn(self):
        self.stage = game_stage.TURN
        logging.info(f'Stage: {game_stage.STAGE[self.stage]}')
        self._deck.pop(0)
        self.table.append(self._deck.pop(0))
        logging.info(
            f'Table: {" ".join([str(Card(*card)) for card in self.table])}'
        )
        for player_order, player in enumerate(self.players):
            if player.status != player_status.FOLD:
                self.p_win[player] = player.p_win(self)
                logging.info(
                    f'Player{player_order} {player.name}: wealth: {player.wealth}, '
                    f'status: {player.STATUS[player.status]}, '
                    f'hand: {Card(*player.hand[0])} {Card(*player.hand[1])}, '
                    f'role: {player.role}, %win: {self.p_win[player]}%'
                )
        self.show_table()
        is_over = self.first_trading(self.players)
        if not is_over:
            self.trading(self.players)
        if self.active_players_count <= 1:
            self.define_winner()
        else:
            self.show_river()

    def show_river(self):
        self.stage = game_stage.RIVER
        logging.info(f'Stage: {game_stage.STAGE[self.stage]}')
        self._deck.pop(0)
        self.table.append(self._deck.pop(0))
        logging.info(
            f'Table: {" ".join([str(Card(*card)) for card in self.table])}'
        )
        for player_order, player in enumerate(self.players):
            if player.status != player_status.FOLD:
                self.p_win[player] = player.p_win(self)
                logging.info(
                    f'Player{player_order} {player.name}: wealth: {player.wealth}, '
                    f'status: {player.STATUS[player.status]}, '
                    f'hand: {Card(*player.hand[0])} {Card(*player.hand[1])}, '
                    f'role: {player.role}, %win: {self.p_win[player]}%'
                )
        self.show_table()
        is_over = self.first_trading(self.players)
        if not is_over:
            self.trading(self.players)
        self.define_winner()

    def show_table(self):
        print('Table:', Cards([Card(*card) for card in self.table]), sep='\n')

    def define_winner(self):
        deal_players = self.players

        def _define_winner(deal, players):
            # Если в игре остался один игрок - он победитель.
            if deal.players_in_count == 1:
                for player in players:
                    if player.status != player_status.FOLD:
                        player.wealth_change += deal.bank
                        break
            else:
                # Расположим игроков в порядке убывания комбинации,
                # при равенстве - в порядке возрастания ставки.
                queue = sorted(
                    [
                        (player, player.combination(deal)) for player
                        in players if player.status != player_status.FOLD
                    ],
                    key=lambda x: (x[1], -x[0].current_bid), reverse=True
                )

                # Простой случай - один победитель забирает весь банк.
                if queue[0][0].current_bid == deal.current_bid:

                    # Простой случай - один победитель забирает весь банк.
                    if queue[0][1] > queue[1][1]:
                        queue[0][0].wealth_change += deal.bank

                    # Ничья - банк делится поровну между несколькими победителями.
                    else:
                        winners_count = 2
                        while (
                            winners_count < len(queue)
                            and queue[winners_count-1][1] == queue[winners_count][1]
                        ):
                            winners_count += 1
                        for player_index in range(winners_count):
                            queue[player_index][0].wealth_change += deal.bank // winners_count

                # Победивший игрок претендует не на весь банк
                elif queue[0][1] > queue[1][1]:
                    new_player_list = []
                    for player in (
                        queue[1:]
                        + [(player,) for player in players
                           if player.status == player_status.FOLD]
                    ):
                        bid = min(
                            queue[0][0].current_bid,
                            player[0].current_bid
                        )
                        queue[0][0].wealth_change += bid
                        deal.bank -= bid
                        player[0].current_bid -= bid
                        if player[0].current_bid > 0:
                            new_player_list.append(player[0])

                    _define_winner(deal, new_player_list)

                # Ничья, и часть игроков не претендовали на весь банк
                else:
                    winners_count = 2
                    while (
                        winners_count < len(queue)
                        and queue[winners_count - 1][1] == queue[winners_count][1]
                    ):
                        winners_count += 1
                    for player_index in range(winners_count):

                        for winner in queue[player_index:winners_count]:
                            winner[0].wealth_change += queue[player_index][0].current_bid
                            winner[0].current_bid -= queue[player_index][0].current_bid
                            deal.bank -= queue[player_index][0].current_bid

                        for loser in (
                            queue[winners_count:]
                            + [(player,) for player in players
                               if player.status == player_status.FOLD]
                        ):
                            if loser[0].current_bid > 0:
                                bid = min(
                                    queue[player_index][0].current_bid,
                                    loser[0].current_bid
                                )
                                for winner in queue[player_index:winners_count]:
                                    winner[0].wealth_change += bid // (winners_count - player_index)
                                loser[0].current_bid -= bid
                                deal.bank -= bid
                    new_player_list = [
                        player for player in players if player.current_bid > 0
                    ]
                    _define_winner(deal, new_player_list)

        _define_winner(self, deal_players)
        for player_order, player in enumerate(self.players):
            logging.info(
                f'Player{player_order} {player.name}: wealth: {player.wealth}, '
                f'status: {player.STATUS[player.status]}, '
                f'combo: {player.summary(self)}, '
                f'change: {f"+{player.wealth_change}" if player.wealth_change > 0 else player.wealth_change}'
            )
        self.show_info()
        self.clean()

    def clean(self):
        for player in self.players:
            player.wealth += player.wealth_change
            player.wealth_change = 0
            player.status = player_status.ACTIVE
            player.set_role()
            player.current_bid = 0

    def show_info(self):
        if self.table:
            self.show_table()
        for player in self.players:
            player.show_hand()
            print(f'{player.name}: {f"+{player.wealth_change}" if player.wealth_change > 0 else player.wealth_change}')


class GameSettings:
    def __init__(
        self,
        small_blind_rate: int = 1,
        reraise_count_limit: int = 2,
        deals_count_limit: int = 10,
        game_time_limit: int = 1000,
        raise_blinds_type: int = 0,
        raise_blinds_freq: int | list[int] = 3,
        raise_blinds_value: int | list[int] = 2
    ):
        """

        :param small_blind_rate:
        :param reraise_count_limit:
        :param deals_count_limit:
        :param game_time_limit:
        :param raise_blinds_type:
            0 - каждые raise_blinds_freq раздач размер минимальной ставки
                увеличивается в raise_blinds_value раз;
            1 - каждые raise_blinds_freq раздач размер минимальной ставки
                увеличивается на raise_blinds_value;
            3 - задается список номеров раздач, с которых устанавливаются
                определенные размеры ставок.
        :param raise_blinds_freq:
        :param raise_blinds_value:
        """
        self.small_blind_rate = small_blind_rate
        self.reraise_count_limit = reraise_count_limit
        self.deals_count_limit = deals_count_limit
        self.game_time_limit = game_time_limit
        self.raise_blinds_type = raise_blinds_type
        self.raise_blinds_value = raise_blinds_value


class Game:
    def __init__(
            self,
            players: list[Player],
            settings: GameSettings
    ):
        logging.info('*' * 10 + 'NEW GAME' + '*' * 10)
        self.id = str(hex(hash(self)))[2:10]
        self.deal = 0
        # random.shuffle(players)
        self.players = players
        self.active_players = self.players
        self.settings = settings
        players_count = len(players)
        logging.info(f'GameID: {self.id}, players count: {players_count}, '
                     f'max trade rounds: {self.settings.reraise_count_limit}')
        for i, player in enumerate(self.players):
            logging.info(
                f'Player{i}: id: {player.player_id}, name: {player.name}, '
                f'wealth: {player.wealth}{", bot" if player.is_bot else ""}'
            )
        self.new_deal()

    def new_deal(self):
        self.deal += 1
        logging.info(f'Deal {self.deal}')
        self.active_players = [
            player for player in self.active_players if player.wealth > 0
        ]
        deal = Deal(
            players=self.active_players,
            small_blind_rate=self.settings.small_blind_rate,
            # limit=self.settings.reraise_count_limit
        )
        self.active_players = self.active_players[1:] + self.active_players[:1]
        self.active_players = [
            player for player in self.active_players if player.wealth > 0
        ]
        if len(self.active_players) > 1:
            self.new_deal()


if __name__ == '__main__':
    logging.config.dictConfig(LOGGING_CONFIG)
    player_list = [
        Player(False, 1, 100, 'Player1'),
        Player(False, 2, 100, 'Player2'),
        Player(False, 3, 100, 'Player3'),
    ]
    game_settings = GameSettings()
    Game(player_list, game_settings)
