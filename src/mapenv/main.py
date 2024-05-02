import logging
import os
from functools import wraps
from pathlib import Path
from typing import Any, Callable, NewType, ParamSpec, get_args, get_origin

log = logging.getLogger(__name__)

F_Spec = ParamSpec("F_Spec")
F_Return = Any

StrDict = NewType("StrDict", dict[str, str])
TypedDict = NewType("TypedDict", dict[str, Any])


class MetaClass(type):
    def __new__(
        cls,
        name: str,
        bases: tuple[Any],
        namespace: dict[str, Any],
        **_: Any,
    ) -> type:
        return super().__new__(cls, name, bases, namespace)

    def __init__(
        cls,
        name: str,
        bases: tuple[Any],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        super().__init__(name, bases, namespace)

        cls.path_env: str = kwargs.get("load_env", "")
        cls.override: bool = kwargs.get("override", False)

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        merged_env = cls.merge_env(file=cls.getenv_file(), out=cls.getenv_out())
        typed_dict = cls.create_types(merged_env)
        instance = super().__call__(*args, **kwargs)
        cls.init_types(instance, typed_dict)
        return instance

    def getenv_file(cls) -> StrDict:
        if not cls.path_env:
            return StrDict({})

        if not os.path.isfile(cls.path_env):
            raise FileNotFoundError(
                f"No such file - {cls.path_env!r}\n"
                f"Your current dir is - {Path(__file__).parent.resolve()}"
            )

        return StrDict({**get_from_file_env(cls.path_env)})

    def getenv_out(cls) -> StrDict:
        return StrDict(
            {
                key: os.environ[key]
                for key in cls.__annotations__
                if os.getenv(key)
            }
        )

    def merge_env(cls, *, file: StrDict, out: StrDict) -> StrDict:
        if cls.override:
            return StrDict(out | file)
        return StrDict(file | out)

    def create_types(cls, merged_env: StrDict) -> TypedDict:
        for name, type_hint in cls.__annotations__.items():
            merged_env[name] = cls._set_type(type_hint, merged_env[name])
        return TypedDict(merged_env)

    def _set_type(cls, type_hint: type, value: str) -> Any:
        tmp_val: str | list[str] | map[Any] = value
        origin: type = get_origin(type_hint) or type_hint
        args_of_origin = get_args(type_hint)

        if origin is None:
            return None

        if args_of_origin and isinstance(tmp_val, str):
            tmp_val = tmp_val.split(",")

        if (
            origin is tuple
            and len(args_of_origin) > 1
            and isinstance(tmp_val, list)
        ):
            for i, type_ in enumerate(args_of_origin):
                tmp_val[i] = cls._set_type(type_, tmp_val[i])

        elif args_of_origin:
            tmp_val = map(args_of_origin[0], tmp_val)

        return origin(tmp_val)

    def init_types(cls, instance: "MetaClass", typed_dict: TypedDict) -> None:
        for k, v in typed_dict.items():
            setattr(instance, k, v)


class MapEnv(metaclass=MetaClass):
    def __setattr__(self, __name: str, __value: Any) -> None:
        if __name not in self.__annotations__:
            raise TypeError("This object is frozen, you can't set attribute")
        if __name in self.__dict__:
            raise TypeError("This object is frozen, you can't change attribute")
        super().__setattr__(__name, __value)

    def __delattr__(self, _: str) -> None:
        raise TypeError("This object is frozen, you can't delete attribute")

    def __str__(self) -> str:
        return f"{self.__class__.__name__}{self.__dict__}"

    def todict(self) -> TypedDict:
        return TypedDict(self.__dict__.copy())


def lru_cache(
    max_cache: int,
) -> Callable[[Callable[F_Spec, F_Return]], Callable[F_Spec, F_Return]]:
    memo: dict[int, StrDict] = {}

    def inner(func: Callable[F_Spec, F_Return]) -> Callable[F_Spec, F_Return]:
        @wraps(func)
        def wrapper(*args: F_Spec.args, **kwargs: F_Spec.kwargs) -> F_Return:
            if len(memo) > max_cache:
                first_key = next(iter(memo))
                memo.pop(first_key)

            key_hash = hash(f"{args}{kwargs}")
            if key_hash not in memo:
                memo[key_hash] = func(*args, **kwargs)

            return memo[key_hash]

        return wrapper

    return inner


@lru_cache(max_cache=32)
def get_from_file_env(path: str) -> StrDict:
    with open(path, encoding="utf-8") as file:
        return StrDict(dict(row.strip().split("=") for row in file))
