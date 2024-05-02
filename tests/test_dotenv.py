import unittest
from decimal import Decimal

from src.envmapp.dotenv import Dotenv


class B:
    def __init__(self, val: str) -> None:
        self.val = val


class Telegram(Dotenv, load_env="tests/.env", override=True):
    TOKEN: str
    FLOAT: float
    SET: set[int]
    LIST: list[int]
    FROZENSET: frozenset[int]
    TUPLE: tuple[str, int, str]
    OTHER: B
    PRICE: Decimal


class TestDotenv(unittest.TestCase):
    def setUp(self) -> None:
        self.tg = Telegram()

    def test_str(self) -> None:
        self.assertIsInstance(self.tg.TOKEN, str, "tg.TOKEN is not str")

    def test_set(self) -> None:
        self.assertIsInstance(self.tg.SET, set, "tg.SET is not set")

    def test_set_content(self) -> None:
        msg = "tg.SET is not equal to content"
        self.assertSetEqual(self.tg.SET, {312, 3213, 3215, 543, 1101}, msg)

    def test_tuple(self) -> None:
        self.assertIsInstance(self.tg.TUPLE, tuple, "tg.TUPLE is not tuple")

    def test_tuple_content(self) -> None:
        msg = "tg.TUPLE is not equal to content"
        self.assertTupleEqual(self.tg.TUPLE, ("kaka", 10, "popa"), msg)

    def test_list(self) -> None:
        self.assertIsInstance(self.tg.LIST, list, "tg.LIST is not list")

    def test_list_content(self) -> None:
        msg = "tg.LIST is not equal to content"
        self.assertListEqual(self.tg.LIST, [10, 11, 12, 13], msg)

    def test_frozenset(self) -> None:
        msg = "tg.FROZENSET is not frozenset"
        self.assertIsInstance(self.tg.FROZENSET, frozenset, msg)

    def test_frozenset_content(self) -> None:
        msg = "tg.FROZENSET is not equal to content"
        self.assertSetEqual(self.tg.FROZENSET, frozenset({0, 1}), msg)

    def test_dict(self) -> None:
        msg = "tg.getdict() is not dict"
        self.assertIsInstance(self.tg.getdict(), dict, msg)

    def test_dict_immutable(self) -> None:
        msg = "tg.getdict()['TOKEN']' id is matches"
        dct = self.tg.getdict()
        dct["TOKEN"] = "sometoken"
        self.assertIsNot(dct["TOKEN"], self.tg.getdict()["TOKEN"], msg)

    def test_decimal(self) -> None:
        self.assertIsInstance(self.tg.PRICE, Decimal)
        self.assertEqual(self.tg.PRICE, Decimal("99.99"))

    def test_float(self) -> None:
        self.assertIsInstance(self.tg.FLOAT, float)
        self.assertEqual(self.tg.FLOAT, float("1.1"))

    def test_entity(self) -> None:
        self.assertIsInstance(self.tg.OTHER, B)
        self.assertEqual(self.tg.OTHER.val, B("Something").val)


if __name__ == "__main__":
    unittest.main()
