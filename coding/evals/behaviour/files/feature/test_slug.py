from slug import slugify


def test_lowercases_and_joins_words_with_dashes():
    assert slugify("Hello World") == "hello-world"


def test_drops_punctuation_and_collapses_spaces():
    assert slugify("  Ship it,   now!  ") == "ship-it-now"
