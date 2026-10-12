def test_contracts_drop_subject_symbols():
    import contracts

    for name in [
        "SubjectCreateRequest",
        "SubjectDetail",
        "SubjectListItem",
        "SubjectProfileResponse",
        "SubjectLessonRollup",
        "LessonItem",
        "LessonCreateRequest",
        "LessonUpdateRequest",
        "LessonDraft",
        "AddLessonSuggestion",
    ]:
        assert not hasattr(contracts, name), name


def test_session_response_has_no_subject_id():
    import contracts

    assert "subject_id" not in contracts.SessionResponse.model_fields


def test_check_answer_response_has_no_suggestion():
    import contracts

    assert "add_lesson_suggestion" not in contracts.CheckAnswerResponse.model_fields
