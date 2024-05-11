import os
from functools import lru_cache
from typing import Any, NewType, TypeAlias, get_args, get_origin

StrDict: TypeAlias = dict[str, str]
TypedDict = NewType("TypedDict", dict[str, Any])


class MetaClass(type):
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
        for key, value in typed_dict.items():
            setattr(instance, key, value)
        setattr(instance, "_frozen", __frozen)  # noqa:B010

        return instance

    def __getenv_file(cls, *, envfile: str | None) -> StrDict:
        if envfile is None:
            return {}

        if not os.path.isfile(envfile):
            raise FileNotFoundError(f"No such file - {envfile!r}\n")

        return {
            key: value
            for key, value in get_from_file_env(envfile).items()
            if key in cls.__annotations__
        }

    def __getenv_out(cls) -> StrDict:
        return {
            key: os.environ[key]
            for key in cls.__annotations__
            if os.getenv(key)
        }

    def __merge_env(
        cls, *, file: StrDict, out: StrDict, override: bool = False
    ) -> StrDict:
        if not (file or out):
            raise TypeError("environment is empty")

        if override:
            out.update(file)
            final = out
        else:
            file.update(out)
            final = file

        return final

    def __make_types(cls, *, merged_env: StrDict) -> TypedDict:
        for name, type_hint in cls.__annotations__.items():
            merged_env[name] = cls.__set_type(
                type_hint=type_hint, value=merged_env[name]
            )
        return TypedDict(merged_env)

    def __set_type(cls, *, type_hint: type, value: str) -> Any:
        val: str | list[str] | map[Any] = value
        origin: type = get_origin(type_hint) or type_hint
        args_of_origin = get_args(type_hint)

        if origin is None:
            return None

        if origin in (list, tuple, set, frozenset):
            val = val.split(",") if isinstance(val, str) else val

        if (
            origin is tuple
            and len(args_of_origin) > 1
            and isinstance(val, list)
        ):
            for i, type_ in enumerate(args_of_origin):
                val[i] = cls.__set_type(type_hint=type_, value=val[i])

        elif args_of_origin:
            val = map(args_of_origin[0], val)

        return origin(val)


class MapEnv(metaclass=MetaClass):
    def __str__(self) -> str:
        return f"{self.__class__.__name__}{self.__dict__}"

    def __setattr__(self, _name: str, _value: Any) -> None:
        if getattr(self, "_frozen", False):  # noqa:B009
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


@lru_cache(maxsize=16)
def get_from_file_env(path: str) -> StrDict:
    with open(path, encoding="utf8") as file:
        return dict(row.strip().split("=") for row in file)
