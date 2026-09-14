from app.services.certificate_service import assignments_all_approved


def test_no_assignments_is_approved():
    assert assignments_all_approved(set(), set()) is True


def test_all_graded_is_approved():
    assert assignments_all_approved({1, 2, 3}, {1, 2, 3}) is True


def test_one_ungraded_is_not_approved():
    assert assignments_all_approved({1, 2, 3}, {1, 2}) is False


def test_extra_graded_ids_ignored():
    assert assignments_all_approved({1, 2}, {1, 2, 9}) is True
