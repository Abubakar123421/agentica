from app.security import hash_password, token_hash, verify_password


def test_password_hash_is_salted_and_verifiable():
    first = hash_password("correct horse battery staple")
    second = hash_password("correct horse battery staple")

    assert first != second
    assert verify_password("correct horse battery staple", first)
    assert not verify_password("wrong password", first)


def test_tracking_and_session_tokens_are_keyed():
    assert token_hash("one") == token_hash("one")
    assert token_hash("one") != token_hash("two")
