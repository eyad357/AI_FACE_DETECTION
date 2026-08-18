"""
Guide content — structured, static educational text for the AI
University Lab Guide Robot.

This module contains ONLY content data. It has no application logic
and no knowledge of Vision, Robot, Decision behavior, or UI. Content is
keyed by the EXISTING GuideTopic enum
(app.decision.event_manager.GuideTopic) so Guide reuses the single
canonical topic vocabulary rather than defining a second one.

Content is intentionally generic and credible rather than inventing
specific institutional facts (no invented university names, room
numbers, schedules, staff names, or equipment specifications).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from app.decision.event_manager import GuideTopic


@dataclass(frozen=True)
class TopicContent:
    """Static content for a single guide topic."""

    title: str
    summary: str
    sections: List[str]
    spoken_text: str


_AI_PROJECTS = TopicContent(
    title="AI Projects in the Lab",
    summary=(
        "An overview of the artificial intelligence projects developed "
        "and studied in this laboratory, from computer vision to "
        "applied machine learning."
    ),
    sections=[
        "Students in this lab work on practical AI systems such as "
        "computer vision, natural language processing, and predictive "
        "modeling.",
        "Projects typically move from a research idea, through a "
        "working prototype, to a tested and documented system.",
        "This robot guide is itself an example of applied AI: it "
        "combines perception, decision-making, and interaction into a "
        "single working system.",
    ],
    spoken_text=(
        "In this lab, we build real AI systems, from computer vision to "
        "machine learning models, and take them from an idea all the "
        "way to a working, tested prototype."
    ),
)

_ROBOTICS = TopicContent(
    title="Robotics in the Lab",
    summary=(
        "How robotics work is carried out in this laboratory, covering "
        "perception, control, and physical interaction."
    ),
    sections=[
        "Robotics work here combines software, for perception and "
        "control, with hardware such as sensors, actuators, and "
        "physical platforms.",
        "Students learn how a robot senses its environment, decides "
        "how to respond, and then acts through motors or other "
        "actuators.",
        "This guide robot is a working example of that pipeline: it "
        "perceives visitors, decides how to engage them, and expresses "
        "that decision physically.",
    ],
    spoken_text=(
        "Robotics here is about connecting perception, decision-making, "
        "and physical action: sensing the world, deciding what to do, "
        "and then actually doing it."
    ),
)

_TRAINING = TopicContent(
    title="Training & Learning Opportunities",
    summary=(
        "An overview of how students are trained and mentored in this "
        "laboratory's AI and robotics programs."
    ),
    sections=[
        "Training combines structured coursework with hands-on project "
        "work, so concepts are applied immediately rather than only "
        "studied theoretically.",
        "Students typically progress from guided exercises to "
        "independent or team-based projects with real deliverables.",
        "Mentorship and design review are a normal part of the "
        "process, helping students build both technical and "
        "professional skills.",
    ],
    spoken_text=(
        "Training in this lab blends coursework with hands-on projects, "
        "so students learn AI and robotics concepts by actually "
        "building with them."
    ),
)

_LAB_INFORMATION = TopicContent(
    title="About This Lab",
    summary=(
        "General information about this laboratory's purpose and the "
        "kind of work carried out here."
    ),
    sections=[
        "This laboratory supports applied work in artificial "
        "intelligence and robotics, bridging coursework and practical "
        "system-building.",
        "Facilities generally include workstations for software "
        "development and space for testing robotics prototypes.",
        "Visitors are welcome to ask about ongoing projects, and "
        "students are often happy to explain their work in more "
        "detail.",
    ],
    spoken_text=(
        "Welcome. This lab is where AI and robotics coursework turns "
        "into real, working projects. Feel free to ask about anything "
        "you see here."
    ),
)


TOPIC_CONTENT: Dict[GuideTopic, TopicContent] = {
    GuideTopic.AI_PROJECTS: _AI_PROJECTS,
    GuideTopic.ROBOTICS: _ROBOTICS,
    GuideTopic.TRAINING: _TRAINING,
    GuideTopic.LAB_INFORMATION: _LAB_INFORMATION,
}
