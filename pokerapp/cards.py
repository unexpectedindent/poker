import random
from typing import Dict, List, Sequence, Tuple


SUIT = {0: '\u2664', 1: '\u2665', 2: '\u2666', 3: '\u2667'}

SUIT_R = {'\u2664': 0, '\u2665': 1, '\u2666': 2, '\u2667': 3}

VALUE = {-1: 'A', 0: '2', 1: '3', 2: '4', 3: '5', 4: '6', 5: '7',
         6: '8', 7: '9', 8: '10', 9: 'J', 10: 'Q', 11: 'K', 12: 'A'}

VALUE_R = {
    '2': 0, '3': 1, '4': 2, '5': 3, '6': 4, '7': 5, '8': 6, '9': 7, '10': 8,
    'J': 9, 'Q': 10, 'K': 11, 'A': 12
}

COMBINATION = {
    0: 'Старшая карта',
    1: 'Пара',
    2: 'Две пары',
    3: 'Сет',
    4: 'Стрит',
    5: 'Флаш',
    6: 'Фулл хауз',
    7: 'Каре',
    8: 'Стрит-флаш'
}


class Card:
    """
    Объект с двумя параметрами - номинал (value) и масть (suit),
    номинал - число от 0 до 12, где 0 - двойка, 12 - туз,
    масть - число от 0 до 3.
    """
    def __init__(self, value: int, suit: int) -> None:
        """
        :param value: номинал карты - число от 0 до 12, где 0 - двойка, 12 - туз.
        :param suit: масть карты - число от 0 до 3.
        """
        self.value = value
        self.suit = suit

    def __repr__(self) -> str:
        return VALUE[self.value] + SUIT[self.suit]

    def __lt__(self, other) -> bool:
        return self.value < other.value

    def __gt__(self, other) -> bool:
        return self.value > other.value

    def __eq__(self, other) -> bool:
        return self.value == other.value

    def __le__(self, other) -> bool:
        return self.value <= other.value

    def __ge__(self, other) -> bool:
        return self.value >= other.value


class Cards:
    def __init__(self, cards: Sequence[Card]) -> None:
        self._cards = cards

    def __repr__(self) -> str:
        """
        Визуальное представление карт:
         ____   ____
        |10♥ | |A♧  |
        |    | |    |
        |_10♥| |__A♧|
        """
        count = len(self._cards)
        upper_signs = [
            str(card) + ' ' if len(str(card)) == 2 else str(card)
            for card in self._cards
        ]
        lower_signs = [
            '_' + str(card) if len(str(card)) == 2 else str(card)
            for card in self._cards
        ]
        return (
            ' '.join([' ____ ' for _ in range(count)]) + '\n'
            + ' '.join(['|{} |' for _ in range(count)]).format(*upper_signs)
            + '\n' + ' '.join(['|    |' for _ in range(count)]) + '\n'
            + ' '.join(['|_{}|' for _ in range(count)]).format(*lower_signs)
        )


def generate_deck(without: Sequence[Card]) -> List[Card]:
    """
    Функция для генерации колоды.
    :param without: набор карт, которые нужно исключиить из колоды.
    :return: список карт.
    """
    deck = [
        Card(value, suit) for value in range(13) for suit in range(4)
        if Card(value, suit) not in without
    ]
    random.shuffle(deck)
    return deck


def _generate_deck(
    without: Sequence[tuple[int, int]] = []
) -> list[tuple[int, int]]:
    """
    Более быстрая функция для генерации колоды - принимает и генерирует не
    объекты карт, а набор кортежей формата (<значение>, <масть>)
    :param without: набор карт, которые нужно исключиить из колоды.
    :return: список карт.
    """
    deck = [
        (value, suit) for value in range(13) for suit in range(4)
        if (value, suit) not in without
    ]
    random.shuffle(deck)
    return deck


def _has_straight_combination(
    ordered_card_values: Sequence[int]
) -> list:
    """
    Функция определяет, присутствует ли в наборе карт стрит и определяет
    его ранг (значение начальной карты). Принимает на вход упорядоченный
    по возрастанию набор значений карт (не менее 5).
    :param ordered_card_values: последовательность целых чисел от 0 до 12,
        упорядоченная по возрастанию.
    :return: список из двух значений True/False в зависимости от того,
        содержится ли в комбинации стрит, и целое число - значение младшей
        карты стрита, либо -1, если ответ False.
    """
    count = len(ordered_card_values)
    if count < 5:
        return [False, -1]
    for bottom_card in range(count-5, -1, -1):
        if (
            ordered_card_values[bottom_card:bottom_card+5] ==
            [i for i in range(ordered_card_values[bottom_card],
                              ordered_card_values[bottom_card]+5)]
        ):
            return [True, ordered_card_values[bottom_card]]
    low_straight = {0, 1, 2, 3, 12}
    return [low_straight == set(ordered_card_values) & low_straight, -1]


