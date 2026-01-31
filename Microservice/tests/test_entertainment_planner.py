import pytest

from app.reasoning.llm_planner import _try_build_entertainment_steps


def _actions(steps):
    return [s.get("action") for s in steps]


def test_play_yt_music_builds_steps():
    steps = _try_build_entertainment_steps("play lofi beats on yt music")
    assert steps is not None
    assert _actions(steps)[:3] == ["open_app", "navigate", "wait"]
    assert steps[0]["target"] == "chrome.exe"
    assert steps[1]["url"].startswith("https://music.youtube.com/search?q=")
    assert steps[3]["action"] == "click_element"
    assert steps[3]["requires_vision_targeting"] is True


def test_play_spotify_builds_steps():
    steps = _try_build_entertainment_steps("play daft punk on spotify")
    assert steps is not None
    assert steps[0]["action"] == "open_app"
    assert steps[1]["action"] == "navigate"
    assert steps[1]["url"].startswith("https://open.spotify.com/search/")


@pytest.mark.parametrize(
    "cmd,expected_action",
    [
        ("pause", "media_play_pause"),
        ("play", "media_play_pause"),
        ("resume", "media_play_pause"),
        ("next", "media_next"),
        ("previous", "media_previous"),
        ("stop", "media_stop"),
    ],
)
def test_media_shortcuts(cmd, expected_action):
    steps = _try_build_entertainment_steps(cmd)
    assert steps == [{"action": expected_action}]
