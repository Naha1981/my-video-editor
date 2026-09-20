from app.director import Clip, build_plan, sanitize_plan


def test_plan_is_30_seconds():
    clips = [
        Clip("1", "food_closeup.mp4", "x", 8, 1080, 1920, 30, {
            "visual_score": 90, "hero_time": 2.0, "scenes": 2,
            "audio": {"active_ranges": [[0.5, 7.5]], "silence_ratio": 0.1},
        }),
        Clip("2", "restaurant.mp4", "x", 10, 1920, 1080, 30, {
            "visual_score": 60, "hero_time": 4.0, "scenes": 1,
            "audio": {"active_ranges": [[0.2, 9.5]], "silence_ratio": 0.05},
        }),
    ]
    plan = build_plan(
        clips,
        "Create a 30-second premium restaurant advertisement with energetic pacing and NahaLabs logo",
        30,
    )
    assert plan["settings"]["priority"] == "food"
    assert plan["settings"]["logo_ending"] is True
    assert plan["version"] == "0.5"
    assert plan["edit_decision_graph"]
    assert plan["timeline"]


def test_visual_quality_and_food_prioritize():
    a = Clip("1", "food_closeup.mp4", "x", 5, 1080, 1920, 30, {
        "visual_score": 95, "hero_time": 1.0, "scenes": 1,
        "semantic": {"labels": {"food": 0.7, "hero": 0.4}},
        "audio": {"active_ranges": [[0, 5]], "silence_ratio": 0},
    })
    b = Clip("2", "street.mp4", "x", 5, 1080, 1920, 30, {
        "visual_score": 40, "hero_time": 1.0, "scenes": 1,
        "semantic": {"labels": {"food": 0.02, "hero": 0.03}},
        "audio": {"active_ranges": [[0, 5]], "silence_ratio": 0},
    })
    assert build_plan([b, a], "premium restaurant food ad", 10)["shots_ranked"][0]["filename"] == "food_closeup.mp4"


def test_transcript_window_is_preferred_for_dialogue():
    clip = Clip("1", "talking.mp4", "x", 20, 1920, 1080, 30, {
        "visual_score": 70, "hero_time": 2.0, "scenes": 3,
        "audio": {"active_ranges": [[1, 19]], "silence_ratio": 0.05},
        "transcript": {
            "available": True,
            "segments": [{"start": 12, "end": 18, "text": "Welcome"}],
            "speech_ranges": [[12, 18]],
        },
    })
    first = build_plan([clip], "balanced video with dialogue and background music", 6)["timeline"][0]
    assert first["source_start"] >= 10


def test_duck_ranges_are_mapped_to_output_timeline():
    clip = Clip("1", "talking.mp4", "x", 20, 1920, 1080, 30, {
        "visual_score": 70, "hero_time": 2.0, "scenes": 1,
        "audio": {"active_ranges": [[0, 20]], "silence_ratio": 0},
        "transcript": {
            "available": True,
            "segments": [{"start": 12, "end": 18, "text": "Welcome"}],
            "speech_ranges": [[12, 18]],
        },
    })
    plan = build_plan([clip], "6 second dialogue ad with music", 6)
    assert plan["audio"]["duck_ranges"]


def test_sanitize_plan_removes_disabled_and_unknown_clips():
    plan = {
        "settings": {"duration": 6},
        "timeline": [
            {"id": "1", "type": "clip", "enabled": True, "clip_id": "ok", "source_start": 0, "duration": 4},
            {"id": "2", "type": "clip", "enabled": False, "clip_id": "ok", "source_start": 0, "duration": 2},
            {"id": "3", "type": "clip", "enabled": True, "clip_id": "bad", "source_start": 0, "duration": 3},
        ],
    }
    clean = sanitize_plan(plan, {"ok"}, 6)
    assert len(clean["timeline"]) == 1
    assert clean["timeline"][0]["clip_id"] == "ok"


