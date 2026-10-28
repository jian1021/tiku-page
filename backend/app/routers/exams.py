"""模拟考试接口：配置、开始、答题、交卷、结果与历史。"""

import json
import random
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user, get_current_user_optional
from ..models import (
    AnswerRecord,
    Chapter,
    Exam,
    ExamConfig,
    Membership,
    Question,
    User,
    WrongQuestion,
)
from ..serializers import question_public, question_with_answer

router = APIRouter(tags=["模拟考试"])

_CONFIG_KEYS = ("question_count", "duration_minutes", "pass_score", "total_score")


class StartExamRequest(BaseModel):
    """开始考试请求，题量与时长均可选。"""

    question_count: Optional[int] = None
    duration_minutes: Optional[int] = None


class SaveExamAnswerRequest(BaseModel):
    """保存考试答案请求。"""

    question_id: int
    selected: list[str] = Field(default_factory=list)


class SubmitExamRequest(BaseModel):
    """交卷请求，answers 为题目 ID -> 选项 key 数组。"""

    answers: Optional[dict[str, list[str]]] = None


def _is_member(db: Session, user: User) -> bool:
    """管理员视为会员，普通用户需会员未过期。"""
    if user.role == "admin":
        return True
    membership = (
        db.query(Membership).filter(Membership.user_id == user.id).first()
    )
    return (
        membership is not None
        and membership.expires_at is not None
        and membership.expires_at > datetime.now()
    )


def _parse_number(value: Any) -> Optional[int | float]:
    """将配置值解析为 int 或 float，无法解析返回 None。"""
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        number = float(text)
    except (TypeError, ValueError):
        return None
    if number.is_integer():
        return int(number)
    return number


def _parse_int(value: Any) -> Optional[int]:
    """将配置值解析为整数。"""
    number = _parse_number(value)
    if number is None:
        return None
    return int(number)


def _config_map(db: Session, province_code: Optional[str]) -> dict[str, str]:
    """读取指定省份的考试配置 key -> value。"""
    if not province_code:
        return {}
    rows = (
        db.query(ExamConfig)
        .filter(ExamConfig.province_code == province_code)
        .all()
    )
    return {row.key: row.value for row in rows}


def _setting_int(user: Optional[User], key: str) -> Optional[int]:
    """读取用户 settings 中的整数配置。"""
    if user is None or not isinstance(user.settings, dict):
        return None
    return _parse_int(user.settings.get(key))


def _score_settings(db: Session, province_code: Optional[str]) -> tuple[float, float]:
    """返回 (pass_score, total_score)，缺失时使用兜底值。"""
    config = _config_map(db, province_code)
    total_value = _parse_number(config.get("total_score"))
    pass_value = _parse_number(config.get("pass_score"))
    total_score = float(total_value) if total_value is not None else 100.0
    pass_score = float(pass_value) if pass_value is not None else 60.0
    return pass_score, total_score


def _exam_province(db: Session, exam: Exam) -> Optional[str]:
    """取考试所属用户当前省份，用于读取考试配置。"""
    user = db.get(User, exam.user_id)
    return user.province_code if user is not None else None


def _get_exam_for_user(db: Session, exam_id: int, user: User) -> Exam:
    """读取本人考试，不存在或非本人均按不存在处理。"""
    exam = db.get(Exam, exam_id)
    if exam is None or exam.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="考试不存在",
        )
    return exam


def _exam_deadline(exam: Exam) -> datetime:
    """考试截止时间。"""
    return exam.started_at + timedelta(seconds=exam.duration_limit_sec or 0)


def _used_seconds(exam: Exam) -> int:
    """已用时（秒）。"""
    if exam.submitted_at is None:
        return 0
    seconds = int((exam.submitted_at - exam.started_at).total_seconds())
    return max(0, seconds)


def _answer_correct(question: Question, selected: list[str]) -> bool:
    """按集合完全相等判分，单选、多选、判断规则一致。"""
    answer_keys = {str(item) for item in (question.answer or [])}
    selected_keys = {str(item) for item in (selected or [])}
    return selected_keys == answer_keys


def _normalize_answers(raw: Any) -> dict[str, list[str]]:
    """统一考试答案为字符串 key + 选项数组。"""
    if not isinstance(raw, dict):
        return {}
    result: dict[str, list[str]] = {}
    for key, value in raw.items():
        if isinstance(value, list):
            result[str(key)] = [str(item) for item in value]
        elif value is None:
            result[str(key)] = []
        else:
            result[str(key)] = [str(value)]
    return result


def _exam_summary(db: Session, exam: Exam) -> dict:
    """考试交卷后的成绩摘要。"""
    pass_score, total_score = _score_settings(db, _exam_province(db, exam))
    return {
        "id": exam.id,
        "score": exam.score,
        "passed": bool(exam.passed),
        "total": exam.total,
        "total_score": total_score,
        "pass_score": pass_score,
        "used_seconds": _used_seconds(exam),
        "submitted_at": (
            exam.submitted_at.isoformat() if exam.submitted_at else None
        ),
    }


