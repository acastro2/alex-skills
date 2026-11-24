from shop.slug import slugify


def test_joins_words_with_dashes():
    assert slugify("Hello World") == "hello-world"
