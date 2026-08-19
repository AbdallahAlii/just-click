from __future__ import annotations

from typing import Any, Dict, List


CHAPTERS_PER_COURSE: List[Dict[str, str | int]] = [
    {"number": 1, "title": "Foundations", "description": "Core vocabulary, setup, and baseline concepts."},
    {"number": 2, "title": "Core Concepts", "description": "The main ideas students need before practical work."},
]


COURSES: List[Dict[str, Any]] = [
    # Semester 1 — 1 CA + 1 IS
    {
        "title": "Python Programming I",
        "code": "PY101",
        "semester_number": 1,
        "department_code": "CA",
        "credit_hours": 3,
        "description": "Python syntax, control flow, functions, and beginner problem solving.",
    },
    {
        "title": "Introduction to Information Technology",
        "code": "IT101",
        "semester_number": 1,
        "department_code": "IS",
        "credit_hours": 3,
        "description": "IT systems, organizations, data, networks, and digital services.",
    },
    # Semester 2
    {
        "title": "React JS Fundamentals",
        "code": "REACT102",
        "semester_number": 2,
        "department_code": "CA",
        "credit_hours": 3,
        "description": "Components, props, state, events, routing, and API-driven UI.",
    },
    {
        "title": "Database Systems",
        "code": "DB102",
        "semester_number": 2,
        "department_code": "IS",
        "credit_hours": 3,
        "description": "Relational design, SQL, normalization, indexes, and constraints.",
    },
    # Semester 3
    {
        "title": "Operating Systems",
        "code": "OS201",
        "semester_number": 3,
        "department_code": "CA",
        "credit_hours": 3,
        "description": "Processes, memory, filesystems, scheduling, and concurrency fundamentals.",
    },
    {
        "title": "Computer Networks",
        "code": "NET201",
        "semester_number": 3,
        "department_code": "IS",
        "credit_hours": 3,
        "description": "Network models, IP addressing, routing, switching, and common protocols.",
    },
    # Semester 4
    {
        "title": "Artificial Intelligence Basics",
        "code": "AI202",
        "semester_number": 4,
        "department_code": "CA",
        "credit_hours": 3,
        "description": "Search, reasoning, machine learning concepts, and practical AI use cases.",
    },
    {
        "title": "Data Analytics",
        "code": "DA202",
        "semester_number": 4,
        "department_code": "IS",
        "credit_hours": 3,
        "description": "Data cleaning, analysis workflows, dashboards, and decision support.",
    },
]


UNIVERSITIES: List[Dict[str, Any]] = [
    {
        "company": {
            "name": "Jamhuriya University",
            "code": "JC",
            "contact_email": "info@jamhuriya.edu",
            "contact_phone": "+252 61 000 0000",
            "country": "Somalia",
            "city": "Mogadishu",
            "timezone": "Africa/Mogadishu",
            "is_enabled": True,
        },
        "super_admin_user": {
            "username": "jc_admin",
            "email": "admin@jamhuriya.edu",
            "password": "just1234",
            "user_type": "ADMIN",
            "profile": {
                "full_name": "Jamhuriya University Admin",
                "staff_id": "JC-ADM-0001",
                "faculty_code": "FCS",
                "department_code": "CA",
                "is_enabled": True,
            },
        },
        "student_user": {
            "username": "C12222",
            "email": "c12222@student.jamhuriya.edu",
            "password": "just1234",
            "user_type": "STUDENT",
            "profile": {
                "full_name": "Zahra Student",
                "student_id": "C12222",
                "faculty_code": "FCS",
                "department_code": "CA",
                "semester_number": 1,
                "classroom_id": None,
                "is_enabled": True,
            },
        },
        "student_users": [],
        "academic": {
            "faculty": {"name": "Faculty of Information Technology", "code": "FCS"},
            "departments": [
                {"name": "Computer Applications", "code": "CA"},
                {"name": "Information Systems", "code": "IS"},
            ],
            "academic_year": {"name": "2025/2026"},
            "semesters": [
                {"number": 1, "name": "Semester 1"},
                {"number": 2, "name": "Semester 2"},
                {"number": 3, "name": "Semester 3"},
                {"number": 4, "name": "Semester 4"},
            ],
            "classrooms": [
                {"name": "CA222", "room_number": "12", "is_enabled": True},
                {"name": "CA227", "room_number": "7", "is_enabled": True},
                {"name": "IT Lab 1", "room_number": "LAB-1", "is_enabled": True},
            ],
            "courses": COURSES,
            "chapters_per_course": CHAPTERS_PER_COURSE,
            "materials": {
                "include_course_syllabus": True,
                "include_chapter_slides": True,
                "materials_per_chapter": 6,
                "max_video_materials": 2,
                "mock_files_dir": "mock_files",
                "pdf_files": [
                    "NLP_Guidline.pdf",
                    "What is a data structure2.pdf",
                    "Mobile and Web based FYPs.pdf",
                ],
                "slide_files": [
                    "Chapter 4 Making Decisions.pptx",
                    "Java Collections - Stack Structure.pptx",
                    "s.ppt",
                ],
                "doc_files": [
                    "DSA Quiz 2 (2213).docx",
                    "RMS_Database_Design.docx",
                ],
                "video_files": [
                    "WhatsApp Video 2026-08-13 at 10.06.17 AM.mp4",
                ],
                "link_resources": [
                    {
                        "title_suffix": "Python Docs — Tutorial",
                        "url": "https://docs.python.org/3/tutorial/",
                        "description": "Official Python tutorial covering core language concepts.",
                    },
                    {
                        "title_suffix": "MDN — JavaScript Guide",
                        "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide",
                        "description": "MDN JavaScript guide for web fundamentals.",
                    },
                    {
                        "title_suffix": "PostgreSQL Docs — SQL",
                        "url": "https://www.postgresql.org/docs/current/sql.html",
                        "description": "PostgreSQL SQL language reference.",
                    },
                    {
                        "title_suffix": "React Docs — Learn React",
                        "url": "https://react.dev/learn",
                        "description": "Official React learning path for components and state.",
                    },
                ],
            },
        },
    }
]
