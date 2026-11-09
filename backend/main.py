"""ELEVIA FastAPI backend.

Run:  uvicorn backend.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""
from __future__ import annotations

import hmac
import os
import logging
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from . import db, llm, orchestrator as orch
from .config import get_settings
from .content import lessons, skill_map, skills_by_id, validate_all

log = logging.getLogger("elevia")
DEMO_TEACHER_PIN = "2468"

@asynccontextmanager
async def lifespan(_: FastAPI):
    db.init_db()
    validate_all()  # fail fast on broken content files
    # Free hosts wipe the disk on restart; ELEVIA_AUTO_SEED=1 re-creates the sample students if the DB is empty.
    if os.getenv("ELEVIA_AUTO_SEED", "").lower() in ("1", "true", "yes") and not orch.list_students():
        from .sample_data import seed
        seed()
    yield


app = FastAPI(title="ELEVIA API", version="1.0.0", lifespan=lifespan,
              description="Agentic learning-gap workflow for fractions: Diagnoser, Checker, Planner, Tutor.")

_s = get_settings()
app.add_middleware(CORSMiddleware, allow_origins=_s.cors_origins, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type", "X-Teacher-Pin"])


@app.exception_handler(orch.WorkflowError)
def _workflow_error(_: Request, exc: orch.WorkflowError):
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


@app.exception_handler(Exception)
def _unhandled(_: Request, exc: Exception):
    log.exception("Unhandled error")
    return JSONResponse(status_code=500, content={"detail": "Internal error. The action was not saved."})


# ---------------------------------------------------------------- models

class NewStudent(BaseModel):
    display_name: str = Field(min_length=1, max_length=40)
    grade: int = Field(ge=3, le=8)


class Answer(BaseModel):
    question_id: str = Field(min_length=1, max_length=20)
    answer: str = Field(max_length=40)
    hints_used: int = Field(default=0, ge=0, le=5)


class RetestStart(BaseModel):
    early: bool = False


class GapDecision(BaseModel):
    decision: str = Field(pattern="^(confirm|reject)$")
    teacher_name: str = Field(min_length=1, max_length=60)
    reason: str = Field(min_length=5, max_length=500)
    focus_skill: Optional[str] = None


class FocusChange(BaseModel):
    focus_skill: str
    teacher_name: str = Field(min_length=1, max_length=60)
    reason: str = Field(min_length=5, max_length=500)


class Note(BaseModel):
    teacher_name: str = Field(min_length=1, max_length=60)
    note: str = Field(min_length=5, max_length=500)


# ---------------------------------------------------------------- auth

def _effective_pin() -> tuple[str, bool]:
    pin = get_settings().teacher_pin
    return (pin, False) if pin else (DEMO_TEACHER_PIN, True)


def require_teacher(x_teacher_pin: str = Header(default="")) -> None:
    pin, _ = _effective_pin()
    if not hmac.compare_digest(x_teacher_pin.encode(), pin.encode()):
        raise HTTPException(status_code=401, detail="Teacher PIN required.")


# ---------------------------------------------------------------- public

@app.get("/health")
def health():
    s = get_settings()
    _, demo_pin = _effective_pin()
    return {"ok": True, "content": validate_all(), "llm": llm.status(s), "demo_teacher_pin": demo_pin,
            "retest_delay_hours": s.retest_delay_hours, "allow_early_retest": s.allow_early_retest}


@app.get("/skills")
def skills():
    m = skill_map()
    return {"skills": m["skills"], "misconceptions": m["misconceptions"], "teachable": sorted(lessons()),
            "curriculum_note": m.get("curriculum_note")}


# ---------------------------------------------------------------- student

@app.get("/students")
def students():
    return orch.list_students()


@app.post("/students", status_code=201)
def new_student(body: NewStudent):
    return orch.create_student(body.display_name, body.grade)


@app.get("/students/{student_id}/overview")
def overview(student_id: int):
    return orch.student_overview(student_id)


@app.post("/students/{student_id}/cases")
def start_case(student_id: int):
    return orch.start_case(student_id)


@app.get("/cases/{case_id}")
def case(case_id: int):
    return orch.case_detail(case_id)


@app.get("/assessments/{assessment_id}")
def assessment(assessment_id: int):
    return orch.get_assessment(assessment_id)


@app.post("/assessments/{assessment_id}/answers")
def answer(assessment_id: int, body: Answer):
    return orch.submit_answer(assessment_id, body.question_id, body.answer, body.hints_used)


@app.get("/assessments/{assessment_id}/hint")
def hint(assessment_id: int, question_id: str, level: int = 1):
    return orch.get_hint(assessment_id, question_id, level)


@app.post("/assessments/{assessment_id}/finish")
def finish(assessment_id: int):
    return orch.finish_practice(assessment_id)


@app.post("/cases/{case_id}/retest")
def retest(case_id: int, body: RetestStart):
    return orch.start_retest(case_id, early=body.early)


# ---------------------------------------------------------------- teacher (PIN protected)

@app.get("/teacher/overview", dependencies=[Depends(require_teacher)])
def teacher_overview():
    return orch.teacher_overview()


@app.get("/teacher/students/{student_id}", dependencies=[Depends(require_teacher)])
def teacher_student(student_id: int):
    return orch.student_overview(student_id)


@app.get("/teacher/cases/{case_id}", dependencies=[Depends(require_teacher)])
def teacher_case(case_id: int):
    return orch.case_detail(case_id)


@app.post("/teacher/cases/{case_id}/gap-decision", dependencies=[Depends(require_teacher)])
def gap_decision(case_id: int, body: GapDecision):
    return orch.teacher_gap_decision(case_id, body.decision, body.teacher_name, body.reason, body.focus_skill)


@app.post("/teacher/cases/{case_id}/focus", dependencies=[Depends(require_teacher)])
def change_focus(case_id: int, body: FocusChange):
    return orch.teacher_set_focus(case_id, body.focus_skill, body.teacher_name, body.reason)


@app.post("/teacher/cases/{case_id}/notes", dependencies=[Depends(require_teacher)])
def add_note(case_id: int, body: Note):
    return orch.teacher_note(case_id, body.teacher_name, body.note)
