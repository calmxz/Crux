import pytest
from pydantic import ValidationError

from contracts import (
    AskCheckQuestionsArgs,
    ChatRequest,
    CheckAnswerRequest,
    CheckAnswerResponse,
    CheckSkipRequest,
    CheckSkipResponse,
    Citation,
    HealthResponse,
    PendingCheck,
    ProfileResponse,
    RetrieveChunksArgs,
    SessionCreateRequest,
    ToolResult,
    TopicProfile,
    UpdateTopicProfileArgs,
)


def test_topic_profile_defaults():
    p = TopicProfile()
    dump = p.model_dump()
    assert dump["knowledge_level"] is None
    assert dump["confirmed_gaps"] == []
    assert dump["mastered_concepts"] == []
    assert dump["focus_target_gap"] is None
    assert dump["last_session_summary"] is None


def test_topic_profile_round_trip_json():
    raw = '{"knowledge_level":"intermediate","confirmed_gaps":[{"name":"g1"}],"mastered_concepts":[],"focus_target_gap":"g1","last_session_summary":null}'
    p = TopicProfile.model_validate_json(raw)
    assert p.knowledge_level == "intermediate"
    assert p.focus_target_gap == "g1"
    assert "g1" in p.model_dump_json()


def test_update_topic_profile_args_minimal_ok():
    args = UpdateTopicProfileArgs(session_id="s1", evidence_type="declared")
    assert args.session_id == "s1"
    assert args.evidence_type == "declared"
    assert args.focus_clear_reason is None


def test_update_topic_profile_args_evidence_type_optional():
    # evidence_type is now optional (required only when add_mastered_concept present
    # — enforced at the service layer, not the schema layer)
    args = UpdateTopicProfileArgs(session_id="s1")
    assert args.session_id == "s1"
    assert args.evidence_type is None


def test_update_topic_profile_args_invalid_focus_clear_reason_rejected():
    with pytest.raises(ValidationError):
        UpdateTopicProfileArgs(
            session_id="s1",
            evidence_type="declared",
            focus_clear_reason="bogus",
        )


def test_update_topic_profile_args_invalid_evidence_type_rejected():
    with pytest.raises(ValidationError):
        UpdateTopicProfileArgs(session_id="s1", evidence_type="guessed")


def test_update_topic_profile_args_extra_fields_rejected():
    with pytest.raises(ValidationError):
        UpdateTopicProfileArgs(
            session_id="s1", evidence_type="declared", surprise="x"
        )


def test_retrieve_chunks_default_k():
    args = RetrieveChunksArgs(session_id="s1", query="what is X")
    assert args.k == 5


def test_retrieve_chunks_k_bounds():
    with pytest.raises(ValidationError):
        RetrieveChunksArgs(session_id="s1", query="q", k=0)
    with pytest.raises(ValidationError):
        RetrieveChunksArgs(session_id="s1", query="q", k=21)


def _one_item():
    return {
        "question": "What nets per glucose?",
        "options": ["2 ATP", "36 ATP"],
        "correct_index": 0,
        "explanation": "Net 2 ATP.",
    }


_ONE_SET = {"set_index": 1, "set_total": 1}


def test_ask_check_questions_args_required_fields():
    args = AskCheckQuestionsArgs(session_id="s1", gap="atp", items=[_one_item()], **_ONE_SET)
    assert args.gap == "atp"
    assert len(args.items) == 1
    assert (args.set_index, args.set_total) == (1, 1)


@pytest.mark.parametrize("missing", ["set_index", "set_total"])
def test_ask_check_questions_args_set_fields_required(missing):
    fields = {k: v for k, v in _ONE_SET.items() if k != missing}
    with pytest.raises(ValidationError):
        AskCheckQuestionsArgs(session_id="s1", gap="atp", items=[_one_item()], **fields)


@pytest.mark.parametrize("field,value", [
    ("set_index", 0), ("set_index", 4), ("set_total", 0), ("set_total", 4),
])
def test_ask_check_questions_args_set_fields_range(field, value):
    with pytest.raises(ValidationError):
        AskCheckQuestionsArgs(
            session_id="s1", gap="atp", items=[_one_item()], **{**_ONE_SET, field: value}
        )


def test_ask_check_questions_args_rejects_empty_items():
    with pytest.raises(ValidationError):
        AskCheckQuestionsArgs(session_id="s1", gap="atp", items=[], **_ONE_SET)


def test_ask_check_questions_args_rejects_over_five_items():
    with pytest.raises(ValidationError):
        AskCheckQuestionsArgs(session_id="s1", gap="atp", items=[_one_item()] * 6, **_ONE_SET)


