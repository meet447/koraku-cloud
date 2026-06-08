import pytest

from koraku_cloud.automations.schedule import cron_human_label, preset_to_cron, schedule_label


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


def test_cron_human_label_every_n_minutes():
    assert schedule_label(None, "*/5 * * * *") == "Every 5 minutes"
    assert cron_human_label("*/1 * * * *") == "Every 1 minute"


def test_cron_human_label_daily_and_weekdays():
    assert cron_human_label("0 9 * * *") == "Daily at 09:00"
    assert cron_human_label("30 8 * * 1-5") == "Weekdays at 08:30"
    assert cron_human_label("0 16 * * 5") == "Weekly Fri 16:00"


def test_schedule_label_custom_cron():
    assert schedule_label({"kind": "custom", "cron_expression": "*/5 * * * *"}, "*/5 * * * *") == (
        "Every 5 minutes"
    )
