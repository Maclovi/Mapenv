import unittest
from decimal import Decimal

from src.mapenv.improve import Improve as improve
from src.mapenv.main import MapEnv


class A:
    def __init__(self, val: str) -> None:
        self.val = val


@improve(envfile="tests/.env", override=True, frozen=True)
class TestEnv(MapEnv):
    TOKEN: str
    RATES: float
    ID_USERS: set[int]
    AVAILABLE_VALUES: list[int]
    FROZEN_ID_USERS: frozenset[int]
    WINNER_ID_USERS: tuple[str, int, str, int]
    USER_CUSTOM_CLASS: A
    PRICE: Decimal

    def __init__(self, val: str) -> None:
        self.val = val


class TestDotenv(unittest.TestCase):
    def setUp(self) -> None:
        self.tg = TestEnv("test")

    def test_str(self) -> None:
        self.assertIsInstance(self.tg.TOKEN, str, "tg.TOKEN is not str")

    def test_set(self) -> None:
        self.assertIsInstance(self.tg.ID_USERS, set, "tg.SET is not set")

    def test_set_content(self) -> None:
        msg = "tg.ID_USERS is not equal to content"
        self.assertSetEqual(self.tg.ID_USERS, {312, 3213, 3215, 543, 1101}, msg)

    def test_tuple(self) -> None:
        self.assertIsInstance(
            self.tg.WINNER_ID_USERS, tuple, "tg.TUPLE is not tuple"
        )

    def test_tuple_content(self) -> None:
        msg = "tg.WINNER_ID_USERS is not equal to content"
        self.assertTupleEqual(
            self.tg.WINNER_ID_USERS, ("maksim", 10, "mark", 20), msg
        )

    def test_list(self) -> None:
        self.assertIsInstance(
            self.tg.AVAILABLE_VALUES, list, "tg.LIST is not list"
        )

    def test_list_content(self) -> None:
        msg = "tg.AVAILABLE_VALUES is not equal to content"
        self.assertListEqual(self.tg.AVAILABLE_VALUES, [10, 11, 12, 13], msg)

    def test_frozenset(self) -> None:
        msg = "tg.FROZEN_ID_USERS is not frozenset"
        self.assertIsInstance(self.tg.FROZEN_ID_USERS, frozenset, msg)

    def test_frozenset_content(self) -> None:
        msg = "tg.FROZEN_ID_USERS is not equal to content"
        self.assertSetEqual(self.tg.FROZEN_ID_USERS, frozenset({0, 1}), msg)

    def test_decimal(self) -> None:
        self.assertIsInstance(self.tg.PRICE, Decimal)
        self.assertEqual(self.tg.PRICE, Decimal("99.99"))

    def test_float(self) -> None:
        self.assertIsInstance(self.tg.RATES, float)
        self.assertEqual(self.tg.RATES, float("1.1"))

    def test_custom_class(self) -> None:
        self.assertIsInstance(self.tg.USER_CUSTOM_CLASS, A)
        self.assertEqual(self.tg.USER_CUSTOM_CLASS.val, A("Something").val)

    def test_dict(self) -> None:
        dct = self.tg.todict()
        self.assertIsNot(self.tg.__dict__, dct)

        dct["AVAILABLE_VALUES"] = [0000, 0000]
        self.assertNotEqual(self.tg.AVAILABLE_VALUES, dct["AVAILABLE_VALUES"])

    def test_init_values(self) -> None:
        self.assertEqual(self.tg.val, "test")


if __name__ == "__main__":
    unittest.main()
