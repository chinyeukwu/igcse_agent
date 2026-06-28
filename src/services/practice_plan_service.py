"""
Practice Plan Service - Generates personalized study plans based on performance.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.orm import Session as DBSession

from src.database.models import QuizAttempt, StudentAnswer, StudentDifficultyProfile
from src.services.spaced_repetition_service import TopicPerformanceService

logger = logging.getLogger(__name__)


class PracticePlanService:
    """Generates personalized practice plans based on student performance."""

    # Topic to resource mapping
    TOPIC_RESOURCES = {
        # Maths
        "algebra": {
            "concepts": ["equations", "polynomials", "factoring", "inequalities"],
            "resources": ["Khan Academy: Algebra", "Pearson Textbook Ch. 3-5"],
            "estimated_hours": 2
        },
        "geometry": {
            "concepts": ["shapes", "angles", "areas", "proofs"],
            "resources": ["Khan Academy: Geometry", "GeoGebra interactive demos"],
            "estimated_hours": 2
        },
        "trigonometry": {
            "concepts": ["sine", "cosine", "tangent", "radians"],
            "resources": ["Khan Academy: Trigonometry", "Interactive trig calculator"],
            "estimated_hours": 3
        },

        # English
        "poetry": {
            "concepts": ["meter", "rhyme", "imagery", "symbolism"],
            "resources": ["Pearson English textbook", "BBC Bitesize Poetry"],
            "estimated_hours": 2
        },
        "prose": {
            "concepts": ["character", "plot", "theme", "narrative structure"],
            "resources": ["Novel analysis guides", "SparkNotes summaries"],
            "estimated_hours": 3
        },
        "language": {
            "concepts": ["grammar", "vocabulary", "syntax", "style"],
            "resources": ["Grammarly", "Oxford Dictionary"],
            "estimated_hours": 1.5
        },

        # Science
        "forces": {
            "concepts": ["Newton's laws", "acceleration", "momentum"],
            "resources": ["PhET simulations", "Khan Academy: Physics"],
            "estimated_hours": 2
        },
        "energy": {
            "concepts": ["kinetic energy", "potential energy", "conservation"],
            "resources": ["Khan Academy: Energy", "Lab demonstrations"],
            "estimated_hours": 2
        },
        "reactions": {
            "concepts": ["chemical reactions", "bonding", "equations"],
            "resources": ["Lab practicals", "ChemDoodle simulations"],
            "estimated_hours": 2.5
        },

        "general": {
            "concepts": ["core concepts"],
            "resources": ["Pearson textbook", "Khan Academy"],
            "estimated_hours": 1.5
        }
    }

    @staticmethod
    def generate_practice_plan(
        db: DBSession,
        user_id: int,
        subject: str,
        weeks_ahead: int = 4
    ) -> Dict[str, Any]:
        """
        Generate comprehensive practice plan for student.

        Args:
            db: Database session
            user_id: Student ID
            subject: Subject (Maths, English, Science, etc.)
            weeks_ahead: How many weeks to plan for

        Returns:
            Detailed practice plan with priorities and resources
        """
        # Get topic performance
        topic_perf = TopicPerformanceService.get_topic_performance(db, user_id, subject)

        # Get current difficulty level
        difficulty_profile = db.query(StudentDifficultyProfile).filter(
            StudentDifficultyProfile.user_id == user_id,
            StudentDifficultyProfile.subject == subject
        ).first()

        current_difficulty = difficulty_profile.current_difficulty if difficulty_profile else "medium"

        # Categorize topics by performance
        weak_topics = {}      # <70% accuracy
        developing_topics = {} # 70-85% accuracy
        strong_topics = {}     # >85% accuracy

        for topic, perf in topic_perf.items():
            if perf["accuracy"] < 70:
                weak_topics[topic] = perf
            elif perf["accuracy"] < 85:
                developing_topics[topic] = perf
            else:
                strong_topics[topic] = perf

        # Build practice plan
        plan = {
            "student_id": user_id,
            "subject": subject,
            "generated_date": datetime.utcnow().isoformat(),
            "plan_duration_weeks": weeks_ahead,
            "current_difficulty": current_difficulty,
            "overall_summary": {
                "weak_topics_count": len(weak_topics),
                "developing_topics_count": len(developing_topics),
                "strong_topics_count": len(strong_topics),
                "average_accuracy": sum(p["accuracy"] for p in topic_perf.values()) / len(topic_perf) if topic_perf else 0,
            },
            "priorities": [],
            "weekly_schedule": [],
            "resources": {},
        }

        # Build priority list
        priority_order = list(weak_topics.keys()) + list(developing_topics.keys())

        for idx, topic in enumerate(priority_order, 1):
            perf = weak_topics.get(topic) or developing_topics.get(topic)
            resource_info = PracticePlanService.TOPIC_RESOURCES.get(
                topic,
                PracticePlanService.TOPIC_RESOURCES["general"]
            )

            priority = {
                "rank": idx,
                "topic": topic,
                "accuracy": perf["accuracy"],
                "proficiency": perf["proficiency"],
                "urgency": "critical" if perf["accuracy"] < 50 else "high" if perf["accuracy"] < 70 else "medium",
                "estimated_study_hours": resource_info["estimated_hours"],
                "key_concepts": resource_info["concepts"][:3],  # Top 3 concepts
                "resources": resource_info["resources"],
            }
            plan["priorities"].append(priority)

        # Build weekly schedule
        topics_to_cover = list(weak_topics.keys()) + list(developing_topics.keys())
        topics_per_week = max(1, len(topics_to_cover) // weeks_ahead)

        for week_num in range(1, weeks_ahead + 1):
            week_start = datetime.utcnow() + timedelta(weeks=week_num - 1)
            week_end = week_start + timedelta(days=7)

            # Assign topics to this week
            start_idx = (week_num - 1) * topics_per_week
            end_idx = min(start_idx + topics_per_week, len(topics_to_cover))
            week_topics = topics_to_cover[start_idx:end_idx]

            # Calculate study time
            total_hours = sum(
                PracticePlanService.TOPIC_RESOURCES.get(t, PracticePlanService.TOPIC_RESOURCES["general"])["estimated_hours"]
                for t in week_topics
            )

            week_plan = {
                "week": week_num,
                "date_range": f"{week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}",
                "topics": week_topics,
                "total_study_hours": total_hours,
                "daily_target_minutes": int((total_hours * 60) / 7),
                "focus": "critical gaps" if week_num <= 2 else "consolidation",
                "target_outcome": f"Improve {', '.join(week_topics)} to 75%+",
            }
            plan["weekly_schedule"].append(week_plan)

        # Compile resources
        resources_set = set()
        for topic in topics_to_cover:
            resource_info = PracticePlanService.TOPIC_RESOURCES.get(
                topic,
                PracticePlanService.TOPIC_RESOURCES["general"]
            )
            for resource in resource_info["resources"]:
                resources_set.add(resource)

        plan["resources"] = {
            "recommended": list(resources_set),
            "total_unique_resources": len(resources_set),
        }

        logger.info(f"Generated practice plan for user {user_id} in {subject}: {len(weak_topics)} weak topics")
        return plan

    @staticmethod
    def get_immediate_actions(
        db: DBSession,
        user_id: int,
        subject: str
    ) -> List[Dict[str, Any]]:
        """
        Get immediate action items (things to do today/this week).

        Returns:
            Prioritized list of immediate actions
        """
        topic_perf = TopicPerformanceService.get_topic_performance(db, user_id, subject)
        actions = []

        for topic, perf in topic_perf.items():
            if perf["accuracy"] < 70:
                action = {
                    "action": f"Review {topic}",
                    "urgency": "critical" if perf["accuracy"] < 50 else "high",
                    "reason": f"Accuracy: {perf['accuracy']:.0f}% (target: 75%)",
                    "suggested_activity": f"Take a {topic} quiz at difficulty: easy to medium",
                    "time_estimate": "15-20 minutes",
                    "resources": PracticePlanService.TOPIC_RESOURCES.get(
                        topic,
                        PracticePlanService.TOPIC_RESOURCES["general"]
                    )["resources"][:2],
                }
                actions.append(action)

        # Sort by urgency
        urgency_order = {"critical": 0, "high": 1, "medium": 2}
        actions.sort(key=lambda x: urgency_order.get(x["urgency"], 999))

        return actions[:5]  # Top 5 immediate actions

    @staticmethod
    def estimate_time_to_proficiency(
        current_accuracy: float,
        target_accuracy: float = 85.0,
        hours_per_week: float = 5.0
    ) -> Dict[str, Any]:
        """
        Estimate how long it will take to reach target proficiency.

        Args:
            current_accuracy: Current accuracy percentage
            target_accuracy: Target accuracy percentage
            hours_per_week: Hours available per week for study

        Returns:
            Time estimate and milestone breakdown
        """
        # Assume improvement follows diminishing returns
        # Each 10% improvement requires more effort

        if current_accuracy >= target_accuracy:
            return {
                "weeks_required": 0,
                "message": "Target proficiency already reached!",
                "milestones": []
            }

        gap = target_accuracy - current_accuracy
        improvement_rates = {
            # 0-25%: slow
            "0-25": {"accuracy_per_hour": 0.5, "multiplier": 3},
            # 25-50%: moderate
            "25-50": {"accuracy_per_hour": 1.0, "multiplier": 2},
            # 50-75%: good
            "50-75": {"accuracy_per_hour": 1.5, "multiplier": 1},
            # 75-85%: slower
            "75-85": {"accuracy_per_hour": 0.7, "multiplier": 1},
            # 85+: very slow
            "85+": {"accuracy_per_hour": 0.3, "multiplier": 1},
        }

        hours_needed = 0
        current = current_accuracy
        milestones = []

        while current < target_accuracy:
            # Determine current improvement rate
            if current < 25:
                rate_key = "0-25"
            elif current < 50:
                rate_key = "25-50"
            elif current < 75:
                rate_key = "50-75"
            elif current < 85:
                rate_key = "75-85"
            else:
                rate_key = "85+"

            rate_info = improvement_rates[rate_key]
            hours_to_next_milestone = 5 / (rate_info["accuracy_per_hour"] * rate_info["multiplier"])

            if current + 5 <= target_accuracy:
                current += 5
                hours_needed += hours_to_next_milestone
                milestones.append({
                    "accuracy": round(current, 1),
                    "hours_to_reach": round(hours_to_next_milestone, 1),
                    "weeks_at_rate": round(hours_to_next_milestone / hours_per_week, 1)
                })
            else:
                # Final push to target
                remaining = target_accuracy - current
                hours_to_target = remaining / rate_info["accuracy_per_hour"]
                hours_needed += hours_to_target
                current = target_accuracy
                milestones.append({
                    "accuracy": round(current, 1),
                    "hours_to_reach": round(hours_to_target, 1),
                    "weeks_at_rate": round(hours_to_target / hours_per_week, 1)
                })

        weeks_required = hours_needed / hours_per_week

        return {
            "weeks_required": round(weeks_required, 1),
            "total_hours_needed": round(hours_needed, 1),
            "hours_per_week": hours_per_week,
            "milestones": milestones,
            "message": f"Estimated {weeks_required:.1f} weeks at {hours_per_week} hours/week"
        }
