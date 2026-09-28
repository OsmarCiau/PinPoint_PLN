import pytest
from app.services.nlp_service import nlp_service


def test_strip_accents():
    assert nlp_service.strip_accents("árbol") == "arbol"
    assert nlp_service.strip_accents("canción") == "cancion"
    assert nlp_service.strip_accents("pingüino") == "pinguino"


def test_clean_text():
    assert nlp_service.clean_text("Perro_Guía!") == "perro guía"
    assert nlp_service.clean_text("   Gato...   ") == "gato"


def test_strip_leading_articles_spanish():
    assert nlp_service.strip_leading_articles("el perro", "spa") == "perro"
    assert nlp_service.strip_leading_articles("una manzana", "spa") == "manzana"
    assert nlp_service.strip_leading_articles("los árboles", "spa") == "árboles"


def test_strip_leading_articles_english():
    assert nlp_service.strip_leading_articles("the dog", "eng") == "dog"
    assert nlp_service.strip_leading_articles("an apple", "eng") == "apple"


def test_spanish_matching_variations():
    assert nlp_service.is_match("los perros", ["perro"], "spa")
    assert nlp_service.is_match("árboles", ["árbol"], "spa")
    assert nlp_service.is_match("arboles", ["árbol"], "spa")
    assert nlp_service.is_match("el gato", ["gato"], "spa")
    assert not nlp_service.is_match("caballo", ["gato"], "spa")


def test_english_matching_variations():
    assert nlp_service.is_match("the dogs", ["dog"], "eng")
    assert nlp_service.is_match("cats", ["cat"], "eng")
    assert nlp_service.is_match("an apple", ["apple"], "eng")
    assert not nlp_service.is_match("horse", ["cat"], "eng")
