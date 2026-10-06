"""Shared state passed between agents + Pydantic schemas for strict JSON outputs."""
from typing import TypedDict

from pydantic import BaseModel


class PipelineState(TypedDict, total=False):
    run_id: str
    idea: str
    requirements: dict
    architecture: dict
    files: dict            # {filepath: code}  (includes tests/)
    tests_written: bool
    test_results: dict     # {"passed": bool, "log": str}
    review_issues: list
    feedback: str          # what the coder must fix next
    retry_count: int
    review_rounds: int
    zip_path: str
    status: str            # running / done / failed


class Requirements(BaseModel):
    app_name: str
    summary: str
    user_stories: list[str]
    features: list[str]
    acceptance_criteria: list[str]
    out_of_scope: list[str] = []


class FileSpec(BaseModel):
    path: str
    purpose: str


class Task(BaseModel):
    id: str
    title: str
    files: list[str]
    description: str


class Architecture(BaseModel):
    stack: dict
    files: list[FileSpec]
    tasks: list[Task]
    contract: str = ""


class Issue(BaseModel):
    severity: str          # high / medium / low
    file: str = ""
    description: str


class Review(BaseModel):
    approved: bool
    issues: list[Issue] = []
