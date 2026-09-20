from app.captions import split_caption_text, segment_caption

def test_caption_chunks_stay_readable():
    out=split_caption_text("This is a long sentence that should become several short caption chunks")
    assert len(out)>1
    assert all(len(x.split())<=6 for x in out)

def test_caption_chunk_timing_fills_segment():
    out=segment_caption({"start":1,"end":5,"text":"one two three four five six seven"})
    assert out[0]["start"]==1
    assert abs(out[-1]["end"]-5)<0.001
    assert all(x["end"]>x["start"] for x in out)