def _grade_exam(db: Session, exam: Exam, now: Optional[datetime] = None) -> Exam:
    """内部判分与交卷；超时则按截止时间记录交卷时间。"""
    if exam.submitted_at is not None:
        return exam

    now = now or datetime.now()
    deadline = _exam_deadline(exam)
    timed_out = now >= deadline
    submitted_at = deadline if timed_out else now

    answers = _normalize_answers(exam.answers)
    question_ids: list[int] = []
    for item in exam.question_ids or []:
        try:
            question_ids.append(int(item))
        except (TypeError, ValueError):
            continue

    questions = (
        db.query(Question).filter(Question.id.in_(question_ids)).all()
        if question_ids
        else []
    )
    question_map = {question.id: question for question in questions}

    total = exam.total or len(question_ids)
    correct_count = 0
    for question_id in question_ids:
        key = str(question_id)
        if key not in answers:
            continue
        question = question_map.get(question_id)
        if question is None:
            continue
        selected = answers[key]
        is_correct = _answer_correct(question, selected)
        if is_correct:
            correct_count += 1

        db.add(
            AnswerRecord(
                user_id=exam.user_id,
                question_id=question_id,
                selected=selected,
                is_correct=is_correct,
                mode="exam",
                created_at=submitted_at,
            )
        )
        if not is_correct:
            wrong = (
                db.query(WrongQuestion)
                .filter(
                    WrongQuestion.user_id == exam.user_id,
                    WrongQuestion.question_id == question_id,
                )
                .first()
            )
            if wrong is None:
                db.add(
                    WrongQuestion(
                        user_id=exam.user_id,
                        question_id=question_id,
                        wrong_count=1,
                        last_wrong_at=now,
                        removed=False,
                    )
                )
            else:
                wrong.wrong_count = (wrong.wrong_count or 0) + 1
                wrong.last_wrong_at = now
                wrong.removed = False

    pass_score, total_score = _score_settings(db, _exam_province(db, exam))
    score = (
        round(correct_count / total * total_score, 1) if total > 0 else 0.0
    )

    exam.answers = answers
    exam.score = score
    exam.passed = score >= pass_score
    exam.submitted_at = submitted_at
    db.commit()
    db.refresh(exam)
    return exam


def _auto_submit_if_timeout(db: Session, exam: Exam) -> bool:
    """未交卷且已超时则自动交卷。"""
    if exam.submitted_at is not None:
        return False
    if datetime.now() >= _exam_deadline(exam):
        _grade_exam(db, exam)
        return True
    return False


def _exam_question_ids(exam: Exam) -> list[int]:
    """解析考试抽题 ID 列表。"""
    result: list[int] = []
    for item in exam.question_ids or []:
        try:
            result.append(int(item))
        except (TypeError, ValueError):
            continue
    return result


def _questions_for_exam(
    db: Session, exam: Exam, with_answer: bool = False
) -> list[dict]:
    """按考试抽题顺序返回题目。"""
    question_ids = _exam_question_ids(exam)
    if not question_ids:
        return []

    questions = db.query(Question).filter(Question.id.in_(question_ids)).all()
    question_map = {question.id: question for question in questions}
    chapter_ids = {
        question.chapter_id
        for question in questions
        if question.chapter_id is not None
    }
    chapters = (
        db.query(Chapter).filter(Chapter.id.in_(chapter_ids)).all()
        if chapter_ids
        else []
    )
    chapter_map = {chapter.id: chapter for chapter in chapters}

    items: list[dict] = []
    for question_id in question_ids:
        question = question_map.get(question_id)
        if question is None:
            continue
        chapter = chapter_map.get(question.chapter_id)
        chapter_name = chapter.name if chapter is not None else None
        if with_answer:
            items.append(
                question_with_answer(question, chapter_name=chapter_name)
            )
        else:
            items.append(question_public(question, chapter_name=chapter_name))
    return items


