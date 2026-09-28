import random
from nltk.corpus import wordnet as wn
from app.core.synset_bank import SYNSET_CATALOG
from app.schemas.game import Clue, SemanticRelation


class WordNetService:
    RELATION_DISPLAY: dict[str, dict[SemanticRelation, str]] = {
        "spa": {
            SemanticRelation.HYPERNYM: "Hiperónimo",
            SemanticRelation.CO_HYPONYM: "Co-hipónimo",
            SemanticRelation.HYPONYM_1: "Hipónimo 1",
            SemanticRelation.HYPONYM_2_OR_MERONYM: "Hipónimo 2 / Merónimo",
            SemanticRelation.SYNONYM: "Lema Clave",
        },
        "eng": {
            SemanticRelation.HYPERNYM: "Hypernym",
            SemanticRelation.CO_HYPONYM: "Co-hyponym",
            SemanticRelation.HYPONYM_1: "Hyponym 1",
            SemanticRelation.HYPONYM_2_OR_MERONYM: "Hyponym 2 / Meronym",
            SemanticRelation.SYNONYM: "Key Lemma",
        },
    }

    TAXONOMIC_ENDINGS: tuple[str, ...] = (
        "idae",
        "ini",
        "inae",
        "formes",
        "oidea",
        "phyta",
        "aceae",
    )

    BINOMIAL_PREFIXES: tuple[str, ...] = (
        "felis",
        "canis",
        "panthera",
        "equus",
        "ursus",
        "vulpes",
        "homo",
        "bos",
        "sus",
        "ovis",
        "capra",
    )

    def clean_lemma_name(self, raw_name: str) -> str:
        return raw_name.replace("_", " ").strip()

    def lemma_priority(self, lemma: str) -> tuple[int, int]:
        lower = lemma.lower()
        is_taxonomic = any(lower.endswith(e) for e in self.TAXONOMIC_ENDINGS)
        is_binomial = len(lower.split()) > 1 and any(lower.startswith(prefix) for prefix in self.BINOMIAL_PREFIXES)
        penalty = 1 if (is_taxonomic or is_binomial) else 0
        return (penalty, len(lemma))

    def get_synset_frequency(self, synset) -> int:
        return max([l.count() for l in synset.lemmas("eng")] or [0])

    def get_clean_lemmas(self, synset, language: str, fallback_to_eng: bool = True) -> list[str]:
        raw_lemmas = synset.lemmas(language)
        cleaned = [self.clean_lemma_name(l.name()) for l in raw_lemmas if l.name()]
        if not cleaned and fallback_to_eng and language != "eng":
            cleaned = [self.clean_lemma_name(l.name()) for l in synset.lemmas("eng") if l.name()]
        unique_lemmas: list[str] = []
        for lemma in cleaned:
            if lemma and lemma.lower() not in [u.lower() for u in unique_lemmas]:
                unique_lemmas.append(lemma)
        return sorted(unique_lemmas, key=self.lemma_priority)

    def get_target_lemmas(self, synset_id: str, language: str) -> list[str]:
        synset = wn.synset(synset_id)
        lemmas = self.get_clean_lemmas(synset, language, fallback_to_eng=False)
        if not lemmas:
            lemmas = self.get_clean_lemmas(synset, "eng")
        return lemmas

    def get_primary_lemma(self, synset_id: str, language: str) -> str:
        lemmas = self.get_target_lemmas(synset_id, language)
        if not lemmas:
            synset = wn.synset(synset_id)
            return synset.name().split(".")[0].replace("_", " ")
        return lemmas[0]

    def get_relation_label(self, relation: SemanticRelation, language: str) -> str:
        lang_dict = self.RELATION_DISPLAY.get(language, self.RELATION_DISPLAY["spa"])
        return lang_dict.get(relation, relation.value)

    def generate_clues(self, synset_id: str, language: str) -> list[Clue]:
        synset = wn.synset(synset_id)
        target_lemmas = set(l.lower() for l in self.get_target_lemmas(synset_id, language))
        used_clue_texts: set[str] = set()

        hypers = sorted(
            synset.hypernyms() + synset.instance_hypernyms(),
            key=lambda h: h.max_depth(),
            reverse=True,
        )

        clue_1_text = ""
        for fallback in (False, True):
            if clue_1_text:
                break
            queue = list(hypers)
            visited = set(queue)
            while queue:
                curr = queue.pop(0)
                for lemma in self.get_clean_lemmas(curr, language, fallback_to_eng=fallback):
                    if lemma.lower() not in target_lemmas and lemma.lower() not in used_clue_texts:
                        clue_1_text = lemma
                        break
                if clue_1_text:
                    break
                parents = sorted(
                    curr.hypernyms() + curr.instance_hypernyms(),
                    key=lambda p: p.max_depth(),
                    reverse=True,
                )
                for parent in parents:
                    if parent not in visited:
                        visited.add(parent)
                        queue.append(parent)

        if not clue_1_text:
            clue_1_text = synset.name().split(".")[0].replace("_", " ")
        used_clue_texts.add(clue_1_text.lower())

        co_hypos: list[str] = []
        for fallback in (False, True):
            if co_hypos:
                break
            for hyper in hypers:
                siblings = sorted(
                    hyper.hyponyms() + hyper.instance_hyponyms(),
                    key=self.get_synset_frequency,
                    reverse=True,
                )
                for sibling in siblings:
                    if sibling != synset:
                        sibling_lemmas = self.get_clean_lemmas(sibling, language, fallback_to_eng=fallback)
                        for lemma in sibling_lemmas:
                            if (
                                lemma.lower() not in target_lemmas
                                and lemma.lower() not in used_clue_texts
                                and lemma not in co_hypos
                            ):
                                co_hypos.append(lemma)
                                break
            if not co_hypos:
                for hyper in hypers:
                    grandparents = sorted(
                        hyper.hypernyms() + hyper.instance_hypernyms(),
                        key=lambda g: g.max_depth(),
                        reverse=True,
                    )
                    for grand in grandparents:
                        cousins = sorted(
                            grand.hyponyms() + grand.instance_hyponyms(),
                            key=self.get_synset_frequency,
                            reverse=True,
                        )
                        for cousin in cousins:
                            if cousin != hyper and cousin != synset:
                                cousin_lemmas = self.get_clean_lemmas(cousin, language, fallback_to_eng=fallback)
                                for lemma in cousin_lemmas:
                                    if (
                                        lemma.lower() not in target_lemmas
                                        and lemma.lower() not in used_clue_texts
                                        and lemma not in co_hypos
                                    ):
                                        co_hypos.append(lemma)
                                        break

        clue_2_text = co_hypos[0] if co_hypos else clue_1_text
        used_clue_texts.add(clue_2_text.lower())

        hypos = sorted(
            synset.hyponyms() + synset.instance_hyponyms(),
            key=self.get_synset_frequency,
            reverse=True,
        )
        hypos_candidates: list[str] = []
        for fallback in (False, True):
            if len(hypos_candidates) >= 4:
                break
            for hypo in hypos:
                hypo_lemmas = self.get_clean_lemmas(hypo, language, fallback_to_eng=fallback)
                for lemma in hypo_lemmas:
                    if (
                        lemma.lower() not in target_lemmas
                        and lemma.lower() not in used_clue_texts
                        and lemma not in hypos_candidates
                    ):
                        hypos_candidates.append(lemma)
                        break

            if not hypos_candidates:
                for hypo in hypos:
                    subs = sorted(
                        hypo.hyponyms() + hypo.instance_hyponyms(),
                        key=self.get_synset_frequency,
                        reverse=True,
                    )
                    for sub in subs:
                        sub_lemmas = self.get_clean_lemmas(sub, language, fallback_to_eng=fallback)
                        for lemma in sub_lemmas:
                            if (
                                lemma.lower() not in target_lemmas
                                and lemma.lower() not in used_clue_texts
                                and lemma not in hypos_candidates
                            ):
                                hypos_candidates.append(lemma)
                                break

            if not hypos_candidates:
                meronym_list = sorted(
                    synset.part_meronyms() + synset.substance_meronyms() + synset.member_meronyms(),
                    key=self.get_synset_frequency,
                    reverse=True,
                )
                for part in meronym_list:
                    part_lemmas = self.get_clean_lemmas(part, language, fallback_to_eng=fallback)
                    for lemma in part_lemmas:
                        if (
                            lemma.lower() not in target_lemmas
                            and lemma.lower() not in used_clue_texts
                            and lemma not in hypos_candidates
                        ):
                            hypos_candidates.append(lemma)
                            break

        clue_3_text = hypos_candidates[0] if hypos_candidates else clue_2_text
        used_clue_texts.add(clue_3_text.lower())

        meronym_pool = sorted(
            synset.part_meronyms() + synset.substance_meronyms() + synset.member_meronyms(),
            key=self.get_synset_frequency,
            reverse=True,
        )
        clue_4_text = ""
        for fallback in (False, True):
            if clue_4_text:
                break
            for part in meronym_pool:
                part_lemmas = self.get_clean_lemmas(part, language, fallback_to_eng=fallback)
                for lemma in part_lemmas:
                    if (
                        lemma.lower() not in target_lemmas
                        and lemma.lower() not in used_clue_texts
                    ):
                        clue_4_text = lemma
                        break
                if clue_4_text:
                    break
            if not clue_4_text and len(hypos_candidates) > 1:
                clue_4_text = hypos_candidates[1]
                break

        holo_pool = sorted(
            synset.member_holonyms() + synset.part_holonyms() + synset.substance_holonyms(),
            key=self.get_synset_frequency,
            reverse=True,
        )
        if not clue_4_text:
            for fallback in (False, True):
                if clue_4_text:
                    break
                for holo in holo_pool:
                    holo_lemmas = self.get_clean_lemmas(holo, language, fallback_to_eng=fallback)
                    for lemma in holo_lemmas:
                        if (
                            lemma.lower() not in target_lemmas
                            and lemma.lower() not in used_clue_texts
                        ):
                            clue_4_text = lemma
                            break
                    if clue_4_text:
                        break
            if not clue_4_text and len(co_hypos) > 1:
                clue_4_text = co_hypos[1]
            elif not clue_4_text:
                clue_4_text = clue_3_text

        used_clue_texts.add(clue_4_text.lower())

        clue_5_text = ""
        for fallback in (False, True):
            if clue_5_text:
                break
            for hypo in hypos_candidates:
                if (
                    hypo.lower() not in target_lemmas
                    and hypo.lower() not in used_clue_texts
                ):
                    clue_5_text = hypo
                    break
            if not clue_5_text:
                for part in meronym_pool:
                    for lemma in self.get_clean_lemmas(part, language, fallback_to_eng=fallback):
                        if (
                            lemma.lower() not in target_lemmas
                            and lemma.lower() not in used_clue_texts
                        ):
                            clue_5_text = lemma
                            break
                    if clue_5_text:
                        break
            if not clue_5_text:
                for hypo in hypos:
                    subs = sorted(
                        hypo.hyponyms() + hypo.instance_hyponyms(),
                        key=self.get_synset_frequency,
                        reverse=True,
                    )
                    for sub in subs:
                        for lemma in self.get_clean_lemmas(sub, language, fallback_to_eng=fallback):
                            if (
                                lemma.lower() not in target_lemmas
                                and lemma.lower() not in used_clue_texts
                            ):
                                clue_5_text = lemma
                                break
                        if clue_5_text:
                            break
                    if clue_5_text:
                        break
            if not clue_5_text:
                for holo in holo_pool:
                    for lemma in self.get_clean_lemmas(holo, language, fallback_to_eng=fallback):
                        if (
                            lemma.lower() not in target_lemmas
                            and lemma.lower() not in used_clue_texts
                        ):
                            clue_5_text = lemma
                            break
                    if clue_5_text:
                        break

        if not clue_5_text:
            clue_5_text = clue_4_text

        used_clue_texts.add(clue_5_text.lower())

        return [
            Clue(
                index=1,
                relation=SemanticRelation.HYPERNYM,
                relation_display=self.get_relation_label(SemanticRelation.HYPERNYM, language),
                text=clue_1_text,
                revealed=True,
            ),
            Clue(
                index=2,
                relation=SemanticRelation.CO_HYPONYM,
                relation_display=self.get_relation_label(SemanticRelation.CO_HYPONYM, language),
                text=clue_2_text,
                revealed=False,
            ),
            Clue(
                index=3,
                relation=SemanticRelation.HYPONYM_1,
                relation_display=self.get_relation_label(SemanticRelation.HYPONYM_1, language),
                text=clue_3_text,
                revealed=False,
            ),
            Clue(
                index=4,
                relation=SemanticRelation.HYPONYM_2_OR_MERONYM,
                relation_display=self.get_relation_label(SemanticRelation.HYPONYM_2_OR_MERONYM, language),
                text=clue_4_text,
                revealed=False,
            ),
            Clue(
                index=5,
                relation=SemanticRelation.SYNONYM,
                relation_display=self.get_relation_label(SemanticRelation.SYNONYM, language),
                text=clue_5_text,
                revealed=False,
            ),
        ]

    def get_random_synset_id(self, exclude_ids: list[str] | None = None) -> str:
        if exclude_ids:
            available = [entry.synset_id for entry in SYNSET_CATALOG if entry.synset_id not in exclude_ids]
            if available:
                return random.choice(available)
        return random.choice(SYNSET_CATALOG).synset_id


wordnet_service = WordNetService()
