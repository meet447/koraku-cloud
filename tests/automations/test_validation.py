import pytest
from croniter import CroniterBadCronError

from koraku.automations.validation import validate_cron_expression, validate_timezone_iana


def test_validate_cron_expression_valid():
    """Test valid cron expressions are returned normalized."""
    assert validate_cron_expression("* * * * *") == "* * * * *"
    assert validate_cron_expression("0 12 * * *") == "0 12 * * *"
    assert validate_cron_expression("  * * * * *  ") == "* * * * *"
    assert validate_cron_expression("*/5 * * * *") == "*/5 * * * *"


def test_validate_cron_expression_invalid_parts_count():
    """Test cron expressions with incorrect number of fields."""
    with pytest.raises(ValueError, match="cron_expression must have exactly 5 fields"):
        validate_cron_expression("* * * *")

    with pytest.raises(ValueError, match="cron_expression must have exactly 5 fields"):
        validate_cron_expression("* * * * * *")

    with pytest.raises(ValueError, match="cron_expression must have exactly 5 fields"):
        validate_cron_expression("")


def test_validate_cron_expression_invalid_croniter():
    """Test cron expressions that are 5 fields but invalid cron syntax/ranges."""
    with pytest.raises(CroniterBadCronError):
        validate_cron_expression("60 * * * *")  # Minute out of range

    with pytest.raises(CroniterBadCronError):
        validate_cron_expression("* 24 * * *")  # Hour out of range

    with pytest.raises(CroniterBadCronError):
        validate_cron_expression("* * 32 * *")  # Day out of range

    with pytest.raises(CroniterBadCronError):
        validate_cron_expression("* * * 13 *")  # Month out of range

    with pytest.raises(CroniterBadCronError):
        validate_cron_expression("invalid cron format string here")


def test_validate_timezone_iana_valid():
    assert validate_timezone_iana("UTC") == "UTC"
    assert validate_timezone_iana("America/New_York") == "America/New_York"
    assert validate_timezone_iana("Europe/London") == "Europe/London"
    assert validate_timezone_iana("  Europe/London  ") == "Europe/London"


def test_validate_timezone_iana_padded():
    assert validate_timezone_iana("  UTC  ") == "UTC"
    assert validate_timezone_iana("  America/Los_Angeles") == "America/Los_Angeles"


def test_validate_timezone_iana_invalid():
    with pytest.raises(ValueError, match="Invalid IANA timezone: Invalid/Timezone"):
        validate_timezone_iana("Invalid/Timezone")

    with pytest.raises(ValueError, match="Invalid IANA timezone: Not/A_Timezone"):
        validate_timezone_iana("Not/A_Timezone")

    with pytest.raises(ValueError, match=r"Invalid IANA timezone: GMT\+1"):
        validate_timezone_iana("GMT+1")  # GMT+1 isn't a valid strict IANA timezone generally
