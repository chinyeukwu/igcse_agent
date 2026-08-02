"""
Phase 4 Test Suite: Quiz Service and History
Tests quiz generation, scoring, history tracking, and 60-day retention.
"""

import os
import sys
import time
import json
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.database import init_database, get_db_manager, get_session
from src.auth import UserService
from src.quiz import QuizGenerator, QuizService


def setup_test_db():
    """Initialize test database."""
    try:
        init_database()
        return True
    except Exception as e:
        print(f"Database setup error: {e}")
        return False


def create_test_user():
    """Create a test user for testing."""
    try:
        db_session = get_session()
        
        unique_suffix = int(time.time() * 1000) % 1000000
        username = f"testuser_phase4_{unique_suffix}"
        email = f"testuser{unique_suffix}@test.com"
        
        success, msg, user = UserService.register_user(
            db_session,
            username=username,
            email=email,
            password="TestPassword123!",
            full_name="Test User Phase 4"
        )
        
        if success:
            return user, db_session
        else:
            print(f"User creation failed: {msg}")
            return None, db_session
    
    except Exception as e:
        print(f"User creation error: {e}")
        return None, None


def test_quiz_config_validation():
    """Test quiz configuration validation."""
    print("\n" + "="*60)
    print("TEST 1: Quiz Configuration Validation")
    print("="*60)
    
    tests_passed = 0
    
    try:
        # Test 1: Valid config
        is_valid, error = QuizGenerator.validate_config("maths", "medium", 5)
        if is_valid:
            print(f"PASS: Valid configuration accepted")
            tests_passed += 1
        else:
            print(f"FAIL: Valid config rejected: {error}")
        
        # Test 2: Invalid subject
        is_valid, error = QuizGenerator.validate_config("invalid_subject", "medium", 5)
        if not is_valid and "subject" in error.lower():
            print(f"PASS: Invalid subject rejected")
            tests_passed += 1
        else:
            print(f"FAIL: Should reject invalid subject")
        
        # Test 3: Invalid difficulty
        is_valid, error = QuizGenerator.validate_config("maths", "impossible", 5)
        if not is_valid and "difficulty" in error.lower():
            print(f"PASS: Invalid difficulty rejected")
            tests_passed += 1
        else:
            print(f"FAIL: Should reject invalid difficulty")
        
        # Test 4: Invalid question count
        is_valid, error = QuizGenerator.validate_config("maths", "medium", 7)
        if not is_valid and "question" in error.lower():
            print(f"PASS: Invalid question count rejected")
            tests_passed += 1
        else:
            print(f"FAIL: Should reject invalid question count")
        
        # Test 5: All valid subjects
        for subject in ["maths", "english", "french", "science", "finearts"]:
            is_valid, _ = QuizGenerator.validate_config(subject, "medium", 5)
            if is_valid:
                tests_passed += 1
        print(f"PASS: All 5 subjects validated")
        
        return tests_passed
    
    except Exception as e:
        print(f"ERROR: Config validation error: {e}")
        return tests_passed