def _extract_flush(
    cards: Sequence[List[int]],
    suits: Dict[int, int]
) -> List[int]:
    """

    :param cards:
    :param suits:
    :return:
    """
    count = len(cards[0])
    suit = suits[max(suits.keys())]
    return [cards[0][i] for i in range(count) if cards[1][i] == suit]


def _high_card_subrank(
    ordered_card_values: list[int, int, int, int, int, int, int], *args
) -> list[int, int, int, int, int]:
    return ordered_card_values[::-1][:5]


def _pair_subrank(
    ordered_card_values: list[int, int, int, int, int, int, int],
    grouped_values: list[int, int, int, int, int, int], *args
) -> list[int, tuple[int, int, int]]:
    """

    :param ordered_card_values:
    :param grouped_values:
    :param args:
    :return:
    """
    pair_index = grouped_values.index(2)
    pair_rank = ordered_card_values.pop(pair_index)
    ordered_card_values.pop(pair_index)
    return [pair_rank, tuple(ordered_card_values[::-1][:3])]


def _two_pairs_subrank(
    ordered_card_values: list[int, int, int, int, int, int, int],
    grouped_values: list[int, int, int, int, int], *args
) -> list[tuple[int, int], int]:
    """

    :param ordered_card_values:
    :param grouped_values:
    :param args:
    :return:
    """
    low_pair_index = grouped_values.index(2)
    grouped_values.pop(low_pair_index)
    high_pair_index = grouped_values.index(2) + 2
    grouped_values.pop(high_pair_index - 2)
    if 2 in grouped_values:
        low_pair_index, high_pair_index = high_pair_index, grouped_values.index(2) + 4
    high_pair_rank = ordered_card_values.pop(high_pair_index)
    ordered_card_values.pop(high_pair_index)
    low_pair_rank = ordered_card_values.pop(low_pair_index)
    ordered_card_values.pop(low_pair_index)
    return [(high_pair_rank, low_pair_rank), ordered_card_values[-1]]


def _triple_subrank(
    ordered_card_values: list[int, int, int, int, int, int, int],
    grouped_values: list[int, int, int, int, int], *args
) -> list[int, tuple[int, int]]:
    """

    :param ordered_card_values:
    :param grouped_values:
    :param args:
    :return:
    """
    triple_index = grouped_values.index(3)
    triple_rank = ordered_card_values.pop(triple_index)
    ordered_card_values.pop(triple_index)
    ordered_card_values.pop(triple_index)
    return [triple_rank, tuple(ordered_card_values[::-1][:2])]


def _full_house_subrank(
    ordered_card_values: list[int, int, int, int, int, int, int],
    grouped_values: list[int, int, int] | list[int, int, int, int], *args
) -> list[int, int]:
    """

    :param ordered_card_values:
    :param grouped_values:
    :param args:
    :return:
    """
    if grouped_values.count(3) == 2:
        return [ordered_card_values[5], ordered_card_values[1]]
    triple_index = grouped_values.index(3)
    if grouped_values.count(2) == 2:
        return [
            ordered_card_values[triple_index * 3],
            ordered_card_values[-1 if triple_index < 2 else 2]
        ]
    pair_index = grouped_values.index(2)
    return [
        ordered_card_values[sum(grouped_values[:triple_index])],
        ordered_card_values[sum(grouped_values[:pair_index])]
    ]


def _carre_subrank(
    ordered_card_values: list[int, int, int, int, int, int, int],
    grouped_values: list[int, int, int, int] | list[int, int, int] | list[int, int],
    *args
) -> list[int, int]:
    if grouped_values[-1] == 4:
        return [ordered_card_values[-1], ordered_card_values[2]]
    carre_index = grouped_values.index(4)
    return [
        ordered_card_values[sum(grouped_values[:carre_index])],
        ordered_card_values[-1]
    ]


def _straight_subrank(
    ordered_card_values: List[int], grouped_values: List[int],
    straight_rank: int, *args
) -> List[int]:
    """

    :param ordered_card_values:
    :param grouped_values:
    :param straight_rank:
    :param args:
    :return:
    """
    return [straight_rank]


