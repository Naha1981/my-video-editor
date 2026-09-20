from app.director import Clip, build_plan

def test_plan_is_30_seconds():
    clips=[Clip("1","food_closeup.mp4","x",8,1080,1920,30,{"visual_score":90,"hero_time":2.0,"scenes":2,"audio":{"active_ranges":[[0.5,7.5]],"silence_ratio":0.1}}),
           Clip("2","restaurant.mp4","x",10,1920,1080,30,{"visual_score":60,"hero_time":4.0,"scenes":1,"audio":{"active_ranges":[[0.2,9.5]],"silence_ratio":0.05}})]
    plan=build_plan(clips,"Create a 30-second premium restaurant advertisement with energetic pacing and NahaLabs logo",30)
    assert plan["settings"]["priority"]=="food";assert plan["settings"]["logo_ending"] is True;assert plan["version"]=="0.2";assert plan["timeline"]

def test_visual_quality_and_food_prioritize():
    a=Clip("1","food_closeup.mp4","x",5,1080,1920,30,{"visual_score":95,"hero_time":1.0,"scenes":1,"audio":{"active_ranges":[[0,5]],"silence_ratio":0}})
    b=Clip("2","street.mp4","x",5,1080,1920,30,{"visual_score":40,"hero_time":1.0,"scenes":1,"audio":{"active_ranges":[[0,5]],"silence_ratio":0}})
    assert build_plan([b,a],"premium restaurant food ad",10)["shots_ranked"][0]["filename"]=="food_closeup.mp4"

def test_hero_window_moves_to_active_content():
    clip=Clip("1","talking.mp4","x",20,1920,1080,30,{"visual_score":70,"hero_time":15.0,"scenes":3,"audio":{"active_ranges":[[1,3],[11,19]],"silence_ratio":0.35}})
    first=build_plan([clip],"Make a balanced video",6)["timeline"][0]
    assert first["source_start"]>=10
