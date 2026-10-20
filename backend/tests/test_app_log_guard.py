"""#577, #594: the conftest guard fails a test that logs an app record at
WARNING or above it did not declare with expect_app_log, so a fake whose
failure a best-effort path swallows and logs still fails its test. It also
fails a declared expectation that matched no record."""

import ast
import logging
from pathlib import Path

import pytest

from tests import conftest

BACKEND = Path(__file__).resolve().parent.parent
# Top-level code that is not the app: codegen output, one-off scripts, tests.
NOT_APP = {"contracts", "scripts", "tests"}
PYTESTER_ARGS = ("-p", "no:cacheprovider", "-p", "no:asyncio")
# A conftest is a plugin, so the guard's report hook registers there too.
INNER_CONFTEST = """
from tests.conftest import (
    _no_unexpected_app_logs,
    expect_app_log,
    pytest_runtest_makereport,
)
"""
INNER_HEADER = """
import logging

import pytest
"""


def _run_inner(pytester, source: str):
    """Run `source` as a test file under the guard. The inner run shares the
    outer test's loggers, so the outer guard sees its records too and the
    outer test declares them."""
    pytester.makeconftest(INNER_CONFTEST)
    pytester.makepyfile(INNER_HEADER + source)
    return pytester.runpytest_inprocess(*PYTESTER_ARGS)


def test_app_warnings_and_errors_are_recorded_third_party_and_info_are_not(
    _no_unexpected_app_logs,
):
    logging.getLogger("services.retrieval_service").error("query failed")
    logging.getLogger("main").warning("startup degraded")
    logging.getLogger("services.llm").info("settled")
    logging.getLogger("litellm").warning("third party")
    logging.getLogger("servicesx").warning("not an app package")

    records = _no_unexpected_app_logs.records
    assert [(r.name, r.getMessage()) for r in records] == [
        ("services.retrieval_service", "query failed"),
        ("main", "startup degraded"),
    ]
    # Cleared, so this test's own teardown check passes.
    records.clear()


def test_guard_survives_a_root_logger_reset_and_a_raised_level(_no_unexpected_app_logs):
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

    records = _no_unexpected_app_logs.records
    assert [r.getMessage() for r in records] == ["still seen"]
    records.clear()


def test_an_undeclared_app_warning_fails_the_test_and_names_it(pytester, expect_app_log):
    expect_app_log("prefetch failed: boom")

    result = _run_inner(
        pytester,
        """
def test_swallowed_fake():
    logging.getLogger("services.retrieval_service").warning("prefetch failed: boom")
""",
    )

    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*WARNING services.retrieval_service: prefetch failed: boom*"])
    result.stdout.fnmatch_lines(["*expect_app_log*"])


def test_requesting_caplog_does_not_opt_out_of_the_guard(pytester, expect_app_log):
    expect_app_log("asserted by hand")

    result = _run_inner(
        pytester,
        """
def test_hand_assert(caplog):
    logging.getLogger("services.llm").warning("asserted by hand")
    assert "asserted by hand" in caplog.text
""",
    )

    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*WARNING services.llm: asserted by hand*"])


def test_one_expectation_covers_every_matching_record(expect_app_log):
    expect_app_log("upload failed")

    logging.getLogger("services.ingestion").warning("upload failed: a.pdf")
    logging.getLogger("worker").error("upload failed: b.pdf")


@pytest.mark.parametrize("text", ["", "  "])
def test_a_blank_expectation_is_refused(expect_app_log, text):
    # "" is a substring of every message, so it would silence the guard.
    with pytest.raises(ValueError, match="blank"):
        expect_app_log(text)


def test_an_expectation_that_never_fired_fails_and_names_it(pytester):
    result = _run_inner(
        pytester,
        """
def test_nothing_logged(expect_app_log):
    expect_app_log("never logged")
""",
    )

    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*never fired*", "*never logged*"])


def test_a_failed_or_skipped_test_is_not_also_failed_for_an_unfired_expectation(pytester):
    result = _run_inner(
        pytester,
        """
def test_fails_first(expect_app_log):
    expect_app_log("never logged")
    assert False


def test_skips_first(expect_app_log):
    expect_app_log("never logged")
    pytest.skip("not here")
""",
    )

    result.assert_outcomes(failed=1, skipped=1)
    result.stdout.no_fnmatch_line("*never fired*")


def test_only_the_undeclared_record_is_listed(pytester, expect_app_log):
    expect_app_log("declared one")
    expect_app_log("stray one")

    result = _run_inner(
        pytester,
        """
def test_two_records(expect_app_log):
    expect_app_log("declared one")
    logging.getLogger("services.llm").warning("declared one")
    logging.getLogger("routes.chat").error("stray one")
""",
    )

    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*ERROR routes.chat: stray one*"])
    result.stdout.no_fnmatch_line("*services.llm: declared one*")
    result.stdout.no_fnmatch_line("*never fired*")


def test_an_expectation_declared_by_a_fixture_covers_its_setup_record(pytester, expect_app_log):
    expect_app_log("seed failed")

    result = _run_inner(
        pytester,
        """
@pytest.fixture
def failing_seed(expect_app_log):
    expect_app_log("seed failed")
    logging.getLogger("services.ingestion").warning("seed failed: no chunks")


def test_uses_the_fixture(failing_seed):
    pass
""",
    )

    result.assert_outcomes(passed=1)


def _blinding_level_calls(source: str) -> list[int]:
    """Lines of caplog.at_level / set_level calls that raise an app logger
    above WARNING: its warnings are then never logged, so the guard cannot
    see them. Root is fine; the guard pins the app's own loggers."""

    def level(node: ast.expr) -> object:
        # logging.ERROR, "ERROR" or 40
        value = node.attr if isinstance(node, ast.Attribute) else getattr(node, "value", None)
        return logging.getLevelName(value) if isinstance(value, str) else value

    lines = []
    for node in ast.walk(ast.parse(source)):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr in {"at_level", "set_level"}
            and node.args
        ):
            continue
        logger = node.args[1] if len(node.args) > 1 else None
        logger = next((k.value for k in node.keywords if k.arg == "logger"), logger)
        name = logger.value if isinstance(logger, ast.Constant) else None
        is_app = isinstance(name, str) and name.split(".")[0] in conftest._APP_LOGGER_ROOTS
        lvl = level(node.args[0])
        if is_app and isinstance(lvl, int) and lvl > logging.WARNING:
            lines.append(node.lineno)
    return sorted(lines)


def test_the_level_scan_flags_an_app_logger_raised_above_warning():
    source = """
with caplog.at_level(logging.ERROR, logger="services.llm"): pass
caplog.set_level("CRITICAL", "routes.chat")
with caplog.at_level(logging.WARNING, logger="services.llm"): pass
with caplog.at_level(logging.ERROR): pass
with caplog.at_level(logging.ERROR, logger="litellm"): pass
"""
    assert _blinding_level_calls(source) == [2, 3]


def test_no_test_raises_an_app_logger_above_warning():
    hits = [
        f"{path.relative_to(BACKEND)}:{line}"
        for path in sorted((BACKEND / "tests").rglob("*.py"))
        for line in _blinding_level_calls(path.read_text(encoding="utf-8"))
    ]

    assert hits == [], "raise caplog's level on an app logger to WARNING at most"


def test_logger_roots_cover_every_top_level_app_module():
    found = {p.stem for p in BACKEND.glob("*.py")} | {
        p.parent.name for p in BACKEND.glob("*/__init__.py")
    }

    assert found - NOT_APP == conftest._APP_LOGGER_ROOTS
