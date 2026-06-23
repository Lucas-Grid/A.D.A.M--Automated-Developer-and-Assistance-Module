"""Tests for scheduler parse_schedule."""
import pytest

from ADAM.automations.scheduler import (
    CronSchedule,
    IntervalSchedule,
    OneTimeSchedule,
    parse_schedule,
)


def test_parse_cron():
    sched = parse_schedule("0 2 * * *")
    assert isinstance(sched, CronSchedule)


def test_parse_interval():
    sched = parse_schedule("every 15 minutes")
    assert isinstance(sched, IntervalSchedule)
    assert sched.seconds == 15


def test_parse_onetime():
    sched = parse_schedule("run once")
    assert isinstance(sched, OneTimeSchedule)


def test_cron_next_run():
    sched = CronSchedule(cron_expr="0 2 * * *")
    next_run = sched.next_run()
    assert next_run is not None
    assert next_run.hour == 2
    assert next_run.minute == 0


def test_interval_next_run():
    sched = IntervalSchedule(seconds=60)
    next_run = sched.next_run()
    assert next_run is not None


def test_invalid_schedule():
    with pytest.raises(ValueError):
        parse_schedule("unknown format")