def test_ask_check_questions_args_extra_fields_rejected():
    with pytest.raises(ValidationError):
        AskCheckQuestionsArgs(
            session_id="s1", gap="g", items=[_one_item()], surprise="x", **_ONE_SET
        )


def _one_pending_item():
    return {
        "question": "What is the base case?",
        "options": ["A", "B"],
        "status": "pending",
    }


def test_pending_check_required_fields():
    pc = PendingCheck(
        gap="recursion",
        current_index=0,
        total=1,
        items=[_one_pending_item()],
    )
    assert pc.gap == "recursion"
    assert pc.current_index == 0
    assert pc.total == 1
    assert len(pc.items) == 1


def test_pending_check_missing_fields_rejected():
    with pytest.raises(ValidationError):
        PendingCheck(gap="recursion", current_index=0, total=1)  # missing items
    with pytest.raises(ValidationError):
        PendingCheck(current_index=0, total=1, items=[_one_pending_item()])  # missing gap


def test_tool_result_minimal():
    r = ToolResult(ok=True, status="ok")
    assert r.error is None
    assert r.data is None


def test_tool_result_status_enum():
    with pytest.raises(ValidationError):
        ToolResult(ok=False, status="weird")


def test_chat_request_required_fields():
    with pytest.raises(ValidationError):
        ChatRequest(session_id="s")  # missing message


def test_chat_request_has_review_gaps_default_false():
    req = ChatRequest(session_id="s1", message="hi")
    assert req.review_gaps is False
    req2 = ChatRequest(session_id="s1", message="hi", review_gaps=True)
    assert req2.review_gaps is True


def test_chat_request_accepts_review_gap():
    req = ChatRequest(session_id="s1", message="hi", review_gaps=True, review_gap="derivatives")
    assert req.review_gap == "derivatives"


def test_chat_request_review_gap_defaults_none():
    req = ChatRequest(session_id="s1", message="hi")
    assert req.review_gap is None


def test_session_create_request_seed_mode_enum():
    SessionCreateRequest(topic="t", seed_mode="fresh")
    SessionCreateRequest(topic="t", seed_mode="resume")
    with pytest.raises(ValidationError):
        SessionCreateRequest(topic="t", seed_mode="continue")


def test_profile_response_shape():
    pr = ProfileResponse(profile=TopicProfile(), recent_learning_events=[], etag="abc123")
    assert pr.profile.knowledge_level is None
    assert pr.recent_learning_events == []


def test_health_response():
    assert HealthResponse(status="ok").status == "ok"


def test_citation_minimal_two_arg():
    c = Citation(doc_id="d", text="t")
    assert c.doc_id == "d"
    assert c.text == "t"
    assert c.page is None
    assert c.doc_name is None


def test_citation_full_fields_round_trip():
    c = Citation(doc_id="d", text="t", page=42, doc_name="Algorithms Ch3")
    dump = c.model_dump()
    assert dump["doc_id"] == "d"
    assert dump["text"] == "t"
    assert dump["page"] == 42
    assert dump["doc_name"] == "Algorithms Ch3"


def test_citation_null_page_and_doc_name_in_dump():
    dump = Citation(doc_id="x", text="y").model_dump()
    assert "page" in dump
    assert "doc_name" in dump
    assert dump["page"] is None
    assert dump["doc_name"] is None


def test_citation_extra_fields_rejected():
    with pytest.raises(ValidationError):
        Citation(doc_id="d", text="t", surprise="x")


def test_check_answer_request_required_fields():
    req = CheckAnswerRequest(index=0, selected_index=2)
    assert req.index == 0
    assert req.selected_index == 2


def test_check_answer_request_missing_field_rejected():
    with pytest.raises(ValidationError):
        CheckAnswerRequest()
    with pytest.raises(ValidationError):
        CheckAnswerRequest(selected_index=2)  # missing index


def test_check_answer_request_extra_fields_rejected():
    with pytest.raises(ValidationError):
        CheckAnswerRequest(index=0, selected_index=0, surprise="x")


def test_check_answer_response_required_fields():
    resp = CheckAnswerResponse(
        correct=True,
        explanation="Option A is the base case.",
        correct_index=0,
        current_index=0,
        total=2,
        has_next=True,
        done=False,
    )
    assert resp.correct is True
    assert resp.explanation == "Option A is the base case."
    assert resp.correct_index == 0
    assert resp.has_next is True
    assert resp.done is False


def test_check_answer_response_missing_field_rejected():
    with pytest.raises(ValidationError):
        CheckAnswerResponse(correct=True, explanation="ok", correct_index=0)  # missing current_index/total/has_next/done


