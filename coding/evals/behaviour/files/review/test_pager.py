from pager import paginate


def test_full_page_has_size_items():
    assert paginate(list(range(10)), 1, 3) == [0, 1, 2]


def test_last_page_keeps_the_remainder():
    assert paginate(list(range(9)), 3, 3) == [6, 7, 8]
