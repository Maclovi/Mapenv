import logging
import os
from functools import wraps
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
    ) -> type:
        return super().__new__(cls, name, bases, namespace)

    def __init__(
        cls,
        name: str,
        bases: tuple[Any],
        namespace: dict[str, Any],
    ) -> None:
        super().__init__(name, bases, namespace)

    def __call__(
        cls,
        *args: Any,
        __envfile: str | None,
        __override: bool,
        __frozen: bool,
        **kwargs: Any,
    ) -> Any:
        merged_env = cls.__merge_env(
            file=cls.__getenv_file(envfile=__envfile),
            out=cls.__getenv_out(),
            override=__override,
        )
        typed_dict = cls.__make_types(merged_env=merged_env)

        instance = super().__call__(*args, **kwargs)
        cls.__setfrozen(instance=instance, frozen=__frozen)
        cls.__init_types(instance=instance, typed_dict=typed_dict)

        return instance

    def __getenv_file(cls, *, envfile: str | None = None) -> StrDict:
        if envfile is None:
            return StrDict({})

        if not os.path.isfile(envfile):
            raise FileNotFoundError(f"No such file - {envfile!r}\n")

        return StrDict({**get_from_file_env(envfile)})

    def __getenv_out(cls) -> StrDict:
        return StrDict(
            {
                key: os.environ[key]
                for key in cls.__annotations__
                if os.getenv(key)
            }
        )

    def __merge_env(
        cls, *, file: StrDict, out: StrDict, override: bool = False
    ) -> StrDict:
        if not (file or out):
            raise TypeError("env is empty")
        if override:
            return StrDict(out | file)
        return StrDict(file | out)

    def __make_types(cls, *, merged_env: StrDict) -> TypedDict:
        for name, type_hint in cls.__annotations__.items():
            merged_env[name] = cls.__set_type(type_hint, merged_env[name])
        return TypedDict(merged_env)

    def __set_type(cls, type_hint: type, value: str) -> Any:
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
                tmp_val[i] = cls.__set_type(type_, tmp_val[i])

        elif args_of_origin:
            tmp_val = map(args_of_origin[0], tmp_val)

        return origin(tmp_val)

    def __init_types(cls, instance: "MetaClass", typed_dict: TypedDict) -> None:
        for k, v in typed_dict.items():
            setattr(instance, k, v)

    def __setfrozen(cls, instance: "MetaClass", frozen: bool) -> None:
        name = "_frozen"
        setattr(instance, name, frozen)


class MapEnv(metaclass=MetaClass):
    def __str__(self) -> str:
        return f"{self.__class__.__name__}{self.__dict__}"

    def __setattr__(self, _name: str, _value: Any) -> None:
        if getattr(self, "_frozen", False):  # noqa [B009]
            if _name not in self.__annotations__:
                raise TypeError(
                    "This object is frozen, you can't set attribute."
                )
            if _name in self.__dict__:
                raise TypeError(
                    "This object is frozen, you can't change attribute"
                )
        super().__setattr__(_name, _value)

    def __delattr__(self, _name: str) -> None:
        if getattr(self, "_frozen", False):  # noqa [B009]
            raise TypeError("This object is frozen, you can't delete attribute")
        super().__delattr__(_name)

    def todict(self) -> TypedDict:
        """Return copy dict from self.__dict__"""
        return TypedDict(self.__dict__.copy())


def lru_cache(
    max_cache: int,
) -> Callable[[Callable[F_Spec, F_Return]], Callable[F_Spec, F_Return]]:
    memo: dict[int, Any] = {}

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
    with open(path, encoding="utf8") as file:
        return StrDict(dict(row.strip().split("=") for row in file))
