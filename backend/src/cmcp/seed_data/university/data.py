from __future__ import annotations

from typing import Any, Dict, List


CHAPTERS_PER_COURSE: List[Dict[str, str | int]] = [
    {"number": 1, "title": "Foundations", "description": "Core vocabulary, setup, and baseline concepts."},
    {"number": 2, "title": "Core Concepts", "description": "The main ideas students need before practical work."},
    {"number": 3, "title": "Practice Lab", "description": "Guided examples, exercises, and applied problem solving."},
    {"number": 4, "title": "Project & Review", "description": "Small project work, revision, and assessment preparation."},
]


COURSES: List[Dict[str, Any]] = [
    # Semester 1
    {"title": "Python Programming I", "code": "PY101", "semester_number": 1, "department_code": "CA", "credit_hours": 3, "description": "Python syntax, control flow, functions, and beginner problem solving."},
    {"title": "Mathematics for Computing I", "code": "MTH101", "semester_number": 1, "department_code": "CA", "credit_hours": 3, "description": "Algebra, functions, logic, and quantitative foundations for computing."},
    {"title": "Computer Fundamentals", "code": "CSE101", "semester_number": 1, "department_code": "CA", "credit_hours": 3, "description": "Hardware, software, operating systems, and practical computer use."},
    {"title": "Introduction to Information Technology", "code": "IT101", "semester_number": 1, "department_code": "IS", "credit_hours": 3, "description": "IT systems, organizations, data, networks, and digital services."},
    {"title": "Computer Ethics", "code": "ETH101", "semester_number": 1, "department_code": "IS", "credit_hours": 2, "description": "Professional ethics, privacy, intellectual property, and responsible computing."},
    {"title": "Web Foundations", "code": "WEB101", "semester_number": 1, "department_code": "CA", "credit_hours": 3, "description": "HTML, CSS, browser basics, and static website structure."},
    {"title": "Academic English for IT", "code": "ENG101", "semester_number": 1, "department_code": "IS", "credit_hours": 2, "description": "Technical reading, writing, presentations, and academic communication."},
    {"title": "Study Skills and Digital Literacy", "code": "SDL101", "semester_number": 1, "department_code": "IS", "credit_hours": 2, "description": "Research habits, productivity tools, collaboration, and online safety."},

    # Semester 2
    {"title": "Python Programming II", "code": "PY102", "semester_number": 2, "department_code": "CA", "credit_hours": 3, "description": "Object-oriented Python, modules, files, exceptions, and testing basics."},
    {"title": "Discrete Mathematics", "code": "MTH102", "semester_number": 2, "department_code": "CA", "credit_hours": 3, "description": "Sets, relations, graphs, combinatorics, and proof techniques."},
    {"title": "Database Systems", "code": "DB102", "semester_number": 2, "department_code": "IS", "credit_hours": 3, "description": "Relational design, SQL, normalization, indexes, and constraints."},
    {"title": "React JS Fundamentals", "code": "REACT102", "semester_number": 2, "department_code": "CA", "credit_hours": 3, "description": "Components, props, state, events, routing, and API-driven UI."},
    {"title": "Data Structures", "code": "DS102", "semester_number": 2, "department_code": "CA", "credit_hours": 3, "description": "Arrays, linked lists, stacks, queues, trees, and complexity basics."},
    {"title": "Digital Logic Design", "code": "DLD102", "semester_number": 2, "department_code": "CA", "credit_hours": 3, "description": "Boolean algebra, gates, circuits, and digital representation."},
    {"title": "Communication Skills for Technology", "code": "COM102", "semester_number": 2, "department_code": "IS", "credit_hours": 2, "description": "Workplace communication, technical reports, and team collaboration."},
    {"title": "UI and UX Design Basics", "code": "UX102", "semester_number": 2, "department_code": "CA", "credit_hours": 2, "description": "User research, wireframes, usability, accessibility, and interface patterns."},

    # Semester 3
    {"title": "Algorithms", "code": "ALG201", "semester_number": 3, "department_code": "CA", "credit_hours": 3, "description": "Algorithm design, recursion, sorting, searching, and complexity analysis."},
    {"title": "Software Engineering", "code": "SE201", "semester_number": 3, "department_code": "CA", "credit_hours": 3, "description": "Requirements, design, development processes, quality, and maintenance."},
    {"title": "Operating Systems", "code": "OS201", "semester_number": 3, "department_code": "CA", "credit_hours": 3, "description": "Processes, memory, filesystems, scheduling, and concurrency fundamentals."},
    {"title": "Computer Networks", "code": "NET201", "semester_number": 3, "department_code": "IS", "credit_hours": 3, "description": "Network models, IP addressing, routing, switching, and common protocols."},
    {"title": "Backend APIs with Flask", "code": "API201", "semester_number": 3, "department_code": "CA", "credit_hours": 3, "description": "REST APIs, validation, authentication, SQLAlchemy, and service layering."},
    {"title": "Cybersecurity Fundamentals", "code": "SEC201", "semester_number": 3, "department_code": "IS", "credit_hours": 3, "description": "Threats, controls, secure practices, encryption, and incident basics."},
    {"title": "Statistics for Computing", "code": "STA201", "semester_number": 3, "department_code": "IS", "credit_hours": 3, "description": "Descriptive statistics, probability, distributions, and data interpretation."},

    # Semester 4
    {"title": "Mobile App Development", "code": "MOB202", "semester_number": 4, "department_code": "CA", "credit_hours": 3, "description": "Mobile UI, navigation, local state, API integration, and deployment basics."},
    {"title": "Cloud Computing", "code": "CLD202", "semester_number": 4, "department_code": "IS", "credit_hours": 3, "description": "Cloud models, virtual machines, containers, storage, and deployment patterns."},
    {"title": "Artificial Intelligence Basics", "code": "AI202", "semester_number": 4, "department_code": "CA", "credit_hours": 3, "description": "Search, reasoning, machine learning concepts, and practical AI use cases."},
    {"title": "Data Analytics", "code": "DA202", "semester_number": 4, "department_code": "IS", "credit_hours": 3, "description": "Data cleaning, analysis workflows, dashboards, and decision support."},
    {"title": "DevOps and Deployment", "code": "DEV202", "semester_number": 4, "department_code": "CA", "credit_hours": 3, "description": "Git workflows, CI/CD, containers, environments, and release practices."},
    {"title": "IT Project Management", "code": "PM202", "semester_number": 4, "department_code": "IS", "credit_hours": 3, "description": "Planning, scope, risk, agile delivery, documentation, and stakeholder management."},
    {"title": "Capstone Project Preparation", "code": "CAP202", "semester_number": 4, "department_code": "CA", "credit_hours": 3, "description": "Problem selection, proposal writing, architecture, and project planning."},
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
            "password": "ChangeMe!123",
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
            "username": "jc_student1",
            "email": "c12291@student.jamhuriya.edu",
            "password": "ChangeMe!123",
            "user_type": "STUDENT",
            "profile": {
                "full_name": "Zahra Student",
                "student_id": "C12291",
                "faculty_code": "FCS",
                "department_code": "IS",
                "semester_number": 1,
                "classroom_id": None,
                "is_enabled": True,
            },
        },
        "student_users": [
            {
                "username": "jc_student2",
                "email": "c12292@student.jamhuriya.edu",
                "password": "ChangeMe!123",
                "user_type": "STUDENT",
                "profile": {
                    "full_name": "Ahmed Computer App",
                    "student_id": "C12292",
                    "faculty_code": "FCS",
                    "department_code": "CA",
                    "semester_number": 2,
                    "classroom_name": "CA227",
                    "is_enabled": True,
                },
            }
        ],
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
                "materials_per_chapter": 15,
                "mock_files_dir": "mock_files",
                "pdf_files": [
                    "Operating System Concepts Essentials - A. Silberschatz, et al., (Wiley, 2011) WW (1).pdf",
                    "Chapter 2  Operating-System Structures.ppt.pdf",
                    "Mobile and Web based FYPs.pdf",
                    "NLP_Guidline.pdf",
                    "What is a data structure2.pdf",
                ],
                "slide_files": [
                    "Chapter 5  CPU Scheduling_Part_One.pptx",
                    "Chapter 4 Making Decisions.pptx",
                    "Java Collections - Stack Structure.pptx",
                    "Oracle 12c Chapter 7-1.pptx",
                    "ethcpp06.ppt",
                    "Lecture 252.ppt",
                    "s.ppt",
                ],
                "doc_files": [
                    "DCMMS_full  updated last 2.docx",
                    "DSA Quiz 2 (2213).docx",
                    "RMS_Database_Design.docx",
                ],
                "video_files": [
                    "WhatsApp Video 2026-08-13 at 10.06.17 AM.mp4",
                    "WhatsApp Video 2026-08-13 at 10.06.27 AM.mp4",
                    "WhatsApp Video 2026-08-13 at 10.06.28 AM.mp4",
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
                    {
                        "title_suffix": "Next.js Docs",
                        "url": "https://nextjs.org/docs",
                        "description": "Next.js documentation for app routing and rendering.",
                    },
                    {
                        "title_suffix": "FastAPI Docs",
                        "url": "https://fastapi.tiangolo.com/",
                        "description": "FastAPI documentation for modern Python APIs.",
                    },
                    {
                        "title_suffix": "Git Book — Basics",
                        "url": "https://git-scm.com/book/en/v2/Getting-Started-About-Version-Control",
                        "description": "Pro Git book chapter on version control basics.",
                    },
                    {
                        "title_suffix": "Stack Overflow — Processes vs Threads",
                        "url": "https://stackoverflow.com/questions/200469/what-is-the-difference-between-a-process-and-a-thread",
                        "description": "Community discussion comparing processes and threads.",
                    },
                ],
            },
        },
    }
]