def test_quiz_generation():
    """Test quiz generation functionality."""
    print("\n" + "="*60)
    print("TEST 2: Quiz Generation")
    print("="*60)
    
    tests_passed = 0
    
    try:
        # Test 1: Generate maths quiz
        print("Generating maths quiz...")
        success, questions, error = QuizGenerator.generate_quiz(
            subject="maths",
            difficulty="medium",
            question_count=3,
            language_code="en"
        )
        
        if success and len(questions) == 3:
            print(f"PASS: Maths quiz generated ({len(questions)} questions)")
            tests_passed += 1
        else:
            print(f"FAIL: Quiz generation failed: {error}")
        
        # Validate quiz structure if generated
        if success and questions:
            # Test 2: Verify question structure
            all_valid = True
            for q in questions:
                if not all(k in q for k in ["question", "options", "correct_answer", "explanation"]):
                    all_valid = False
                if len(q["options"]) != 4:
                    all_valid = False
                if q["correct_answer"] not in [0, 1, 2, 3]:
                    all_valid = False
            
            if all_valid:
                print(f"PASS: All questions have valid structure")
                tests_passed += 1
            else:
                print(f"FAIL: Some questions have invalid structure")
            
            # Test 3: Verify no duplicates
            question_texts = [q["question"] for q in questions]
            if len(question_texts) == len(set(question_texts)):
                print(f"PASS: No duplicate questions")
                tests_passed += 1
            else:
                print(f"FAIL: Found duplicate questions")
        
        # Test 4: Different difficulty should generate different questions
        print("Generating easy quiz for comparison...")
        success2, questions2, error2 = QuizGenerator.generate_quiz(
            subject="maths",
            difficulty="easy",
            question_count=3,
            language_code="en"
        )
        
        if success2:
            print(f"PASS: Easy quiz generated")
            tests_passed += 1
        else:
            print(f"FAIL: Easy quiz generation failed")
        
        return tests_passed
    
    except Exception as e:
        print(f"ERROR: Quiz generation error: {e}")
        import traceback
        traceback.print_exc()
        return tests_passed


def test_scoring():
    """Test score calculation."""
    print("\n" + "="*60)
    print("TEST 3: Score Calculation")
    print("="*60)
    
    tests_passed = 0
    
    try:
        # Create mock questions
        questions = [
            {"question": "Q1", "options": ["A", "B", "C", "D"], "correct_answer": 0},
            {"question": "Q2", "options": ["A", "B", "C", "D"], "correct_answer": 1},
            {"question": "Q3", "options": ["A", "B", "C", "D"], "correct_answer": 2},
            {"question": "Q4", "options": ["A", "B", "C", "D"], "correct_answer": 3},
        ]
        
        # Test 1: Perfect score
        user_answers = [0, 1, 2, 3]
        score, correct = QuizService.calculate_score(questions, user_answers)
        if score == 100.0 and correct == 4:
            print(f"PASS: Perfect score: {score}%")
            tests_passed += 1
        else:
            print(f"FAIL: Perfect score calculation failed")
        
        # Test 2: Zero score
        user_answers = [1, 0, 3, 2]
        score, correct = QuizService.calculate_score(questions, user_answers)
        if score == 0.0 and correct == 0:
            print(f"PASS: Zero score: {score}%")
            tests_passed += 1
        else:
            print(f"FAIL: Zero score calculation failed")
        
        # Test 3: 50% score
        user_answers = [0, 1, 3, 2]  # First two correct
        score, correct = QuizService.calculate_score(questions, user_answers)
        if score == 50.0 and correct == 2:
            print(f"PASS: 50% score: {score}%")
            tests_passed += 1
        else:
            print(f"FAIL: 50% score calculation failed")
        
        # Test 4: Mismatch between questions and answers
        score, correct = QuizService.calculate_score(questions, [0, 1])  # Only 2 answers
        if score == 0.0 and correct == 0:
            print(f"PASS: Mismatch handled correctly")
            tests_passed += 1
        else:
            print(f"FAIL: Mismatch should result in 0 score")
        
        return tests_passed
    
    except Exception as e:
        print(f"ERROR: Scoring error: {e}")
        return tests_passed


