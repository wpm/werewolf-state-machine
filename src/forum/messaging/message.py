import json
from json import JSONDecodeError
from typing import Type, Self

from loguru import logger
from nats.aio.msg import Msg
from pydantic import BaseModel, ValidationError, computed_field

from forum.common import Hashable


class Message(Hashable, BaseModel):
    """
    The content of a message sent to and from `Endpoint` objects.

    Every message has an associated type used in serialization and deserialization
    that is indexed by name in a global codec singleton.

    Endpoints send the type as part of the NATS message header.
    """

    def __init_subclass__(cls, /, **kwargs):
        Codec().add(cls)
        super().__init_subclass__(**kwargs)

    @computed_field
    @property
    def type(self) -> str:
        return self.__class__.__qualname__

    @classmethod
    def decode(cls, data: bytes) -> Self:
        return Codec().decode(data)

    def encode(self) -> bytes:
        return Codec().encode(self)

    @classmethod
    def from_msg(cls, msg: Msg) -> Self:
        return cls.decode(msg.data)


class SingletonMeta(type):
    """
    A metaclass that implements the Singleton pattern.

    Ensures only one instance of a class is created and provides a global point
    of access to it. Used by the Codec class to maintain a single global registry
    of message types.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Codec(dict[str, Type[Message]], metaclass=SingletonMeta):
    """
    A registry for TypedContent classes that handles serialization and deserialization.

    The Codec is implemented as a singleton dictionary that maps message type names to
    their corresponding TypedMessage classes. It provides methods for encoding messages
    to be sent over NATS and decoding received NATS messages and JSON objects into TypedMessage
    objects.

    TypedMessage subclasses are automatically registered with the Codec when they are defined.
    """

    def __init__(self, *types: Type[Message]):
        super().__init__()
        for type_ in types:
            self.add(type_)

    def add(self, message_type: Type[Message]) -> None:
        self[message_type.__qualname__] = message_type

    @staticmethod
    def encode(message: Message) -> bytes:
        """
        Encode a typed message to send over NATS.

        :param message: the typed message
        :return: the serialization in bytes
        """
        return message.model_dump_json(exclude_none=True).encode()

    def decode(self, data: bytes) -> Message:
        """
        Decode a typed message serialized as the payload of a NATS message.

        :param data: JSON serialization of a typed message
        :return: the decoded typed message
        """
        try:
            s = json.loads(data.decode())
        except UnicodeDecodeError:
            logger.error(f'Invalid binary data in "{data}"')
            raise
        except JSONDecodeError:
            logger.error(f'Invalid JSON "{data}"')
            raise
        type_ = s["type"]
        try:
            return self[type_].model_validate_json(data)
        except KeyError:
            logger.error(f'Unrecognized message type "{type_ !r}":\n"{s}"')
            raise
        except ValidationError:
            logger.error(f'Invalid typed message:\n"{s}"')
            raise