def test_v04_storyboard_has_hook_and_brand_close():
    from app.storyboard import build_storyboard
    plan = {
        "timeline": [
            {"type": "clip", "enabled": True, "filename": "hero.mp4", "duration": 3, "reasons": ["visual quality"]},
            {"type": "logo", "enabled": True, "duration": 2},
        ]
    }
    board = build_storyboard(plan)
    assert board[0]["type"] == "hook"
    assert board[-1]["type"] == "brand_close"


def test_v04_captions_are_mapped_to_output_time():
    from app.storyboard import add_transcript_captions
    plan = {
        "timeline": [{
            "type": "clip", "enabled": True, "source_start": 10, "duration": 5,
            "transcript_segments_source": [{"start": 11, "end": 13, "text": "Fresh from our kitchen"}]
        }]
    }
    out = add_transcript_captions(plan)
    assert out["captions"][0]["text"] == "Fresh from our kitchen"
    assert out["captions"][0]["start"] == 1.0


def test_website_brief_compiler_is_deterministic():
    from app.brief import compile_creative_brief
    site={"url":"https://example.com","domain":"example.com","title":"Gemelli Kitchen","meta":{"description":"Premium restaurant dining and reservations"},"text":"Fresh food, chef, menu and table bookings."}
    brief=compile_creative_brief(site)
    assert brief["category"] == "restaurant"
    assert brief["cta"] == "Book your table"
    assert brief["business_name"] == "Gemelli Kitchen"


def test_stock_requirements_follow_category():
    from app.stock import shot_requirements
    req=shot_requirements({"category":"restaurant"})
    assert req[0]["beat"] == "hook"
    assert any("customer" in x["need"].lower() for x in req)


def test_creative_direction_has_concept_and_shot_sequence():
    from app.creative import creative_direction
    direction=creative_direction({"category":"restaurant","cta":"Book your table","audience":"local diners"}, "premium energetic restaurant advertisement")
    assert direction["selected"]["name"] == "The Craving Cut"
    assert direction["selected"]["shot_sequence"][0] == "hero_food"
    assert direction["pacing"] == "energetic"


def test_storyboard_uses_creative_intent():
    from app.storyboard import build_storyboard
    plan={
        "creative_direction":{"selected":{"shot_sequence":["hero_food","craft","cta"]}},
        "timeline":[
            {"type":"clip","enabled":True,"filename":"hero.mp4","duration":2},
            {"type":"clip","enabled":True,"filename":"chef.mp4","duration":2},
            {"type":"logo","enabled":True,"duration":2},
        ],
    }
    board=build_storyboard(plan)
    assert board[0]["creative_intent"] == "hero_food"
    assert board[1]["creative_intent"] == "craft"
    assert board[-1]["creative_intent"] == "cta"


def test_creative_intent_affects_clip_score():
    from app.director import Clip, score_clip
    clip=Clip(id="1",filename="hero_food_closeup.mp4",path="hero_food_closeup.mp4",duration=5,width=1080,height=1920,fps=30,analysis={"visual_score":70})
    base,_=score_clip(clip,{"priority":"food"},{"selected":{"shot_sequence":["experience","cta"]}})
    matched,reasons=score_clip(clip,{"priority":"food"},{"selected":{"shot_sequence":["hero_food","cta"]}})
    assert matched > base
    assert any("creative shot-intent" in x for x in reasons)


def test_semantic_label_can_match_creative_intent():
    from app.director import Clip, score_clip
    clip=Clip(id="1",filename="camera_001.mp4",path="camera_001.mp4",duration=5,width=1080,height=1920,fps=30,analysis={"visual_score":70,"semantic":{"labels":{"experience":0.75}}})
    score,reasons=score_clip(clip,{"priority":"visual_story"},{"selected":{"shot_sequence":["experience","cta"]}})
    assert score > 50
    assert any("AI experience relevance" in x for x in reasons)


def test_shot_intelligence_builds_explainable_tags():
    from app.shot_intelligence import classify_shot, intent_fit
    analysis={"semantic":{"labels":{"food":0.82,"experience":0.18}},"hero_time":1.2}
    info=classify_shot(analysis)
    assert "food" in info["tags"] and "hero_candidate" in info["tags"]
    assert intent_fit(analysis,"hero_food") == 0.82
