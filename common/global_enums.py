from enum import IntEnum, StrEnum



class IsDelete(IntEnum):
    NO_DELETE = 0
    DELETE = 1

class LLMType(StrEnum):
    CHAT = 'chat'
    EMBEDDING = 'embedding'
    SPEECH2TEXT = 'speech2text'
    IMAGE2TEXT = 'image2text'
    RERANK = 'rerank'
    TTS    = 'tts'