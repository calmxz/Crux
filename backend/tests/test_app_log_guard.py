"""#577: the conftest guard fails a test that logs an app record at WARNING or
above without requesting caplog, so a fake whose failure a best-effort path
swallows and logs still fails its test."""

import logging
from pathlib import Path

from tests import conftest

BACKEND = Path(__file__).resolve().parent.parent
# Top-level code that is not the app: codegen output, one-off scripts, tests.
NOT_APP = {"contracts", "scripts", "tests"}


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


def test_requesting_caplog_opts_out_of_the_guard(caplog):
    logging.getLogger("services.llm").warning("expected")

    assert conftest._app_log_records == []
    assert "expected" in caplog.text


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


def test_an_unrequested_app_warning_fails_the_test_and_names_it(pytester, caplog):
    # caplog opts this outer test out: the inner run's record is its own.
    pytester.makepyfile(
        """
        import logging

        from tests.conftest import _no_unexpected_app_logs


        def test_swallowed_fake():
            logging.getLogger("services.retrieval_service").warning("prefetch failed: boom")
        """
    )

    result = pytester.runpytest_inprocess("-p", "no:cacheprovider", "-p", "no:asyncio")

    result.assert_outcomes(passed=1, errors=1)
    result.stdout.fnmatch_lines(["*WARNING services.retrieval_service: prefetch failed: boom*"])
    assert "prefetch failed: boom" in caplog.text


def test_logger_roots_cover_every_top_level_app_module():
    found = {p.stem for p in BACKEND.glob("*.py")} | {
        p.parent.name for p in BACKEND.glob("*/__init__.py")
    }

    assert found - NOT_APP == conftest._APP_LOGGER_ROOTS