@router.get("/exam/config")
def get_exam_config(
    province_code: Optional[str] = Query(None, max_length=16),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> dict:
    """返回省份考试配置与用户个性化设置。"""
    resolved_province = (province_code or "").strip() or (
        current_user.province_code if current_user is not None else None
    )
    config = _config_map(db, resolved_province)

    parsed_values = {
        "question_count": _parse_int(config.get("question_count")),
        "duration_minutes": _parse_int(config.get("duration_minutes")),
        "pass_score": _parse_number(config.get("pass_score")),
        "total_score": _parse_number(config.get("total_score")),
    }

    type_distribution = None
    raw_distribution = config.get("type_distribution")
    if raw_distribution is not None and str(raw_distribution).strip():
        try:
            type_distribution = json.loads(raw_distribution)
        except (TypeError, ValueError):
            type_distribution = None

    configured = all(
        config.get(key) is not None and str(config.get(key)).strip() != ""
        for key in _CONFIG_KEYS
    )

    available_questions = 0
    if resolved_province:
        available_questions = (
            db.query(Question)
            .filter(
                Question.province_code == resolved_province,
                Question.status == "published",
            )
            .count()
        )

    return {
        "province_code": resolved_province,
        "question_count": parsed_values["question_count"],
        "duration_minutes": parsed_values["duration_minutes"],
        "pass_score": parsed_values["pass_score"],
        "total_score": parsed_values["total_score"],
        "type_distribution": type_distribution,
        "configured": configured,
        "available_questions": available_questions,
        "user_settings": {
            "exam_question_count": _setting_int(
                current_user, "exam_question_count"
            ),
            "exam_duration_minutes": _setting_int(
                current_user, "exam_duration_minutes"
            ),
        },
    }


@router.post("/exam/start")
def start_exam(
    payload: Optional[StartExamRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """开始一场模拟考试（仅会员）。"""
    payload = payload or StartExamRequest()
    if not _is_member(db, current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="模拟考试仅会员可参加",
        )

    province_code = current_user.province_code
    if not province_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="请先选择省份",
        )

    questions = (
        db.query(Question)
        .filter(
            Question.province_code == province_code,
            Question.status == "published",
        )
        .order_by(Question.id)
        .all()
    )
    if not questions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="该省份暂无可用题目",
        )

    config = _config_map(db, province_code)
    count_value: Optional[int] = payload.question_count
    if count_value is None:
        count_value = _setting_int(current_user, "exam_question_count")
    if count_value is None:
        count_value = _parse_int(config.get("question_count"))

    duration_value: Optional[int] = payload.duration_minutes
    if duration_value is None:
        duration_value = _setting_int(current_user, "exam_duration_minutes")
    if duration_value is None:
        duration_value = _parse_int(config.get("duration_minutes"))

    if count_value is None or duration_value is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="管理员尚未配置本省考试参数",
        )

    question_count = min(int(count_value), len(questions))
    if question_count < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="考试题量配置有误",
        )

    duration_minutes = int(duration_value)
    if duration_minutes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="考试时长配置有误",
        )

    chosen = random.sample(questions, question_count)
    now = datetime.now()
    exam = Exam(
        user_id=current_user.id,
        started_at=now,
        submitted_at=None,
        duration_limit_sec=duration_minutes * 60,
        total=question_count,
        score=None,
        passed=False,
        question_ids=[question.id for question in chosen],
        answers={},
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    pass_score, total_score = _score_settings(db, province_code)
    chapter_ids = {
        question.chapter_id
        for question in chosen
        if question.chapter_id is not None
    }
    chapters = (
        db.query(Chapter).filter(Chapter.id.in_(chapter_ids)).all()
        if chapter_ids
        else []
    )
    chapter_map = {chapter.id: chapter for chapter in chapters}

    return {
        "id": exam.id,
        "started_at": exam.started_at.isoformat(),
        "duration_limit_sec": exam.duration_limit_sec,
        "total": exam.total,
        "server_time": now.isoformat(),
        "pass_score": pass_score,
        "total_score": total_score,
        "questions": [
            question_public(
                question,
                chapter_name=(
                    chapter_map[question.chapter_id].name
                    if question.chapter_id in chapter_map
                    else None
                ),
            )
            for question in chosen
        ],
    }


@router.get("/exam/history")
def get_exam_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """返回当前用户已交卷的考试历史。"""
    exams = (
        db.query(Exam)
        .filter(
            Exam.user_id == current_user.id,
            Exam.submitted_at.isnot(None),
        )
        .order_by(Exam.started_at.desc(), Exam.id.desc())
        .all()
    )
    return {
        "items": [
            {
                "id": exam.id,
                "started_at": (
                    exam.started_at.isoformat() if exam.started_at else None
                ),
                "submitted_at": (
                    exam.submitted_at.isoformat()
                    if exam.submitted_at
                    else None
                ),
                "score": exam.score,
                "passed": bool(exam.passed),
                "total": exam.total,
                "used_seconds": _used_seconds(exam),
                "duration_limit_sec": exam.duration_limit_sec,
            }
            for exam in exams
        ]
    }


@router.get("/exam/{exam_id}")
def get_exam(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """获取考试详情，用于断网恢复；超时自动交卷。"""
    exam = _get_exam_for_user(db, exam_id, current_user)
    _auto_submit_if_timeout(db, exam)

    now = datetime.now()
    if exam.submitted_at is not None:
        remaining_seconds = 0
    else:
        remaining_seconds = max(
            0, int((_exam_deadline(exam) - now).total_seconds())
        )
    pass_score, total_score = _score_settings(
        db, current_user.province_code
    )

    return {
        "id": exam.id,
        "started_at": exam.started_at.isoformat(),
        "submitted_at": (
            exam.submitted_at.isoformat() if exam.submitted_at else None
        ),
        "duration_limit_sec": exam.duration_limit_sec,
        "total": exam.total,
        "score": exam.score,
        "passed": bool(exam.passed),
        "remaining_seconds": remaining_seconds,
        "answers": _normalize_answers(exam.answers),
        "questions": _questions_for_exam(db, exam),
        "server_time": now.isoformat(),
        "pass_score": pass_score,
        "total_score": total_score,
    }


@router.post("/exam/{exam_id}/answer")
def save_exam_answer(
    exam_id: int,
    payload: SaveExamAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """保存单题答案；若已超时则先自动交卷。"""
    exam = _get_exam_for_user(db, exam_id, current_user)
    if exam.submitted_at is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="考试已交卷",
        )

    if datetime.now() >= _exam_deadline(exam):
        _grade_exam(db, exam)
        return {"auto_submitted": True}

    if payload.question_id not in _exam_question_ids(exam):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="题目不属于本场考试",
        )

    answers = _normalize_answers(exam.answers)
    answers[str(payload.question_id)] = [
        str(item) for item in payload.selected
    ]
    exam.answers = answers
    db.commit()

    answered = sum(1 for value in answers.values() if value)
    return {"saved": True, "answered": answered, "total": exam.total}


@router.post("/exam/{exam_id}/submit")
def submit_exam(
    exam_id: int,
    payload: Optional[SubmitExamRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """交卷并判分；重复交卷幂等返回成绩摘要。"""
    exam = _get_exam_for_user(db, exam_id, current_user)
    if exam.submitted_at is not None:
        return _exam_summary(db, exam)

    answers = _normalize_answers(exam.answers)
    if payload is not None and payload.answers:
        for question_id, selected in payload.answers.items():
            answers[str(question_id)] = [str(item) for item in selected]
    exam.answers = answers

    _grade_exam(db, exam)
    return _exam_summary(db, exam)


@router.get("/exam/{exam_id}/result")
def get_exam_result(
    exam_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    """返回考试成绩、章节正确率与错题明细。"""
    exam = _get_exam_for_user(db, exam_id, current_user)
    _auto_submit_if_timeout(db, exam)
    if exam.submitted_at is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="考试尚未交卷",
        )

    question_ids = _exam_question_ids(exam)
    questions = (
        db.query(Question).filter(Question.id.in_(question_ids)).all()
        if question_ids
        else []
    )
    question_map = {question.id: question for question in questions}
    chapter_ids = {
        question.chapter_id
        for question in questions
        if question.chapter_id is not None
    }
    chapters = (
        db.query(Chapter).filter(Chapter.id.in_(chapter_ids)).all()
        if chapter_ids
        else []
    )
    chapter_map = {chapter.id: chapter for chapter in chapters}
    answers = _normalize_answers(exam.answers)

    chapter_groups: dict[Optional[int], dict] = {}
    wrong_items: list[dict] = []
    for question_id in question_ids:
        question = question_map.get(question_id)
        if question is None:
            continue
        chapter = chapter_map.get(question.chapter_id)
        chapter_name = chapter.name if chapter is not None else "未分类"
        group = chapter_groups.get(question.chapter_id)
        if group is None:
            group = {
                "chapter_id": question.chapter_id,
                "chapter_name": chapter_name,
                "total": 0,
                "correct": 0,
                "accuracy": 0.0,
            }
            chapter_groups[question.chapter_id] = group

        group["total"] += 1
        key = str(question_id)
        if key not in answers:
            continue
        selected = answers[key]
        if _answer_correct(question, selected):
            group["correct"] += 1
        else:
            wrong_items.append(
                {
                    "question": question_with_answer(
                        question, chapter_name=chapter_name
                    ),
                    "selected": selected,
                }
            )

    for group in chapter_groups.values():
        total = group["total"]
        group["accuracy"] = (
            round(group["correct"] / total * 100, 1) if total else 0.0
        )

    pass_score, total_score = _score_settings(
        db, current_user.province_code
    )
    return {
        "exam": {
            "id": exam.id,
            "score": exam.score,
            "passed": bool(exam.passed),
            "total": exam.total,
            "started_at": exam.started_at.isoformat(),
            "submitted_at": (
                exam.submitted_at.isoformat()
                if exam.submitted_at
                else None
            ),
            "used_seconds": _used_seconds(exam),
            "duration_limit_sec": exam.duration_limit_sec,
            "pass_score": pass_score,
            "total_score": total_score,
        },
        "chapters": list(chapter_groups.values()),
        "wrong_items": wrong_items,
    }
