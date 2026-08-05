"""Repository générique — isole les services de SQLAlchemy.

Les services appellent add/get/list/delete sans jamais toucher db.session.
On peut remplacer l'implémentation (autre ORM, mock en test) sans toucher aux
services : c'est le Dependency Inversion Principle appliqué à la persistance.
"""
from __future__ import annotations

from typing import Generic, TypeVar

from ..extensions import db

T = TypeVar("T")


class BaseRepository(Generic[T]):
    model: type[T]

    def add(self, entity: T, *, commit: bool = True) -> T:
        db.session.add(entity)
        if commit:
            db.session.commit()
        return entity

    def get(self, id_: str) -> T | None:
        return db.session.get(self.model, id_)

    def list(self, **filters) -> list[T]:
        stmt = db.select(self.model).filter_by(**filters)
        return list(db.session.scalars(stmt).all())

    def first(self, **filters) -> T | None:
        stmt = db.select(self.model).filter_by(**filters).limit(1)
        return db.session.scalars(stmt).first()

    def delete(self, entity: T, *, commit: bool = True) -> None:
        db.session.delete(entity)
        if commit:
            db.session.commit()

    def commit(self) -> None:
        db.session.commit()
