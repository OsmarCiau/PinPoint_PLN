from enum import Enum
from pydantic import BaseModel, Field


class SemanticRelation(str, Enum):
    HYPERNYM = "hypernym"
    CO_HYPONYM = "co_hyponym"
    HYPONYM_1 = "hyponym_1"
    HYPONYM_2_OR_MERONYM = "hyponym_2_or_meronym"
    SYNONYM = "synonym"


class Clue(BaseModel):
    index: int
    relation: SemanticRelation
    relation_display: str
    text: str
    revealed: bool = False


class GameSessionCreate(BaseModel):
    language: str = Field(default="spa", pattern="^(spa|eng)$")
    synset_id: str | None = None


class GuessRequest(BaseModel):
    session_id: str
    guess: str = Field(min_length=1, max_length=100)


class ClueRevealRequest(BaseModel):
    session_id: str


class GuessResponse(BaseModel):
    session_id: str
    is_correct: bool
    revealed_clues: list[Clue]
    attempts_used: int
    max_clues: int
    is_game_over: bool
    is_solved: bool
    target_lemma: str | None = None
    target_synset: str | None = None
    alternative_lemmas: list[str] = Field(default_factory=list)
    score: int
    message: str



class GameSessionState(BaseModel):
    session_id: str
    language: str
    target_synset: str
    target_lemmas: list[str]
    clues: list[Clue]
    revealed_clues: list[Clue]
    attempts_used: int
    max_clues: int
    is_solved: bool
    is_game_over: bool
    score: int
