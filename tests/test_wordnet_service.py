import pytest
from app.core.synset_bank import SYNSET_CATALOG
from app.schemas.game import SemanticRelation
from app.services.wordnet_service import wordnet_service


def test_clue_hierarchy_sequence():
    clues = wordnet_service.generate_clues("dog.n.01", "spa")
    assert len(clues) == 5
    assert clues[0].relation == SemanticRelation.HYPERNYM
    assert clues[1].relation == SemanticRelation.CO_HYPONYM
    assert clues[2].relation == SemanticRelation.HYPONYM_1
    assert clues[3].relation == SemanticRelation.HYPONYM_2_OR_MERONYM
    assert clues[4].relation == SemanticRelation.SYNONYM


def test_bilingual_clues_presence():
    spa_clues = wordnet_service.generate_clues("tree.n.01", "spa")
    eng_clues = wordnet_service.generate_clues("tree.n.01", "eng")
    assert all(c.text for c in spa_clues)
    assert all(c.text for c in eng_clues)
    assert all(c.relation_display for c in spa_clues)
    assert all(c.relation_display for c in eng_clues)


def test_entire_catalog_verification():
    for entry in SYNSET_CATALOG:
        spa_clues = wordnet_service.generate_clues(entry.synset_id, "spa")
        eng_clues = wordnet_service.generate_clues(entry.synset_id, "eng")
        assert len(spa_clues) == 5
        assert len(eng_clues) == 5
        assert all(len(c.text.strip()) > 0 for c in spa_clues)
        assert all(len(c.text.strip()) > 0 for c in eng_clues)
