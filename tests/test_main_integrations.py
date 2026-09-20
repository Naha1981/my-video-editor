from app.main import AssetScoutRequest, StockScoutRequest


def test_new_requests_are_backward_compatible():
    assert AssetScoutRequest(url="https://example.com").task == ""
    assert StockScoutRequest().max_missions == 6
