"""
Guide locations — structured, static prototype information about
university places and services.

This module contains ONLY content data, following the exact same
pattern already established in app.guide.content (TopicContent /
TOPIC_CONTENT). It has no application logic and no knowledge of Vision,
Robot, Decision, ML, DL, Navigation, or UI.

LocationId is a plain string (not an Enum) by design: real university
location data is expected to be open-ended and swapped in later, and a
plain string keeps adding/renaming a location a pure data change rather
than a change to a shared Enum contract. This is deliberately
independent from the existing GuideTopic enum
(app.decision.event_manager.GuideTopic), which continues to serve its
own, unrelated lab-tour-topic flow completely unchanged — see
docs/guide.md for the full rationale and the Guide-vs-Navigation field
ownership split.

IMPORTANT — PROTOTYPE DATA DISCLAIMER:

All location data below is PROTOTYPE / EXAMPLE data. Buildings,
floors, services, and opening information do not represent any real
institution and should be replaced with actual university data when
available. Nothing here should be read as a factual claim about any
specific real university.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional

LocationId = str


@dataclass(frozen=True)
class LocationRecord:
    """
    Static prototype information about a single university location.

    Guide-owned fields only (see docs/guide.md for the full Guide vs.
    Navigation field-ownership split): no coordinates, waypoints, route
    graph, distance, or turn-by-turn data belongs here — that is
    Navigation's future responsibility, not Guide's. Guide describes a
    place; it never calculates how to get there.

    Attributes:
        location_id: Stable identifier used to look this record up.
        name: Display name.
        building: Prototype building name.
        floor: Prototype floor description, if applicable.
        description: One-paragraph overview (this becomes
            GuideResponse.summary).
        services: Short list of services offered at this location.
        facilities: Short list of facilities available here.
        opening_info: Prototype availability note (never a real claim).
        spoken_text: Short, natural text suitable for robot speech.
    """

    location_id: LocationId
    name: str
    building: str
    floor: Optional[str]
    description: str
    services: List[str]
    facilities: List[str]
    opening_info: Optional[str]
    spoken_text: str


_AI_LAB = LocationRecord(
    location_id="ai_lab",
    name="AI Lab",
    building="Engineering Building",
    floor="2nd floor",
    description=(
        "The AI Lab is a workspace for artificial intelligence and "
        "machine learning projects, including computer vision and "
        "applied research."
    ),
    services=["Project supervision", "Equipment checkout"],
    facilities=["GPU workstations", "Meeting area"],
    opening_info="Open during regular class hours on weekdays.",
    spoken_text=(
        "The AI Lab is on the second floor of the Engineering "
        "Building. Students use it for AI, machine learning, and "
        "computer vision projects."
    ),
)

_ROBOTICS_LAB = LocationRecord(
    location_id="robotics_lab",
    name="Robotics Lab",
    building="Engineering Building",
    floor="1st floor",
    description=(
        "The Robotics Lab is where students build and test robotic "
        "systems, from small prototypes to larger project platforms."
    ),
    services=["Equipment checkout", "Safety briefing for new users"],
    facilities=["Workbenches", "Robot testing area", "Tool storage"],
    opening_info="Open during regular class hours on weekdays.",
    spoken_text=(
        "The Robotics Lab is on the first floor of the Engineering "
        "Building. It's where students design, build, and test "
        "robots."
    ),
)

_COMPUTER_LAB = LocationRecord(
    location_id="computer_lab",
    name="Computer Lab",
    building="Engineering Building",
    floor="1st floor",
    description=(
        "The Computer Lab provides general-purpose workstations for "
        "coursework, assignments, and software projects."
    ),
    services=["Printing", "Technical support desk"],
    facilities=["Desktop workstations", "Shared printers"],
    opening_info="Open daily, including evenings during exam periods.",
    spoken_text=(
        "The Computer Lab is on the first floor of the Engineering "
        "Building, with workstations for coursework and assignments."
    ),
)

_LIBRARY = LocationRecord(
    location_id="library",
    name="University Library",
    building="Library Building",
    floor="Multiple floors",
    description=(
        "The University Library offers study spaces, book and journal "
        "collections, and research support for students."
    ),
    services=["Book lending", "Research assistance", "Study room booking"],
    facilities=["Reading rooms", "Group study rooms", "Computer terminals"],
    opening_info="Open daily, with extended hours during exams.",
    spoken_text=(
        "The University Library has study spaces and book collections "
        "across several floors, plus research help if you need it."
    ),
)

_ENGINEERING_BUILDING = LocationRecord(
    location_id="engineering_building",
    name="Engineering Building",
    building="Engineering Building",
    floor=None,
    description=(
        "The Engineering Building houses several labs and lecture "
        "rooms for engineering and computing coursework, including the "
        "AI Lab, Robotics Lab, and Computer Lab."
    ),
    services=["Reception desk"],
    facilities=["Labs", "Lecture rooms", "Student lounge"],
    opening_info="Open during regular university hours.",
    spoken_text=(
        "The Engineering Building holds most of the engineering and "
        "computing labs, including the AI Lab and Robotics Lab."
    ),
)

_STUDENT_AFFAIRS = LocationRecord(
    location_id="student_affairs",
    name="Student Affairs",
    building="Administration Building",
    floor="Ground floor",
    description=(
        "Student Affairs handles student records, enrollment "
        "questions, and general administrative support for students."
    ),
    services=["Enrollment support", "Document requests", "General inquiries"],
    facilities=["Front desk", "Waiting area"],
    opening_info="Open during regular office hours on weekdays.",
    spoken_text=(
        "Student Affairs is on the ground floor of the Administration "
        "Building. They help with enrollment and student records."
    ),
)

_MAIN_AUDITORIUM = LocationRecord(
    location_id="main_auditorium",
    name="Main Auditorium",
    building="Main Building",
    floor="Ground floor",
    description=(
        "The Main Auditorium hosts lectures, seminars, and university "
        "events for larger audiences."
    ),
    services=["Event booking"],
    facilities=["Stage", "Seating for large groups", "AV equipment"],
    opening_info="Open for scheduled events and lectures.",
    spoken_text=(
        "The Main Auditorium is on the ground floor of the Main "
        "Building, and it's used for lectures and larger university "
        "events."
    ),
)

_INNOVATION_LAB = LocationRecord(
    location_id="innovation_lab",
    name="Innovation Lab",
    building="Engineering Building",
    floor="3rd floor",
    description=(
        "The Innovation Lab supports student projects and prototyping "
        "work across disciplines, including hardware and software "
        "prototypes."
    ),
    services=["Project mentoring", "Equipment checkout"],
    facilities=["3D printers", "Prototyping workbenches", "Meeting area"],
    opening_info="Open during regular class hours on weekdays.",
    spoken_text=(
        "The Innovation Lab is on the third floor of the Engineering "
        "Building, where students prototype new projects."
    ),
)

_LECTURE_ROOMS = LocationRecord(
    location_id="lecture_rooms",
    name="Lecture Rooms",
    building="Engineering Building",
    floor="2nd floor",
    description=(
        "The lecture rooms are used for scheduled classes and "
        "presentations across engineering and computing courses."
    ),
    services=["Room scheduling"],
    facilities=["Projectors", "Seating for classes"],
    opening_info="Open according to the posted class schedule.",
    spoken_text=(
        "The lecture rooms are on the second floor of the Engineering "
        "Building, used for scheduled classes."
    ),
)

_CAFETERIA = LocationRecord(
    location_id="cafeteria",
    name="Cafeteria",
    building="Main Building",
    floor="Ground floor",
    description=(
        "The Cafeteria offers food and drinks for students and staff "
        "throughout the day."
    ),
    services=["Food service", "Seating area"],
    facilities=["Dining tables", "Vending machines"],
    opening_info="Open daily during university hours.",
    spoken_text=(
        "The Cafeteria is on the ground floor of the Main Building, "
        "open daily for food and drinks."
    ),
)


LOCATION_CONTENT: Dict[LocationId, LocationRecord] = {
    _AI_LAB.location_id: _AI_LAB,
    _ROBOTICS_LAB.location_id: _ROBOTICS_LAB,
    _COMPUTER_LAB.location_id: _COMPUTER_LAB,
    _LIBRARY.location_id: _LIBRARY,
    _ENGINEERING_BUILDING.location_id: _ENGINEERING_BUILDING,
    _STUDENT_AFFAIRS.location_id: _STUDENT_AFFAIRS,
    _MAIN_AUDITORIUM.location_id: _MAIN_AUDITORIUM,
    _INNOVATION_LAB.location_id: _INNOVATION_LAB,
    _LECTURE_ROOMS.location_id: _LECTURE_ROOMS,
    _CAFETERIA.location_id: _CAFETERIA,
}
