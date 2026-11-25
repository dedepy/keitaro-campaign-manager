
import pytest
from app.services.offer_editor import (
    remove_offer_from_distribution,
)

from app.services.offer_editor import (
    distribute_offer_shares,
)


def test_single_offer_gets_100_percent() -> None:
    result = distribute_offer_shares([18004])

    assert result == [
        {
            "offer_id": 18004,
            "share": 100,
            "state": "active",
        }
    ]


def test_two_offers_get_equal_shares() -> None:
    result = distribute_offer_shares(
        [18004, 18005]
    )

    assert [item["share"] for item in result] == [
        50, 50
    ]


def test_three_offers_total_100_percent() -> None:
    result = distribute_offer_shares(
        [18004, 18005, 18006]
    )

    assert [item["share"] for item in result] == [
        34, 33, 33
    ]
    assert sum(item["share"] for item in result) == 100


@pytest.mark.parametrize(
    "offer_ids",
    [
        [],
        [18004, 18004],
        [-1],
        list(range(1, 102)),
    ],
)
def test_invalid_offer_lists(offer_ids: list[int]) -> None:
    with pytest.raises(ValueError):
        distribute_offer_shares(offer_ids)

def test_remove_offer_redistributes_shares() -> None:
    current = [
        {"offer_id": 18004, "share": 50, "state": "active"},
        {"offer_id": 18005, "share": 50, "state": "active"},
    ]

    result = remove_offer_from_distribution(
        current, 18004
    )

    assert result == [
        {
            "offer_id": 18005,
            "share": 100,
            "state": "active",
        }
    ]

    assert len(current) == 2


def test_cannot_remove_last_offer() -> None:
    current = [
        {"offer_id": 18005, "share": 100, "state": "active"}
    ]

    with pytest.raises(ValueError, match="last offer"):
        remove_offer_from_distribution(current, 18005)


def test_cannot_remove_unknown_offer() -> None:
    current = [
        {"offer_id": 18005, "share": 100, "state": "active"}
    ]

    with pytest.raises(ValueError, match="not attached"):
        remove_offer_from_distribution(current, 18004)


def test_cannot_redistribute_inactive_offers() -> None:
    current = [
        {"offer_id": 18004, "share": 50, "state": "active"},
        {"offer_id": 18005, "share": 50, "state": "disabled"},
    ]

    with pytest.raises(ValueError, match="inactive"):
        remove_offer_from_distribution(current, 18004)
