"""#577, #594: the conftest guard fails a test that logs an app record at
WARNING or above it did not declare with expect_app_log, so a fake whose
failure a best-effort path swallows and logs still fails its test. It also
fails a declared expectation that matched no record."""

import logging
from pathlib import Path

from tests import conftest

BACKEND = Path(__file__).resolve().parent.parent
# Top-level code that is not the app: codegen output, one-off scripts, tests.
NOT_APP = {"contracts", "scripts", "tests"}
# The inner runs share the outer test's loggers, so the outer guard sees their
# records too and the outer test declares them.
PYTESTER_ARGS = ("-p", "no:cacheprovider", "-p", "no:asyncio")
INNER_IMPORTS = """
import logging

import pytest

from tests.conftest import _no_unexpected_app_logs, expect_app_log
"""


def test_app_warnings_and_errors_are_recorded_third_party_and_info_are_not():
    logging.getLogger("services.retrieval_service").error("query failed")
    logging.getLogger("main").warning("startup degraded")
    logging.getLogger("services.llm").info("settled")
    logging.getLogger("litellm").warning("third party")
    logging.getLogger("servicesx").warning("not an app package")

    assert [(r.name, r.getMessage()) for r in conftest._app_log_records] == [
        ("services.retrieval_service", "query failed"),
        ("main", "startup degraded"),
    ]
    # Cleared, so this test's own teardown check passes.
    conftest._app_log_records.clear()


def test_guard_survives_a_root_logger_reset_and_a_raised_level():
    from lib.logging_config import configure_logging

    root = logging.getLogger()
    handlers, level = root.handlers[:], root.level
    try:
        configure_logging()  # dictConfig replaces root's handlers
        root.setLevel(logging.ERROR)
        logging.getLogger("services.retrieval_service").warning("still seen")
    finally:
        root.handlers[:] = handlers
        root.setLevel(level)

    assert [r.getMessage() for r in conftest._app_log_records] == ["still seen"]
    conftest._app_log_records.clear()


def test_an_undeclared_app_warning_fails_the_test_and_names_it(pytester, expect_app_log):
    expect_app_log("prefetch failed: boom")
    pytester.makepyfile(
        INNER_IMPORTS
        + """
def test_swallowed_fake():
    logging.getLogger("services.retrieval_service").warning("prefetch failed: boom")
"""
    )

    result = pytester.runpytest_inprocess(*PYTESTER_ARGS)

    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*WARNING services.retrieval_service: prefetch failed: boom*"])
    result.stdout.fnmatch_lines(["*expect_app_log*"])


def test_requesting_caplog_does_not_opt_out_of_the_guard(pytester, expect_app_log):
    expect_app_log("asserted by hand")
    pytester.makepyfile(
        INNER_IMPORTS
        + """
def test_hand_assert(caplog):
    logging.getLogger("services.llm").warning("asserted by hand")
    assert "asserted by hand" in caplog.text
"""
    )

    result = pytester.runpytest_inprocess(*PYTESTER_ARGS)

    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*WARNING services.llm: asserted by hand*"])


def test_one_expectation_covers_every_matching_record(expect_app_log):
    expect_app_log("upload failed")

    logging.getLogger("services.ingestion").warning("upload failed: a.pdf")
    logging.getLogger("worker").error("upload failed: b.pdf")


def test_an_expectation_that_never_fired_fails_and_names_it(pytester):
    pytester.makepyfile(
        INNER_IMPORTS
        + """
def test_nothing_logged(expect_app_log):
    expect_app_log("never logged")
"""
    )

    result = pytester.runpytest_inprocess(*PYTESTER_ARGS)

    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*never fired*", "*never logged*"])


def test_only_the_undeclared_record_is_listed(pytester, expect_app_log):
    expect_app_log("declared one")
    expect_app_log("stray one")
    pytester.makepyfile(
        INNER_IMPORTS
        + """
def test_two_records(expect_app_log):
    expect_app_log("declared one")
    logging.getLogger("services.llm").warning("declared one")
    logging.getLogger("routes.chat").error("stray one")
"""
    )

    result = pytester.runpytest_inprocess(*PYTESTER_ARGS)

    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*ERROR routes.chat: stray one*"])
    result.stdout.no_fnmatch_line("*services.llm: declared one*")
    result.stdout.no_fnmatch_line("*never fired*")


def test_an_expectation_declared_by_a_fixture_covers_its_setup_record(pytester, expect_app_log):
    expect_app_log("seed failed")
    pytester.makepyfile(
        INNER_IMPORTS
        + """
@pytest.fixture
def failing_seed(expect_app_log):
    expect_app_log("seed failed")
    logging.getLogger("services.ingestion").warning("seed failed: no chunks")


def test_uses_the_fixture(failing_seed):
    pass
"""
    )

    result = pytester.runpytest_inprocess(*PYTESTER_ARGS)

    result.assert_outcomes(passed=1)


def test_logger_roots_cover_every_top_level_app_module():
    found = {p.stem for p in BACKEND.glob("*.py")} | {
        p.parent.name for p in BACKEND.glob("*/__init__.py")
    }

    assert found - NOT_APP == conftest._APP_LOGGER_ROOTS
