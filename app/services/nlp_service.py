import re
import subprocess
import unicodedata
from functools import lru_cache
from nltk.stem import WordNetLemmatizer, SnowballStemmer
from app.core.config import settings


@lru_cache(maxsize=1024)
def _cached_canonicalize(text: str, language: str) -> str:
    cleaned = nlp_service.clean_text(text)
    stripped = nlp_service.strip_leading_articles(cleaned, language)
    if not stripped:
        return ""

    if language == "spa":
        freeling_lemmas = nlp_service.lemmatize_spanish_freeling(stripped)
        if freeling_lemmas:
            tokens = freeling_lemmas
        else:
            tokens = nlp_service.lemmatize_spanish_fallback(stripped)
    else:
        tokens = nlp_service.lemmatize_english(stripped)

    normalized_tokens = [nlp_service.strip_accents(token).lower() for token in tokens]
    return " ".join(normalized_tokens)


class NLPService:
    def __init__(self) -> None:
        self.english_lemmatizer = WordNetLemmatizer()
        self.spanish_stemmer = SnowballStemmer("spanish")
        self.spanish_articles = {"el", "la", "los", "las", "un", "una", "unos", "unas", "al", "del", "lo"}
        self.english_articles = {"the", "a", "an"}

    def strip_accents(self, text: str) -> str:
        decomposed = unicodedata.normalize("NFD", text)
        return "".join(char for char in decomposed if unicodedata.category(char) != "Mn")

    def clean_text(self, text: str) -> str:
        normalized = text.replace("_", " ").lower()
        cleaned = re.sub(r"[^\w\s]", "", normalized)
        return re.sub(r"\s+", " ", cleaned).strip()

    def strip_leading_articles(self, text: str, language: str) -> str:
        words = text.split()
        if not words:
            return text

        articles = self.spanish_articles if language == "spa" else self.english_articles
        while words and words[0] in articles:
            words.pop(0)

        return " ".join(words) if words else text

    def lemmatize_spanish_freeling(self, text: str) -> list[str] | None:
        if not settings.is_freeling_available():
            return None

        try:
            env = settings.get_freeling_env()
            process = subprocess.run(
                [
                    settings.freeling_bin,
                    "-f",
                    settings.freeling_config,
                    "--outlv",
                    "tagged",
                ],
                input=f"{text}\n",
                text=True,
                capture_output=True,
                env=env,
                timeout=4,
                check=True,
            )

            lemmas: list[str] = []
            for line in process.stdout.strip().splitlines():
                parts = line.strip().split()
                if len(parts) >= 2:
                    lemmas.append(parts[1])

            return lemmas if lemmas else None
        except Exception:
            return None

    def batch_lemmatize_spanish_freeling(self, texts: list[str]) -> list[list[str]] | None:
        if not settings.is_freeling_available() or not texts:
            return None

        cleaned_texts = [self.clean_text(t) for t in texts]
        stripped_texts = [self.strip_leading_articles(t, "spa") for t in cleaned_texts]
        word_counts = [len(t.split()) for t in stripped_texts]
        if sum(word_counts) == 0:
            return None

        try:
            env = settings.get_freeling_env()
            input_payload = " ".join(stripped_texts) + "\n"
            process = subprocess.run(
                [
                    settings.freeling_bin,
                    "-f",
                    settings.freeling_config,
                    "--outlv",
                    "tagged",
                ],
                input=input_payload,
                text=True,
                capture_output=True,
                env=env,
                timeout=6,
                check=True,
            )

            raw_lemmas: list[str] = []
            for line in process.stdout.strip().splitlines():
                parts = line.strip().split()
                if len(parts) >= 2:
                    raw_lemmas.append(parts[1])

            if len(raw_lemmas) != sum(word_counts):
                return None

            results: list[list[str]] = []
            curr = 0
            for count in word_counts:
                results.append(raw_lemmas[curr : curr + count])
                curr += count

            return results
        except Exception:
            return None

    def lemmatize_spanish_fallback(self, text: str) -> list[str]:
        words = text.split()
        return [self.spanish_stemmer.stem(word) for word in words]

    def lemmatize_english(self, text: str) -> list[str]:
        words = text.split()
        lemmas: list[str] = []
        for word in words:
            lemmatized = self.english_lemmatizer.lemmatize(word, pos="n")
            if lemmatized == word:
                lemmatized = self.english_lemmatizer.lemmatize(word, pos="v")
            lemmas.append(lemmatized)
        return lemmas

    def lemmatize_tokens(self, text: str, language: str) -> list[str]:
        cleaned = self.clean_text(text)
        stripped = self.strip_leading_articles(cleaned, language)
        if not stripped:
            return []

        if language == "spa":
            freeling_lemmas = self.lemmatize_spanish_freeling(stripped)
            if freeling_lemmas:
                return freeling_lemmas
            return self.lemmatize_spanish_fallback(stripped)

        return self.lemmatize_english(stripped)

    def canonicalize(self, text: str, language: str) -> str:
        return _cached_canonicalize(text, language)

    def get_stems(self, text: str, language: str) -> str:
        cleaned = self.clean_text(text)
        stripped = self.strip_leading_articles(cleaned, language)
        unaccented = self.strip_accents(stripped)
        words = unaccented.split()
        if language == "spa":
            return " ".join(self.spanish_stemmer.stem(w) for w in words)
        return " ".join(self.english_lemmatizer.lemmatize(w) for w in words)

    def precompute_target_forms(self, target_lemmas: list[str], language: str) -> dict[str, set[str]]:
        clean_set: set[str] = set()
        canonical_set: set[str] = set()
        stem_set: set[str] = set()

        for target in target_lemmas:
            clean = self.strip_accents(self.strip_leading_articles(self.clean_text(target), language))
            if clean:
                clean_set.add(clean)
            stem = self.get_stems(target, language)
            if stem:
                stem_set.add(stem)

        if language == "spa":
            batch_lemmas = self.batch_lemmatize_spanish_freeling(target_lemmas)
            if batch_lemmas:
                for tokens in batch_lemmas:
                    canon = " ".join(self.strip_accents(token).lower() for token in tokens)
                    if canon:
                        canonical_set.add(canon)
            else:
                for target in target_lemmas:
                    canon = self.canonicalize(target, language)
                    if canon:
                        canonical_set.add(canon)
        else:
            for target in target_lemmas:
                canon = self.canonicalize(target, language)
                if canon:
                    canonical_set.add(canon)

        return {
            "clean": clean_set,
            "canonical": canonical_set,
            "stem": stem_set,
        }

    def is_match(
        self,
        guess: str,
        target_lemmas: list[str],
        language: str,
        target_forms: dict[str, set[str]] | None = None,
    ) -> bool:
        if target_forms is None:
            target_forms = self.precompute_target_forms(target_lemmas, language)

        guess_cleaned = self.strip_accents(self.strip_leading_articles(self.clean_text(guess), language))
        if guess_cleaned and guess_cleaned in target_forms["clean"]:
            return True

        canonical_guess = self.canonicalize(guess, language)
        if canonical_guess and canonical_guess in target_forms["canonical"]:
            return True

        guess_stem = self.get_stems(guess, language)
        if guess_stem and guess_stem in target_forms["stem"]:
            return True

        return False


nlp_service = NLPService()
