import uuid
import os
from datetime import datetime, timezone, timedelta
from database import db
from auth_utils import hash_password

SUBJECT_THUMBS = {
    "Physics": "https://images.unsplash.com/photo-1636466497217-26a8cbeaf0aa?w=800&q=60",
    "Chemistry": "https://images.unsplash.com/photo-1603126857599-f6e157fa2fe6?w=800&q=60",
    "Mathematics": "https://images.unsplash.com/photo-1635372722656-389f87a941b7?w=800&q=60",
    "Biotechnology": "https://images.unsplash.com/photo-1576086213369-97a306d36557?w=800&q=60",
}


async def seed():
    admin_email = os.environ.get("ADMIN_EMAIL", "").lower().strip()
    if admin_email and not await db.users.find_one({"email": admin_email}):
        await db.users.insert_one({
            "_id": str(uuid.uuid4()),
            "name": "Academy Admin",
            "email": admin_email,
            "password_hash": hash_password(os.environ.get("ADMIN_PASSWORD", "Admin@123")),
            "role": "admin",
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

    teacher_email = "teacher@jamacademy.com"
    student_email = "student@jamacademy.com"

    teacher = await db.users.find_one({"email": teacher_email})
    if not teacher:
        teacher = {
            "_id": str(uuid.uuid4()),
            "name": "Dr. Ananya Sharma",
            "email": teacher_email,
            "password_hash": hash_password("Teacher@123"),
            "role": "teacher",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(teacher)

    student = await db.users.find_one({"email": student_email})
    if not student:
        student = {
            "_id": str(uuid.uuid4()),
            "name": "Rahul Verma",
            "email": student_email,
            "password_hash": hash_password("Student@123"),
            "role": "student",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        await db.users.insert_one(student)

    tid = teacher["_id"]
    tname = teacher["name"]

    if await db.courses.count_documents({}) == 0:
        courses_data = [
            ("IIT-JAM Physics Complete Course", "Physics", "Master Mechanics, Electromagnetism, Quantum Mechanics and Thermodynamics with 120+ hours of live and recorded lectures aligned to the latest JAM syllabus.", 4999, "6 months"),
            ("IIT-JAM Chemistry Masterclass", "Chemistry", "Physical, Organic and Inorganic chemistry covered in depth with weekly problem-solving sessions and previous-year paper analysis.", 4999, "6 months"),
            ("IIT-JAM Mathematics Crash Course", "Mathematics", "Real Analysis, Linear Algebra, Calculus and Differential Equations — a focused crash course with daily practice sheets.", 2999, "3 months"),
            ("IIT-JAM Biotechnology Foundation", "Biotechnology", "Biology, Chemistry, Mathematics and Physics fundamentals for the BT paper, taught from first principles.", 3999, "5 months"),
        ]
        for title, subject, desc, price, duration in courses_data:
            sections = [
                {"id": str(uuid.uuid4()), "title": f"{subject} Fundamentals", "lessons": [
                    {"id": str(uuid.uuid4()), "title": f"Introduction to IIT-JAM {subject}", "type": "video", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "duration": "45 min"},
                    {"id": str(uuid.uuid4()), "title": "Syllabus Breakdown & Strategy", "type": "video", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "duration": "30 min"},
                    {"id": str(uuid.uuid4()), "title": "Formula Sheet — Chapter 1", "type": "pdf", "url": "https://example.com/notes.pdf", "duration": "PDF"},
                ]},
                {"id": str(uuid.uuid4()), "title": "Core Concepts", "lessons": [
                    {"id": str(uuid.uuid4()), "title": "Core Concept Lecture 1", "type": "video", "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ", "duration": "60 min"},
                    {"id": str(uuid.uuid4()), "title": "Practice Problem Set 1", "type": "pdf", "url": "https://example.com/pset1.pdf", "duration": "PDF"},
                ]},
            ]
            await db.courses.insert_one({
                "_id": str(uuid.uuid4()), "title": title, "subject": subject,
                "description": desc, "thumbnail": SUBJECT_THUMBS[subject],
                "price": price, "duration": duration, "published": True,
                "teacher_id": tid, "teacher_name": tname, "sections": sections,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

    if await db.live_classes.count_documents({}) == 0:
        now = datetime.now(timezone.utc)
        classes = [
            ("Quantum Mechanics — Wave Functions", "Physics", 1, "Deep dive into Schrödinger's equation and probability densities."),
            ("Organic Chemistry — Reaction Mechanisms", "Chemistry", 2, "SN1 vs SN2 with previous-year JAM questions."),
            ("Real Analysis — Sequences & Series", "Mathematics", 3, "Convergence tests and epsilon-delta proofs."),
        ]
        for title, subject, days, desc in classes:
            await db.live_classes.insert_one({
                "_id": str(uuid.uuid4()), "title": title, "subject": subject,
                "description": desc,
                "start_time": (now + timedelta(days=days)).replace(minute=0, second=0, microsecond=0).isoformat(),
                "duration_min": 90, "meeting_link": "https://meet.google.com/jam-demo-class",
                "teacher_id": tid, "teacher_name": tname,
                "created_at": now.isoformat(),
            })

    if await db.tests.count_documents({}) == 0:
        physics_qs = [
            ("A particle moves in a circle of radius R with constant speed v. Its average acceleration over half a revolution is:", ["zero", "2v²/πR", "v²/R", "4v²/πR"], 1),
            ("The dimension of Planck's constant is the same as that of:", ["Energy", "Angular momentum", "Linear momentum", "Power"], 1),
            ("For a particle in a 1D infinite potential well, the energy of the nth level is proportional to:", ["n", "n²", "1/n", "√n"], 1),
            ("The work done in an isothermal reversible expansion of an ideal gas depends on:", ["Only temperature", "Temperature and volume ratio", "Only pressure", "Only volume"], 1),
            ("Which Maxwell equation implies the absence of magnetic monopoles?", ["∇·E = ρ/ε₀", "∇·B = 0", "∇×E = -∂B/∂t", "∇×B = μ₀J"], 1),
        ]
        maths_qs = [
            ("The sequence aₙ = (1 + 1/n)ⁿ converges to:", ["1", "e", "0", "∞"], 1),
            ("The rank of a 3×3 identity matrix is:", ["0", "1", "2", "3"], 3),
            ("∫₀^π sin(x) dx equals:", ["0", "1", "2", "π"], 2),
            ("A series Σaₙ with aₙ ≥ 0 converges if:", ["aₙ → 0", "partial sums are bounded", "aₙ is decreasing", "aₙ → 1"], 1),
            ("The dimension of the vector space of 2×2 symmetric matrices is:", ["2", "3", "4", "1"], 1),
        ]
        for title, subject, qs in [
            ("JAM Physics Mock Test 1", "Physics", physics_qs),
            ("JAM Mathematics Mock Test 1", "Mathematics", maths_qs),
        ]:
            questions = [{"id": str(uuid.uuid4()), "text": t, "options": o, "correct_index": c, "marks": 4} for t, o, c in qs]
            await db.tests.insert_one({
                "_id": str(uuid.uuid4()), "title": title, "subject": subject,
                "duration_min": 30, "published": True, "questions": questions,
                "total_marks": sum(q["marks"] for q in questions),
                "teacher_id": tid, "teacher_name": tname,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })

    if await db.assignments.count_documents({}) == 0:
        now = datetime.now(timezone.utc)
        for title, subject, desc, days in [
            ("Thermodynamics Problem Set", "Physics", "Solve the 10 problems on Carnot cycles and entropy from the attached sheet. Show all working.", 5),
            ("Linear Algebra Worksheet", "Mathematics", "Prove the given statements on eigenvalues and diagonalizability. Submit a scanned copy or typed link.", 7),
        ]:
            await db.assignments.insert_one({
                "_id": str(uuid.uuid4()), "title": title, "subject": subject,
                "description": desc, "due_date": (now + timedelta(days=days)).date().isoformat(),
                "max_marks": 10, "teacher_id": tid, "teacher_name": tname,
                "created_at": now.isoformat(),
            })

    if await db.batches.count_documents({}) == 0:
        courses = await db.courses.find({}).to_list(10)
        now = datetime.now(timezone.utc)
        for course in courses:
            for name, sched, cap in [
                ("Morning Batch", "Mon–Fri, 7:00–9:00 AM", 50),
                ("Evening Batch", "Mon–Fri, 6:00–8:00 PM", 50),
            ]:
                await db.batches.insert_one({
                    "_id": str(uuid.uuid4()), "course_id": course["_id"],
                    "teacher_id": course["teacher_id"], "name": name,
                    "start_date": (now + timedelta(days=7)).date().isoformat(),
                    "schedule": sched, "capacity": cap,
                    "created_at": now.isoformat(),
                })

    if await db.announcements.count_documents({}) == 0:
        for title, body in [
            ("JAM 2027 Registration Opens Soon", "IIT Bombay has announced that JAM 2027 registrations will open in the first week of September. Keep your documents ready."),
            ("New Mock Test Series Released", "Two new full-syllabus mock tests for Physics and Mathematics are now live in the Tests section. Attempt them before Sunday's discussion class."),
            ("Doubt-Clearing Session Every Saturday", "Weekly doubt-clearing sessions will be held every Saturday at 6 PM. Join from the Live Classes tab."),
        ]:
            await db.announcements.insert_one({
                "_id": str(uuid.uuid4()), "title": title, "body": body,
                "teacher_id": tid, "teacher_name": tname,
                "created_at": datetime.now(timezone.utc).isoformat(),
            })
