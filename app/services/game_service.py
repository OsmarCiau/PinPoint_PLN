import uuid
from app.core.config import settings
from app.schemas.game import (
    Clue,
    GameSessionState,
    GuessResponse,
)
from app.services.nlp_service import nlp_service
from app.services.wordnet_service import wordnet_service


class GameSession:
    def __init__(self, session_id: str, language: str, synset_id: str) -> None:
        self.session_id = session_id
        self.language = language
        self.synset_id = synset_id
        self.clues: list[Clue] = wordnet_service.generate_clues(synset_id, language)
        self.target_lemmas: list[str] = wordnet_service.get_target_lemmas(synset_id, language)
        self.primary_lemma: str = wordnet_service.get_primary_lemma(synset_id, language)
        self.target_forms: dict[str, set[str]] = nlp_service.precompute_target_forms(self.target_lemmas, language)
        self.revealed_count: int = 1
        self.attempts_used: int = 0
        self.is_solved: bool = False
        self.is_game_over: bool = False
        self.score: int = 0

    def get_revealed_clues(self) -> list[Clue]:
        return [
            Clue(
                index=c.index,
                relation=c.relation,
                relation_display=c.relation_display,
                text=c.text,
                revealed=True,
            )
            for c in self.clues[: self.revealed_count]
        ]

    def reveal_next_clue(self) -> bool:
        if self.revealed_count < settings.max_clues:
            self.revealed_count += 1
            self.clues[self.revealed_count - 1].revealed = True
            return True
        return False

    def calculate_score(self) -> int:
        if not self.is_solved:
            return 0
        return max(1, settings.max_clues - self.attempts_used + 1)

    def to_state(self) -> GameSessionState:
        return GameSessionState(
            session_id=self.session_id,
            language=self.language,
            target_synset=self.synset_id,
            target_lemmas=self.target_lemmas,
            clues=self.clues,
            revealed_clues=self.get_revealed_clues(),
            attempts_used=self.attempts_used,
            max_clues=settings.max_clues,
            is_solved=self.is_solved,
            is_game_over=self.is_game_over,
            score=self.score,
        )


class GameService:
    def __init__(self) -> None:
        self.sessions: dict[str, GameSession] = {}
        self.recent_synsets: list[str] = []

    def create_session(self, language: str = "spa", synset_id: str | None = None) -> GameSessionState:
        session_id = str(uuid.uuid4())
        chosen_synset = synset_id if synset_id else wordnet_service.get_random_synset_id(self.recent_synsets)
        self.recent_synsets.append(chosen_synset)
        if len(self.recent_synsets) > 20:
            self.recent_synsets.pop(0)

        session = GameSession(session_id=session_id, language=language, synset_id=chosen_synset)
        self.sessions[session_id] = session
        return session.to_state()


    def get_session(self, session_id: str) -> GameSession | None:
        return self.sessions.get(session_id)

    def process_guess(self, session_id: str, raw_guess: str) -> GuessResponse:
        session = self.get_session(session_id)
        if not session:
            return GuessResponse(
                session_id=session_id,
                is_correct=False,
                revealed_clues=[],
                attempts_used=0,
                max_clues=settings.max_clues,
                is_game_over=True,
                is_solved=False,
                score=0,
                message="Session not found" if session.language == "eng" else "Sesión no encontrada",
            )

        if session.is_game_over:
            return self._build_response(
                session,
                is_correct=session.is_solved,
                message=(
                    "The match has already finished."
                    if session.language == "eng"
                    else "La partida ya ha finalizado."
                ),
            )

        session.attempts_used += 1
        is_correct = nlp_service.is_match(
            raw_guess,
            session.target_lemmas,
            session.language,
            target_forms=session.target_forms,
        )

        if is_correct:
            session.is_solved = True
            session.is_game_over = True
            session.score = session.calculate_score()
            message = (
                f"¡Felicidades! Adivinaste la categoría en {session.attempts_used} intento(s)."
                if session.language == "spa"
                else f"Congratulations! You guessed the category in {session.attempts_used} attempt(s)."
            )
            return self._build_response(session, is_correct=True, message=message)

        if session.attempts_used >= settings.max_clues:
            session.is_game_over = True
            session.score = 0
            session.revealed_count = settings.max_clues
            for clue in session.clues:
                clue.revealed = True
            message = (
                f"¡Suerte para la próxima! La categoría correcta era: {session.primary_lemma.capitalize()}."
                if session.language == "spa"
                else f"Better luck next time! The category was: {session.primary_lemma.capitalize()}."
            )
            return self._build_response(session, is_correct=False, message=message)

        session.reveal_next_clue()
        message = (
            "¡Intento incorrecto! Se ha revelado la siguiente pista."
            if session.language == "spa"
            else "Incorrect guess! The next clue has been revealed."
        )
        return self._build_response(session, is_correct=False, message=message)

    def reveal_clue_manually(self, session_id: str) -> GuessResponse:
        session = self.get_session(session_id)
        if not session or session.is_game_over:
            return self._build_response(
                session,
                is_correct=session.is_solved if session else False,
                message=(
                    "Unable to reveal clue."
                    if not session or session.language == "eng"
                    else "No es posible revelar más pistas."
                ),
            )

        session.attempts_used += 1
        if session.revealed_count >= settings.max_clues or session.attempts_used >= settings.max_clues:
            session.is_game_over = True
            session.score = 0
            session.revealed_count = settings.max_clues
            message = (
                f"Has agotado todas las pistas. La categoría era: {session.primary_lemma.capitalize()}."
                if session.language == "spa"
                else f"All clues exhausted. The category was: {session.primary_lemma.capitalize()}."
            )
            return self._build_response(session, is_correct=False, message=message)

        session.reveal_next_clue()
        message = (
            "Pista revelada."
            if session.language == "spa"
            else "Clue revealed."
        )
        return self._build_response(session, is_correct=False, message=message)

    def _build_response(self, session: GameSession, is_correct: bool, message: str) -> GuessResponse:
        return GuessResponse(
            session_id=session.session_id,
            is_correct=is_correct,
            revealed_clues=session.get_revealed_clues(),
            attempts_used=session.attempts_used,
            max_clues=settings.max_clues,
            is_game_over=session.is_game_over,
            is_solved=session.is_solved,
            target_lemma=session.primary_lemma if session.is_game_over else None,
            target_synset=session.synset_id if session.is_game_over else None,
            alternative_lemmas=session.target_lemmas if session.is_game_over else [],
            score=session.score,
            message=message,
        )



game_service = GameService()
