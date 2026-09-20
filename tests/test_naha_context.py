from app.naha_context import compile_context, parse_commands


def test_command_parser_builds_nahalabs_creative_context():
    out = parse_commands(
        "/cargoiq /lead-gen /facebook-ad /nahalabs-authentic /south-african-authenticity"
    )
    assert out["product"] == "cargoiq"
    assert out["lane"] == "enterprise_intelligence"
    assert out["objective"] == "lead_gen"
    assert out["format"] == "facebook_ad"
    assert out["authenticity_profile"] == "nahalabs-authentic"


def test_context_falls_back_to_brief():
    out = compile_context(
        prompt="premium enterprise video",
        brief={
            "product": "CargoIQ",
            "objective": "proof",
            "format": "LinkedIn",
            "authenticity": True,
        },
    )
    assert out["product"] == "cargoiq"
    assert out["objective"] == "proof"
    assert out["format"] == "linkedin"
    assert out["authenticity_profile"] == "nahalabs-authentic"


def test_context_contains_growth_loop():
    out = parse_commands("")
    assert out["growth_loop"] == ["content", "distribution", "leads", "sales", "revenue", "analytics"]
