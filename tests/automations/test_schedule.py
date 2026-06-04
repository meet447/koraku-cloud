import pytest

from koraku_cloud.automations.schedule import preset_to_cron, schedule_label


def test_preset_every_n_minutes():
    assert preset_to_cron({"kind": "every_n_minutes", "every_n_minutes": 30}) == "*/30 * * * *"


def test_preset_weekdays():
    assert preset_to_cron({"kind": "weekdays", "hour": 8, "minute": 0}) == "0 8 * * 1-5"


def test_preset_custom():
    assert preset_to_cron({"kind": "custom", "cron_expression": "0 9 * * *"}) == "0 9 * * *"


def test_preset_invalid_kind():
    with pytest.raises(ValueError, match="kind"):
        preset_to_cron({"kind": "hourly"})


def test_schedule_label():
    assert "30 minutes" in schedule_label({"kind": "every_n_minutes", "every_n_minutes": 30}, None)
