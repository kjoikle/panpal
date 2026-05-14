"""
ELO scoring utility for ranking GenAI approaches.

Pure math — no Django dependency. Can be imported and used anywhere.
"""

ELO_K = 32
DEFAULT_ELO = 1000


def expected_score(rating_a: int, rating_b: int) -> float:
    """Expected score for player A when facing player B."""
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))


def update_elos(winner_rating: int, loser_rating: int, k: int = ELO_K) -> tuple[int, int]:
    """
    Apply the ELO update formula.

    Returns (new_winner_rating, new_loser_rating).
    """
    e = expected_score(winner_rating, loser_rating)
    new_winner = round(winner_rating + k * (1 - e))
    new_loser = round(loser_rating + k * (0 - (1 - e)))
    return new_winner, new_loser
