"""The scaffold's example resource: list, create, delete. Copy its shape for real ones, then delete it."""

from datetime import datetime

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from ..db import SessionDep
from ..models import Note
from .errors import get_or_404

router = APIRouter(prefix="/notes", tags=["notes"])


class NoteIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    body: str = ""


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    body: str
    created_at: datetime


@router.get("")
def list_notes(session: SessionDep) -> list[NoteOut]:
    notes = session.scalars(select(Note).order_by(Note.created_at.desc(), Note.id.desc()))
    return [NoteOut.model_validate(n) for n in notes]


@router.post("", status_code=201)
def create_note(data: NoteIn, session: SessionDep) -> NoteOut:
    note = Note(**data.model_dump())
    session.add(note)
    session.commit()
    return NoteOut.model_validate(note)


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: int, session: SessionDep) -> None:
    session.delete(get_or_404(session, Note, note_id))
    session.commit()
