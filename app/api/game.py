from fastapi import APIRouter, HTTPException, status
from app.core.synset_bank import SYNSET_CATALOG, SynsetEntry
from app.schemas.game import (
    ClueRevealRequest,
    GameSessionCreate,
    GameSessionState,
    GuessRequest,
    GuessResponse,
)
from app.services.game_service import game_service

router = APIRouter(prefix="/api/game", tags=["game"])


@router.post("/new", response_model=GameSessionState, status_code=status.HTTP_201_CREATED)
def start_new_game(payload: GameSessionCreate) -> GameSessionState:
    return game_service.create_session(
        language=payload.language,
        synset_id=payload.synset_id,
    )


@router.post("/guess", response_model=GuessResponse)
def submit_guess(payload: GuessRequest) -> GuessResponse:
    return game_service.process_guess(
        session_id=payload.session_id,
        raw_guess=payload.guess,
    )


@router.post("/reveal", response_model=GuessResponse)
def reveal_next_clue(payload: ClueRevealRequest) -> GuessResponse:
    return game_service.reveal_clue_manually(session_id=payload.session_id)


@router.get("/catalog", response_model=list[SynsetEntry])
def get_catalog() -> list[SynsetEntry]:
    return SYNSET_CATALOG


@router.get("/session/{session_id}", response_model=GameSessionState)
def get_session_state(session_id: str) -> GameSessionState:
    session = game_service.get_session(session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Game session not found",
        )
    return session.to_state()
