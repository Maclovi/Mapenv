import logging
import os
from functools import wraps
from pathlib import Path
from typing import Any, Callable, ParamSpec, get_args, get_origin

log = logging.getLogger(__name__)

F_Spec = ParamSpec("F_Spec")
F_Return = Any
EnvMap = dict[str, str]


class MetaClass(type):
    def __new__(
        cls,
        name: str,
        bases: tuple[Any],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> type:
        if kwargs:
            pass
        return super().__new__(cls, name, bases, namespace)

    def __init__(
        cls,
        name: str,
        bases: tuple[Any],
        namespace: dict[str, Any],
        **kwargs: Any,
    ) -> None:
        super().__init__(name, bases, namespace)

        cls._environ_from_file: dict[str, Any] = {}
        cls.path_env: str = kwargs.get("load_env", "")
        cls.override: bool = kwargs.get("override", False)

    def __call__(cls, *args: Any, **kwargs: Any) -> Any:
        instance = super().__call__(*args, **kwargs)
        cls.load_to_env(instance)
        cls.create_const(instance)
        return instance

    def load_to_env(cls, instance: "MetaClass") -> None:
        if os.path.isfile(cls.path_env):
            cls._load_to_env(instance)
        elif cls.path_env:
            raise FileNotFoundError(
                f"No such file - {cls.path_env!r}\n"
                f"Your current dir is - {Path(__file__).parent.resolve()}"
            )
        elif cls.override:
            log.warning("\tNothing to override!")

    def _load_to_env(cls, instance: "MetaClass") -> None:
        if not cls._environ_from_file:
            env: "EnvMap" = get_from_file_env(cls.path_env)
            cls._environ_from_file |= {
                key: env.get(key) or os.environ[key]
                for key in cls.__annotations__
            }
        instance._environ_from_file = cls._environ_from_file.copy()

    def create_const(cls, instance: "MetaClass") -> None:
        for key, type_hint in cls.__annotations__.items():
            if cls.override:
                value = instance._environ_from_file.get(key) or os.environ[key]
            else:
                value = os.getenv(key) or instance._environ_from_file[key]

            value_typed = cls._set_type(type_hint, value)
            setattr(instance, key, value_typed)
            instance._environ_from_file[key] = value_typed

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


class Dotenv(metaclass=MetaClass):
    def getdict(self) -> dict[str, Any]:
        if hasattr(self, "_environ_from_file") and isinstance(
            self._environ_from_file, dict
        ):
            return self._environ_from_file.copy()
        raise TypeError("Not found _attr _environ_from_file")


def lru_cache(
    max_cache: int,
) -> Callable[[Callable[F_Spec, F_Return]], Callable[F_Spec, F_Return]]:
    cache: dict[int, EnvMap] = {}

    def inner(func: Callable[F_Spec, F_Return]) -> Callable[F_Spec, F_Return]:
        @wraps(func)
        def wrapper(*args: F_Spec.args, **kwargs: F_Spec.kwargs) -> F_Return:
            if len(cache) > max_cache:
                first_key = next(iter(cache))
                cache.pop(first_key)

            key_hash = hash(f"{args}{kwargs}")
            out_func: EnvMap = func(*args, **kwargs)
            return cache.setdefault(key_hash, out_func)

        return wrapper

    return inner


@lru_cache(max_cache=32)
def get_from_file_env(path: str) -> EnvMap:
    with open(path, encoding="utf-8") as file:
        return dict(row.strip().split("=") for row in file)