def _calculate_max_value(
        seven_cards: Sequence[tuple[int, int]]
) -> tuple:
    """
    Функция принимает на вход комбинацию из 7 карт и возвращает ранг
    страршей комбинации из 5 карт.
    :param seven_cards: входящая комбинация из 7 карт, где карта - кортеж из
    целых чисел: перове число от 0 до 12 - номинал карты, второе - от 0 до
    3 - масть карты.
    :return:
    """
    seven_cards = sorted(seven_cards, key=lambda x: x[0])

    # Список, содержащий два списка: номиналов карт и соответствующих мастей
    cards = [
        [card[0] for card in seven_cards], [card[1] for card in seven_cards]
    ]
    card_values_count = [cards[0].count(i)
                         for i in sorted(list(set(cards[0])))]
    card_suits = {cards[1].count(i): i for i in set(cards[1])}
    straight_rank = None
    if max(card_suits.keys()) > 4:
        cards[0] = _extract_flush(cards, card_suits)
        has_straight_flush, straight_rank = _has_straight_combination(cards[0])
        if has_straight_flush:
            main_rank = 8
        else:
            main_rank = 5
    elif 4 in card_values_count:
        main_rank = 7
    elif 3 in card_values_count:
        if sorted(card_values_count)[-2] > 1:
            main_rank = 6
        else:
            main_rank = 3
    else:
        has_straight, straight_rank = _has_straight_combination(cards[0])
        if has_straight:
            main_rank = 4
        else:
            main_rank = min(card_values_count.count(2), 2)

    def_subrank = {
        0: _high_card_subrank,
        1: _pair_subrank,
        2: _two_pairs_subrank,
        3: _triple_subrank,
        4: _straight_subrank,
        5: _high_card_subrank,
        6: _full_house_subrank,
        7: _carre_subrank,
        8: _straight_subrank
    }
    return tuple(
        [main_rank]
        + def_subrank[main_rank](
            cards[0], card_values_count, straight_rank
        )
    )


def rank_to_cards(score: tuple) -> str:
    info = COMBINATION[score[0]]
    if score[0] == 0 or score[0] == 5:
        return info + ': ' + ''.join([VALUE[i] for i in score[1:][::-1]])
    if score[0] == 1:
        return info + ': ' + VALUE[score[1]] * 2 + ''.join([VALUE[i] for i in score[2][::-1]])
    if score[0] == 2:
        return info + ': ' + VALUE[score[1][1]] * 2 + VALUE[score[1][0]] * 2 + VALUE[score[2]]
    if score[0] == 3:
        return info + ': ' + VALUE[score[1]] * 3 + ''.join([VALUE[i] for i in score[2][::-1]])
    if score[0] == 6:
        return info + ': ' + VALUE[score[1]] * 3 + VALUE[score[2]] * 2
    if score[0] == 7:
        return info + ': ' + VALUE[score[1]] * 4 + VALUE[score[2]]
    return info + ': ' + ''.join([VALUE[i] for i in range(score[1], score[1] + 5)])


def get_stats(n: int) -> dict:
    names = {
        0: 'Старшая карта',
        1: 'Пара',
        2: 'Две пары',
        3: 'Сет',
        4: 'Стрит',
        5: 'Флаш',
        6: 'Фулл хауз',
        7: 'Каре',
        8: 'Стрит-флаш'
    }
    stats = {
        'Старшая карта': [0, '0.00%'],
        'Пара': [0, '0.00%'],
        'Две пары': [0, '0.00%'],
        'Сет': [0, '0.00%'],
        'Стрит': [0, '0.00%'],
        'Флаш': [0, '0.00%'],
        'Фулл хауз': [0, '0.00%'],
        'Каре': [0, '0.00%'],
        'Стрит-флаш': [0, '0.00%'],
    }
    for _ in range(n):
        hand = _calculate_max_value(_generate_deck()[:7])
        stats[names[hand[0]]][0] += 1
    for key in stats.keys():
        stats[key][1] = f'{stats[key][0] * 100 / n:.04}%'
    return stats


def emulate_deal(
        hand: Tuple[Tuple[int, int]],
        players_count: int,
        table: Tuple[Tuple[int, int]] = None
):
    if table:
        deck = _generate_deck(list(hand) + list(table))
        table_card_count = len(table)
    else:
        deck = _generate_deck(hand)
        table_card_count = 0
        table = ()
    this_table = list(table)
    cards_to_other = [deck[i * 2:i * 2 + 2] for i in range(players_count - 1)]
    this_table += deck[47 + table_card_count:]
    hands = [list(hand) + this_table] + [i + this_table for i in cards_to_other]
    score = [_calculate_max_value(hand) for hand in hands]
    return int(score.index(max(score)) == 0)


def _calculate_p_win(hand: tuple | list, players_count: int, table: tuple = None, n: int = 100000):
    score = 0
    for _ in range(n):
        score += emulate_deal(hand, players_count, table)
    return score * 100 / n


def main():
    for n in range(2, 9):
        for i in range(13):
            for j in range(i+1, 13):
                p = _calculate_p_win(((i, 0), (j, 1)), n, None, 100000)
                print(f'Players: {n}, cards: {Card(i, 0)}{Card(j, 1)}: {p:.04}%')
                p = _calculate_p_win(((i, 0), (j, 0)), n, None, 100000)
                print(f'Players: {n}, cards: {Card(i, 0)}{Card(j, 0)}: {p:.04}%')
            p = _calculate_p_win(((i, 0), (i, 1)), n, None, 100000)
            print(f'Players: {n}, cards: {Card(i, 0)}{Card(i, 1)}: {p:.04}%')


if __name__ == '__main__':
    print(_calculate_max_value(
        ((1, 0), (1, 1), (1, 2), (1, 3), (0, 0), (3, 1), (7, 3))
    ))
