from expense_audit import policy


def test_city_tiers():
    assert policy.city_tier("Bengaluru") == "X"
    assert policy.city_tier("Jaipur") == "Y"
    assert policy.city_tier("Shimla") == "Z"


def test_limits_lookup():
    assert policy.hotel_limit("G1", "Mumbai") == 4500
    assert policy.hotel_limit("G3", "Hosur") == 5000
    assert policy.meal_limit("G2") == 1500
    assert policy.transport_limit("G3") is None


def test_every_registered_clause_has_text():
    texts = policy.clause_texts()
    ids = [c["id"] for c in policy.clause_registry()]
    assert len(ids) == len(set(ids)) == 26
    for cid in ids:
        assert cid in texts and len(texts[cid]) > 20


def test_clause_text_is_exact_policy_wording():
    assert "more economical for the company than returning to base" in policy.clause_text("HTL-03")
    assert "₹10,000" in policy.clause_text("GEN-05")


def test_check_names_unique():
    checks = [c["check"] for c in policy.clause_registry() if "check" in c]
    assert len(checks) == len(set(checks))
