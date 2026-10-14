"""TDD: Subject/Lesson models and Session.subject_id are removed."""


def test_session_model_has_no_subject_id():
    import db.models as m

    assert not hasattr(m.Session, "subject_id")


def test_subject_lesson_models_removed():
    import db.models as m

    assert not hasattr(m, "Subject")
    assert not hasattr(m, "Lesson")
