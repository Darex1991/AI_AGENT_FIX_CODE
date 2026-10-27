from kalkulator import srednia, rabat


def test_srednia():
    assert srednia([2, 4, 6]) == 4


def test_srednia_pusta_lista():
    assert srednia([]) == 0


def test_rabat():
    assert rabat(100, 20) == 80