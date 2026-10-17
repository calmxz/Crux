"""#577: the conftest guard records every app log record at WARNING or above,
so a fake whose failure a best-effort path swallows and logs still fails its
test."""

import logging

from tests import conftest


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