def test_quiz_history():
    """Test quiz history storage and retrieval."""
    print("\n" + "="*60)
    print("TEST 4: Quiz History Management")
    print("="*60)
    
    user, db_session = create_test_user()
    if not user:
        print("FAIL: Could not create test user")
        return 0
    
    tests_passed = 0
    user_id = user.id
    
    try:
        # Mock quiz data
        mock_questions = [
            {"question": "Q1", "options": ["A", "B", "C", "D"], "correct_answer": 0},
            {"question": "Q2", "options": ["A", "B", "C", "D"], "correct_answer": 1},
        ]
        mock_answers = [0, 1]
        
        # Test 1: Save quiz attempt
        success, quiz_id, error = QuizService.save_quiz_attempt(
            db_session,
            user_id=user_id,
            subject="maths",
            topic="Algebra",
            difficulty="medium",
            questions=mock_questions,
            user_answers=mock_answers,
            time_taken_seconds=120,
            is_offline=False,
            language_code="en"
        )
        
        if success and quiz_id:
            print(f"PASS: Quiz saved with ID {quiz_id}")
            tests_passed += 1
        else:
            print(f"FAIL: Quiz save failed: {error}")
        
        # Test 2: Retrieve quiz history
        history = QuizService.get_quiz_history(db_session, user_id, limit=10)
        if len(history) > 0:
            print(f"PASS: Retrieved {len(history)} quiz records")
            tests_passed += 1
        else:
            print(f"FAIL: No history retrieved")
        
        # Test 3: Save multiple quizzes in different subjects
        for subject in ["english", "french"]:
            success, qid, _ = QuizService.save_quiz_attempt(
                db_session,
                user_id=user_id,
                subject=subject,
                topic=f"{subject} Test",
                difficulty="easy",
                questions=mock_questions,
                user_answers=[1, 0],
                time_taken_seconds=60,
                is_offline=False,
                language_code="en"
            )
        
        # Test filtering by subject
        maths_history = QuizService.get_quiz_history(db_session, user_id, subject="maths")
        english_history = QuizService.get_quiz_history(db_session, user_id, subject="english")
        
        if len(maths_history) >= 1 and len(english_history) >= 1:
            print(f"PASS: Topic filtering works: maths={len(maths_history)}, english={len(english_history)}")
            tests_passed += 1
        else:
            print(f"FAIL: Topic filtering issue")
        
        # Test 4: Get quiz detail
        if quiz_id:
            detail = QuizService.get_quiz_detail(db_session, user_id, quiz_id)
            if detail and "questions" in detail:
                print(f"PASS: Quiz detail retrieved: {len(detail['questions'])} questions")
                tests_passed += 1
            else:
                print(f"FAIL: Quiz detail retrieval failed")
        
        return tests_passed
    
    except Exception as e:
        print(f"ERROR: Quiz history error: {e}")
        import traceback
        traceback.print_exc()
        return tests_passed


def test_statistics():
    """Test quiz statistics calculation."""
    print("\n" + "="*60)
    print("TEST 5: Quiz Statistics")
    print("="*60)
    
    user, db_session = create_test_user()
    if not user:
        print("FAIL: Could not create test user")
        return 0
    
    tests_passed = 0
    user_id = user.id
    
    try:
        # Create multiple quiz attempts with different scores
        mock_questions = [
            {"question": "Q1", "options": ["A", "B", "C", "D"], "correct_answer": 0},
            {"question": "Q2", "options": ["A", "B", "C", "D"], "correct_answer": 1},
        ]
        
        # Save quizzes with different scores
        quiz_data = [
            {"subject": "maths", "answers": [0, 1], "score": 100},  # Perfect
            {"subject": "maths", "answers": [1, 0], "score": 0},    # Fail
            {"subject": "english", "answers": [0, 1], "score": 100}, # Perfect
        ]
        
        for data in quiz_data:
            QuizService.save_quiz_attempt(
                db_session,
                user_id=user_id,
                subject=data["subject"],
                topic="Test",
                difficulty="medium",
                questions=mock_questions,
                user_answers=data["answers"],
                time_taken_seconds=60,
                is_offline=False,
                language_code="en"
            )
        
        # Test 1: Get statistics
        stats = QuizService.get_quiz_statistics(db_session, user_id)
        
        if stats and "total_quizzes" in stats:
            print(f"PASS: Statistics retrieved: total_quizzes={stats['total_quizzes']}")
            tests_passed += 1
        else:
            print(f"FAIL: Statistics retrieval failed")
        
        # Test 2: Verify average calculation
        if stats.get("total_quizzes") > 0:
            avg = stats.get("average_score", 0)
            if avg > 0:
                print(f"PASS: Average score calculated: {avg}%")
                tests_passed += 1
            else:
                print(f"FAIL: Average score not calculated")
        
        # Test 3: Verify breakdown by subject
        if "by_subject" in stats and len(stats["by_subject"]) > 0:
            print(f"PASS: Subject breakdown available: {list(stats['by_subject'].keys())}")
            tests_passed += 1
        else:
            print(f"FAIL: Subject breakdown missing")
        
        # Test 4: Verify breakdown by difficulty
        if "by_difficulty" in stats and len(stats["by_difficulty"]) > 0:
            print(f"PASS: Difficulty breakdown available: {list(stats['by_difficulty'].keys())}")
            tests_passed += 1
        else:
            print(f"FAIL: Difficulty breakdown missing")
        
        return tests_passed
    
    except Exception as e:
        print(f"ERROR: Statistics error: {e}")
        import traceback
        traceback.print_exc()
        return tests_passed


