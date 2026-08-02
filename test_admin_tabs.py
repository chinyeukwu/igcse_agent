"""
Tests for the admin analytics + question-bank features (A + B1).

Exercises AdminService directly (same style as test_phase5.py):
- get_subject_mastery (heatmap)
- get_weak_topics
- PaperQuestion CRUD (list/create/update/delete)

Run: python test_admin_tabs.py
"""

import sys
import json
import random
import string
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from src.database import init_database, get_session
from src.database.models import QuizHistory, PaperQuestion
from src.admin import AdminService
from src.auth import UserService

passed = 0
failed = 0


def check(label, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"PASS - {label}")
    else:
        failed += 1
        print(f"FAIL - {label}")


def unique(prefix):
    return prefix + "".join(random.choices(string.ascii_lowercase, k=8))


def seed_quiz_data(db):
    """Create a student and a spread of quiz history across subjects/difficulties."""
    uname = unique("adminqa_")
    ok, err, user = UserService.register_user(
        db, username=uname, email=f"{uname}@example.com",
        password="TestPassword123", full_name="QA Student",
    )
    assert ok, err
    rows = [
        # subject, topic, difficulty, score
        ("Maths", "Algebra", "easy", 90.0),
        ("Maths", "Algebra", "hard", 55.0),   # weak
        ("Maths", "Trigonometry", "medium", 48.0),  # weak
        ("Science", "Photosynthesis", "easy", 82.0),
        ("Science", "Photosynthesis", "medium", 66.0),  # weak
    ]
    for subject, topic, difficulty, score in rows:
        db.add(QuizHistory(
            user_id=user.id, subject=subject, topic=topic, difficulty=difficulty,
            language_code="en", questions_json="[]", user_answers_json="[]",
            score=score, is_offline=False,
        ))
    db.commit()
    return user


def main():
    print("=" * 60)
    print("ADMIN TABS TESTS (A: analytics, B1: question bank)")
    print("=" * 60)

    init_database()
    db = get_session()

    seed_quiz_data(db)

    # ---- A: subject mastery ----
    ok, mastery, err = AdminService.get_subject_mastery(db)
    check("get_subject_mastery succeeds", ok)
    check("mastery includes Maths", "Maths" in mastery)
    if "Maths" in mastery:
        bd = mastery["Maths"]["by_difficulty"]
        check("Maths has easy+hard difficulty buckets", bd["easy"]["count"] >= 1 and bd["hard"]["count"] >= 1)
        check("Maths easy avg is 90", round(bd["easy"]["avg"]) == 90)
        check("Maths overall_avg present", "overall_avg" in mastery["Maths"])

    # ---- A: weak topics ----
    ok, weak, err = AdminService.get_weak_topics(db, threshold=70.0)
    check("get_weak_topics succeeds", ok)
    topics = {(w["subject"], w["topic"]) for w in weak}
    check("Trigonometry flagged weak", ("Maths", "Trigonometry") in topics)
    check("all weak topics below threshold", all(w["avg_score"] < 70 for w in weak))
    check("weak topics sorted ascending", weak == sorted(weak, key=lambda x: x["avg_score"]))
    if weak:
        check("weak topic has student count", weak[0]["students"] >= 1)

    # ---- B1: question CRUD ----
    ok, created, err = AdminService.create_paper_question(db, {
        "subject": "Maths", "question_text": "Solve 2x + 3 = 9.",
        "question_type": "calculation", "difficulty_level": "easy", "marks_total": 3,
    })
    check("create_paper_question succeeds", ok and created and created.get("id"))
    qid = created["id"] if created else None

    ok2, bad, err2 = AdminService.create_paper_question(db, {"subject": "Maths", "question_text": ""})
    check("create rejects empty question_text", (not ok2) and "question_text" in (err2 or ""))

    ok, listing, err = AdminService.list_paper_questions(db, subject="Maths")
    check("list_paper_questions succeeds", ok)
    check("created question appears in list", any(q["id"] == qid for q in listing))

    ok, updated, err = AdminService.update_paper_question(db, qid, {"marks_total": 5, "difficulty_level": "medium"})
    check("update_paper_question succeeds", ok and updated and updated["marks_total"] == 5)
    check("update changed difficulty", updated and updated["difficulty_level"] == "medium")

    ok, _upd_data, upd_err = AdminService.update_paper_question(db, 999999999, {"marks_total": 1})
    check("update missing question returns not found", (not ok) and upd_err == "Question not found")

    ok, del_err = AdminService.delete_paper_question(db, qid)
    check("delete_paper_question succeeds", ok)
    ok, listing2, err = AdminService.list_paper_questions(db, subject="Maths")
    check("deleted question gone from list", all(q["id"] != qid for q in listing2))

    ok, del_err2 = AdminService.delete_paper_question(db, qid)
    check("delete missing question returns not found", (not ok) and del_err2 == "Question not found")

    print("=" * 60)
    print(f"Result: {passed} passed, {failed} failed")
    print("=" * 60)
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
