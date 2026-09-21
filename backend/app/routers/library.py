"""La Biblioteca: cursos cortos por tema que se practican con el tutor."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.deps import get_current_user, require_access
from app.models import FlashCourse, FlashCourseProgress, User
from app.repositories import flash_course_repository
from app.schemas.library import FlashCourseDetailOut, FlashCourseSummaryOut, KeyPhraseOut, ScenarioOut

router = APIRouter(prefix="/library", tags=["library"], dependencies=[Depends(require_access)])


def _summary(course: FlashCourse, progress: FlashCourseProgress | None) -> dict:
    done = set(progress.completed_scenarios) if progress else set()
    ids = [scenario["id"] for scenario in course.scenarios]
    return {
        "slug": course.slug,
        "title": course.title,
        "title_es": course.title_es,
        "description_es": course.description_es,
        "category": course.category,
        "icon": course.icon,
        "recommended_level": course.recommended_level,
        "duration_minutes": course.duration_minutes,
        "scenario_count": len(ids),
        # Solo cuenta los que siguen existiendo en el curso: si se retira
        # un escenario, su progreso antiguo no debe dejar un "4 de 3".
        "completed_scenarios": len(done.intersection(ids)),
        "completed": bool(ids) and done.issuperset(ids),
    }


@router.get("/courses", response_model=list[FlashCourseSummaryOut])
async def list_courses(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[FlashCourseSummaryOut]:
    courses = await flash_course_repository.list_all(db)
    progress = await flash_course_repository.progress_by_course(db, current_user.id)
    return [FlashCourseSummaryOut(**_summary(course, progress.get(course.id))) for course in courses]


@router.get("/courses/{slug}", response_model=FlashCourseDetailOut)
async def get_course(
    slug: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> FlashCourseDetailOut:
    course = await flash_course_repository.get_by_slug(db, slug)
    if course is None:
        raise HTTPException(status_code=404, detail="Curso no encontrado.")

    progress = (await flash_course_repository.progress_by_course(db, current_user.id)).get(course.id)
    done = set(progress.completed_scenarios) if progress else set()

    return FlashCourseDetailOut(
        **_summary(course, progress),
        communicative_objectives=course.communicative_objectives,
        key_phrases=[KeyPhraseOut(**phrase) for phrase in course.key_phrases],
        scenarios=[
            ScenarioOut(
                id=scenario["id"],
                title=scenario["title"],
                prompt=scenario["prompt"],
                tutor_role=scenario["tutor_role"],
                completed=scenario["id"] in done,
            )
            for scenario in course.scenarios
        ],
    )