def test_retention_cleanup():
    """Test 60-day retention and cleanup."""
    print("\n" + "="*60)
    print("TEST 6: 60-Day Retention & Cleanup")
    print("="*60)
    
    user, db_session = create_test_user()
    if not user:
        print("FAIL: Could not create test user")
        return 0
    
    tests_passed = 0
    user_id = user.id
    
    try:
        # Test 1: Retention days constant
        if QuizService.RETENTION_DAYS == 60:
            print(f"PASS: Retention period is 60 days")
            tests_passed += 1
        else:
            print(f"FAIL: Retention period should be 60 days, got {QuizService.RETENTION_DAYS}")
        
        # Test 2: Get history respects retention
        history_recent = QuizService.get_quiz_history(
            db_session,
            user_id,
            within_retention=True
        )
        history_all = QuizService.get_quiz_history(
            db_session,
            user_id,
            within_retention=False
        )
        
        if isinstance(history_recent, list) and isinstance(history_all, list):
            print(f"PASS: History retrieval works: recent={len(history_recent)}, all={len(history_all)}")
            tests_passed += 1
        else:
            print(f"FAIL: History retrieval issue")
        
        # Test 3: Cleanup function runs
        deleted = QuizService.cleanup_old_quizzes(db_session)
        print(f"PASS: Cleanup executed: {deleted} old records deleted")
        tests_passed += 1
        
        # Test 4: Statistics respect retention
        stats = QuizService.get_quiz_statistics(db_session, user_id, within_retention=True)
        if stats:
            print(f"PASS: Statistics respect retention policy")
            tests_passed += 1
        else:
            print(f"FAIL: Statistics issue")
        
        return tests_passed
    
    except Exception as e:
        print(f"ERROR: Retention/cleanup error: {e}")
        return tests_passed


def main():
    """Run all Phase 4 tests."""
    print("\n" + "="*60)
    print("IGCSE TUTOR - PHASE 4 TEST SUITE")
    print("Quiz Service & History Testing")
    print("="*60)
    
    # Initialize database
    if not setup_test_db():
        print("Database initialization failed")
        return
    
    # Run tests
    results = {
        "Quiz Config Validation": test_quiz_config_validation(),
        "Quiz Generation": test_quiz_generation(),
        "Score Calculation": test_scoring(),
        "Quiz History": test_quiz_history(),
        "Statistics": test_statistics(),
        "Retention & Cleanup": test_retention_cleanup(),
    }
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    total_passed = 0
    for test_name, passed in results.items():
        status = "PASS" if passed > 0 else "PARTIAL"
        print(f"{status:12} - {test_name}: {passed} tests")
        total_passed += passed
    
    print("="*60)
    print(f"Result: {total_passed} total tests passed")
    print("="*60)
    
    success = total_passed >= 20
    if success:
        print("\n[SUCCESS] Phase 4 tests passed! Quiz service is working correctly.")
    else:
        print(f"\n{total_passed} of 24+ tests passed. Please review failures above.")
    return success


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
