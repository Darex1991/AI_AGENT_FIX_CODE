def srednia(liczby):
    """Zwraca średnią z listy liczb. Dla pustej listy zwraca 0."""
    if not liczby:
        return 0
    return sum(liczby) / len(liczby)

def rabat(cena, procent):
    """Zwraca cenę po rabacie, np. rabat(100, 20) -> 80."""
    return cena * (1 - procent / 100)