def test_check_answer_response_extra_fields_rejected():
    with pytest.raises(ValidationError):
        CheckAnswerResponse(
            correct=False, explanation="no", correct_index=1,
            current_index=0, total=1, has_next=False, done=True,
            surprise="x",
        )


def test_check_skip_request_required_fields():
    req = CheckSkipRequest(index=1)
    assert req.index == 1


def test_check_skip_request_missing_field_rejected():
    with pytest.raises(ValidationError):
        CheckSkipRequest()


def test_check_skip_response_required_fields():
    resp = CheckSkipResponse(current_index=1, total=3, has_next=True, done=False)
    assert resp.current_index == 1
    assert resp.has_next is True


def test_check_skip_response_missing_field_rejected():
    with pytest.raises(ValidationError):
        CheckSkipResponse(current_index=1, total=3)  # missing has_next, done


def test_array_fields_accept_none_quirk():
    """Codegen quirk: OpenAPI `default: []` produces `list[T] | None = []`.

    Pinned so any change is intentional. Phase 2+ consumers must treat
    these as possibly-None or normalize at the boundary.
    """
    p = TopicProfile(confirmed_gaps=None, mastered_concepts=None)
    assert p.confirmed_gaps is None
    assert p.mastered_concepts is None


def test_review_queue_contracts_exist():
    from contracts import ReviewQueueItem, ReviewQueuePage

    item = ReviewQueueItem(
        concept="photosynthesis",
        source_session_id="s1",
        source_topic="biology",
        last_tested_at="2026-07-01T00:00:00Z",
        streak=2,
        due_at="2026-07-03T00:00:00Z",
    )
    page = ReviewQueuePage(items=[item], total=1, limit=20, offset=0)
    assert page.items[0].concept == "photosynthesis"
    assert page.items[0].streak == 2
    assert page.total == 1


def test_concept_entry_defaults():
    from contracts import ConceptEntry

    e = ConceptEntry(name="limits")
    assert e.name == "limits"
    assert e.evidence_type is None
    assert e.last_event_at is None


def test_concept_entry_rejects_inferred():
    import pytest
    from pydantic import ValidationError

    from contracts import ConceptEntry

    with pytest.raises(ValidationError):
        ConceptEntry(name="limits", evidence_type="inferred")


def test_topic_profile_new_shape():
    from contracts import ConceptEntry, TopicProfile

    p = TopicProfile()
    assert p.subtopic_levels == {}
    p2 = TopicProfile(
        mastered_concepts=[{"name": "limits", "evidence_type": "tested"}],
        subtopic_levels={"integration by parts": "beginner"},
    )
    assert isinstance(p2.mastered_concepts[0], ConceptEntry)
    assert p2.subtopic_levels["integration by parts"] == "beginner"


def test_update_args_subtopic_fields():
    from contracts import UpdateTopicProfileArgs

    a = UpdateTopicProfileArgs(
        session_id="s1", subtopic="chain rule", subtopic_level="intermediate"
    )
    assert a.subtopic == "chain rule"
    assert a.subtopic_level == "intermediate"


def test_profile_patch_request_subtopic_fields():
    from contracts import ProfilePatchRequest

    b = ProfilePatchRequest(subtopic="chain rule", subtopic_level="advanced")
    assert b.subtopic == "chain rule"
    assert b.subtopic_level == "advanced"


# I-02: ErrorResponse.detail must accept BOTH shapes the backend actually
# sends -- a bare string (plain FastAPI/validation errors) and a coded
# object with code-specific extras (caps, session_ended, duplicate_topic,
# upload errors).
def test_error_response_detail_accepts_string():
    from contracts import ErrorResponse

    e = ErrorResponse.model_validate({"detail": "not found"})
    assert e.detail == "not found"


def test_error_response_detail_accepts_coded_object_with_extras():
    from contracts import CodedErrorDetail, ErrorResponse

    e = ErrorResponse.model_validate({
        "detail": {
            "code": "daily_cost_cap_reached",
            "soft_cap_usd": "2.00",
            "hard_cap_usd": "3.00",
            "used_usd": "3.01",
            "resets_at": "2026-01-02T00:00:00Z",
        }
    })
    assert isinstance(e.detail, CodedErrorDetail)
    assert e.detail.code == "daily_cost_cap_reached"
    d = e.detail.model_dump()
    assert d["soft_cap_usd"] == "2.00"


def test_error_response_detail_object_requires_code():
    from contracts import ErrorResponse

    with pytest.raises(ValidationError):
        ErrorResponse.model_validate({"detail": {"session_id": "abc"}})
