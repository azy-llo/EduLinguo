from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, session, url_for
from sqlalchemy import func, inspect, select
from werkzeug.security import check_password_hash, generate_password_hash

from sqlalchemy.exc import IntegrityError

from models import Exercise, Lesson, Level, User, UserExerciseCompletion, UserLevelProgress, db
from seed_curriculum import refresh_grammar_lessons, refresh_grammar_theory, seed_full_curriculum

from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_login import LoginManager, UserMixin, login_required, current_user, login_user, logout_user
from flask import abort, redirect, url_for, request, session, flash
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-change-me-in-production")

# Настройка для работы с PostgreSQL на сервере
database_url = os.environ.get('DATABASE_URL')
if database_url and database_url.startswith("postgres://"):
    database_url = database_url.replace("postgres://", "postgresql://", 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url or 'sqlite:///lingualeap.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

from flask_login import LoginManager, login_required, current_user, login_user, logout_user

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

from flask_admin import AdminIndexView, expose
from flask import redirect, url_for

class AdminAuthView(AdminIndexView):
    @expose('/')
    def index(self):
        if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
            return redirect(url_for('admin_login'))
        return super().index()

admin = Admin(app, name='Управление EduLinguo', index_view=AdminAuthView())

class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and getattr(current_user, 'is_admin', False)
    
    def inaccessible_callback(self, name, **kwargs):
        return redirect(url_for('admin_login'))

# Пользователи
class UserAdmin(SecureModelView):
    column_list = ('id', 'username', 'email', 'xp', 'streak', 'is_admin', 'created_at')
    column_searchable_list = ('username', 'email')
    column_filters = ('is_admin', 'xp')
    form_columns = ('username', 'email', 'xp', 'streak', 'is_admin')

# Уровни
class LevelAdmin(SecureModelView):
    column_list = ('code', 'title', 'description', 'sort_order')
    form_columns = ('code', 'title', 'description', 'sort_order')

# Уроки
class LessonAdmin(SecureModelView):
    column_list = ('title', 'level', 'order_index', 'aspect', 'is_exam')
    column_searchable_list = ('title', 'theory')
    form_columns = ('level', 'order_index', 'aspect', 'title', 'theory', 'reading_passage', 'is_exam')

# Упражнения
class ExerciseAdmin(SecureModelView):
    column_list = ('id', 'lesson', 'order_index', 'kind', 'prompt')
    form_columns = ('lesson', 'order_index', 'kind', 'prompt', 'payload_json')

admin.add_view(UserAdmin(User, db.session))
admin.add_view(LevelAdmin(Level, db.session))
admin.add_view(LessonAdmin(Lesson, db.session))
admin.add_view(ExerciseAdmin(Exercise, db.session))

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = db.session.scalar(select(User).where(User.email == email))
        if user and check_password_hash(user.password_hash, password) and user.is_admin:
            login_user(user)
            return redirect(url_for('admin.index'))
        flash('Неверные данные или недостаточно прав')
    return render_template('admin_login.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('index'))

GUIDE_TOPICS = {
    "present-simple": {
        "title": "Present Simple",
        "level": "A1",
        "body": [
            "Используется для регулярных действий, фактов и расписаний.",
            "Формула: Subject + Verb (V1). Для he/she/it добавляем -s/-es.",
            "Отрицание: do not / does not + V1.",
            "Вопрос: Do/Does + subject + V1?",
            "Маркерные слова: always, usually, often, sometimes, never, every day.",
        ],
    },
    "verb-to-be": {
        "title": "Verb to be",
        "level": "A1",
        "body": [
            "Формы: am, is, are. Выбор зависит от подлежащего.",
            "I am, you are, he/she/it is, we/they are.",
            "Отрицание: am not, is not (isn't), are not (aren't).",
            "Вопрос: Am I? / Is he? / Are they?",
            "To be часто используется в описаниях, возрасте, профессии, состоянии.",
        ],
    },
    "articles": {
        "title": "Articles a / an / the",
        "level": "A1-A2",
        "body": [
            "A/An — для исчисляемого существительного в единственном числе впервые.",
            "An используется перед гласным звуком: an apple.",
            "The — когда предмет уже известен или единственный в контексте.",
            "Нулевой артикль часто с множественным числом и неисчисляемыми существительными.",
        ],
    },
    "past-simple": {
        "title": "Past Simple",
        "level": "A2",
        "body": [
            "Используется для завершенного действия в прошлом.",
            "Regular verbs: V2 = verb + ed (worked, played).",
            "Irregular verbs имеют отдельную форму: go-went, have-had, see-saw.",
            "Отрицание/вопрос: did not / Did + V1.",
        ],
    },
    "present-perfect": {
        "title": "Present Perfect",
        "level": "B1",
        "body": [
            "Связь прошлого с настоящим: опыт, результат, действие до сейчас.",
            "Формула: have/has + V3.",
            "Маркерные слова: ever, never, already, yet, just, since, for.",
            "Важно отличать от Past Simple: когда время действия в прошлом указано явно, чаще Past Simple.",
        ],
    },
    "conditionals": {
        "title": "Conditionals (1st/2nd/3rd)",
        "level": "B1-B2",
        "body": [
            "1st conditional: If + Present, will + V1 (реальный будущий результат).",
            "2nd conditional: If + Past Simple, would + V1 (маловероятная/воображаемая ситуация).",
            "3rd conditional: If + Past Perfect, would have + V3 (сожаление о прошлом).",
        ],
    },
}


def current_user():
    uid = session.get("user_id")
    if not uid:
        return None
    return db.session.get(User, uid)


def _guest_lessons_done() -> set[int]:
    raw = session.get("guest_lessons_done") or []
    return set(raw) if isinstance(raw, list) else set()


def _guest_exams_done() -> set[int]:
    raw = session.get("guest_exams_done") or []
    return set(raw) if isinstance(raw, list) else set()


def _set_guest_lesson(lesson_id: int):
    s = _guest_lessons_done()
    s.add(lesson_id)
    session["guest_lessons_done"] = list(s)
    session.modified = True


def _set_guest_exam(level_id: int):
    s = _guest_exams_done()
    s.add(level_id)
    session["guest_exams_done"] = list(s)
    session.modified = True


def user_passed_level_exam(user_id: int, level_id: int) -> bool:
    row = db.session.scalar(
        select(UserLevelProgress).where(
            UserLevelProgress.user_id == user_id,
            UserLevelProgress.level_id == level_id,
        )
    )
    return row is not None


def guest_passed_level_exam(level_id: int) -> bool:
    return level_id in _guest_exams_done()


def level_unlocked_for(user: User | None, level: Level) -> bool:
    if level.sort_order <= 1:
        return True
    prev = db.session.scalar(select(Level).where(Level.sort_order == level.sort_order - 1))
    if not prev:
        return True
    if user:
        return user_passed_level_exam(user.id, prev.id)
    return guest_passed_level_exam(prev.id)


def lesson_fully_completed_user(user_id: int, lesson_id: int) -> bool:
    ex_ids = db.session.scalars(select(Exercise.id).where(Exercise.lesson_id == lesson_id)).all()
    if not ex_ids:
        return False
    n = db.session.scalar(
        select(func.count())
        .select_from(UserExerciseCompletion)
        .where(
            UserExerciseCompletion.user_id == user_id,
            UserExerciseCompletion.exercise_id.in_(ex_ids),
        )
    )
    return int(n or 0) >= len(ex_ids)


def lesson_fully_completed_guest(lesson_id: int) -> bool:
    return lesson_id in _guest_lessons_done()


def lesson_completed(user: User | None, lesson_id: int) -> bool:
    if user:
        return lesson_fully_completed_user(user.id, lesson_id)
    return lesson_fully_completed_guest(lesson_id)


def can_access_lesson(user: User | None, lesson: Lesson) -> bool:
    return True
    # level_obj = db.session.get(Level, lesson.level_id)
    # if not level_obj:
    #     return False
    # if not level_unlocked_for(user, level_obj):
    #     return False
    # if lesson.is_exam:
    #     need = 50
    #     done_regular = 0
    #     for o in range(1, 51):
    #         les = db.session.scalar(
    #             select(Lesson).where(Lesson.level_id == lesson.level_id, Lesson.order_index == o)
    #         )
    #         if les and lesson_completed(user, les.id):
    #             done_regular += 1
    #     if done_regular < need:
    #         return False
    #     return True
    # if lesson.order_index <= 1:
    #     return True
    # prev = db.session.scalar(
    #     select(Lesson).where(
    #         Lesson.level_id == lesson.level_id,
    #         Lesson.order_index == lesson.order_index - 1,
    #     )
    # )
    # if not prev:
    #     return True
    # return lesson_completed(user, prev.id)


def maybe_award_level_exam(user_id: int, lesson: Lesson) -> None:
    if not lesson.is_exam:
        return
    if user_passed_level_exam(user_id, lesson.level_id):
        return
    if not lesson_fully_completed_user(user_id, lesson.id):
        return
    db.session.add(
        UserLevelProgress(
            user_id=user_id,
            level_id=lesson.level_id,
            exam_passed_at=datetime.now(timezone.utc),
        )
    )
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()


def maybe_award_level_exam_guest(lesson: Lesson) -> None:
    if not lesson.is_exam:
        return
    if guest_passed_level_exam(lesson.level_id):
        return
    _set_guest_exam(lesson.level_id)


def score_writing(text: str, payload: dict) -> int:
    text = (text or "").strip()
    if not text:
        return 0
    words = re.findall(r"[A-Za-z']+", text)
    n_words = len(words)
    min_w = int(payload.get("min_words") or 40)
    score = 0
    if n_words >= min_w:
        score += 45
    elif n_words >= max(5, min_w // 2):
        score += 25
    else:
        score += 10
    lower = text.lower()
    keys = payload.get("keywords") or []
    hit = sum(1 for k in keys if k.lower() in lower)
    if keys:
        score += min(40, int(40 * hit / len(keys)))
    else:
        score += 20
    if len(text) > 400:
        score += 5
    return min(100, score)


def first_lesson_url() -> str:
    level = db.session.scalar(select(Level).where(Level.sort_order == 1))
    if not level:
        return url_for("learn")
    lesson = db.session.scalar(
        select(Lesson).where(Lesson.level_id == level.id, Lesson.order_index == 1)
    )
    if not lesson:
        return url_for("learn")
    return url_for("lesson_view", lesson_id=lesson.id)


def continue_lesson_url(user: User | None) -> str:
    if not user:
        return first_lesson_url()
    levels = db.session.scalars(select(Level).order_by(Level.sort_order)).all()
    all_lessons: list[Lesson] = []
    for level in levels:
        lessons = db.session.scalars(
            select(Lesson)
            .where(Lesson.level_id == level.id)
            .order_by(Lesson.order_index)
        ).all()
        all_lessons.extend(lessons)
    if not all_lessons:
        return url_for("learn")
    for lesson in all_lessons:
        if can_access_lesson(user, lesson) and not lesson_completed(user, lesson.id):
            return url_for("lesson_view", lesson_id=lesson.id)
    last_done = None
    for lesson in all_lessons:
        if lesson_completed(user, lesson.id):
            last_done = lesson
    if last_done:
        return url_for("lesson_view", lesson_id=last_done.id)
    return first_lesson_url()


@app.route("/")
def index():
    user = current_user()
    return render_template(
        "index.html",
        first_lesson_url=first_lesson_url(),
        continue_lesson_url=continue_lesson_url(user),
    )


@app.route("/skip-auth")
def skip_auth():
    return redirect(url_for("learn"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        username = (request.form.get("username") or "").strip()
        password = request.form.get("password") or ""
        if not email or not username or len(password) < 6:
            flash("Заполните поля. Пароль — не короче 6 символов.", "error")
            return redirect(url_for("register"))
        if db.session.scalar(select(User).where(User.email == email)):
            flash("Этот email уже зарегистрирован.", "error")
            return redirect(url_for("register"))
        user = User(
            email=email,
            username=username,
            password_hash=generate_password_hash(password),
            xp=0,
            streak=0,
            created_at=datetime.now(timezone.utc),
        )
        db.session.add(user)
        db.session.commit()
        session["user_id"] = user.id
        flash("Добро пожаловать!", "success")
        return redirect(url_for("dashboard"))
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        user = db.session.scalar(select(User).where(User.email == email))
        if not user or not check_password_hash(user.password_hash, password):
            flash("Неверный email или пароль.", "error")
            return redirect(url_for("login"))
        session["user_id"] = user.id
        flash("С возвращением!", "success")
        return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user_id", None)
    flash("Вы вышли из аккаунта.", "success")
    return redirect(url_for("index"))


@app.route("/dashboard")
def dashboard():
    user = current_user()
    if user:
        done = db.session.scalar(
            select(func.count()).select_from(UserExerciseCompletion).where(
                UserExerciseCompletion.user_id == user.id
            )
        )
        return render_template("dashboard.html", user=user, exercises_done=int(done or 0))
    return render_template("dashboard_guest.html")


@app.route("/guide")
def guide():
    topics = [
        ("present-simple", "Present Simple", "A1"),
        ("verb-to-be", "Verb to be", "A1"),
        ("articles", "Articles a/an/the", "A1-A2"),
        ("past-simple", "Past Simple", "A2"),
        ("present-perfect", "Present Perfect", "B1"),
        ("conditionals", "Conditionals", "B1-B2"),
    ]
    return render_template("guide.html", topics=topics)


@app.route("/guide/<slug>")
def guide_topic(slug: str):
    topic = GUIDE_TOPICS.get(slug)
    if not topic:
        flash("Тема справочника не найдена.", "error")
        return redirect(url_for("guide"))
    return render_template("guide_topic.html", topic=topic)


@app.route("/leaderboard")
def leaderboard():
    users = db.session.scalars(select(User).order_by(User.xp.desc(), User.id.asc())).all()
    top3 = users[:3]
    rest = users[3:]
    return render_template("leaderboard.html", top3=top3, rest=rest)


@app.route("/profile", methods=["GET", "POST"])
def profile():
    user = current_user()
    if not user:
        flash("Войдите, чтобы открыть профиль.", "error")
        return redirect(url_for("login"))
    if request.method == "POST":
        username = (request.form.get("username") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        new_password = (request.form.get("password") or "").strip()
        if not username or not email:
            flash("Имя и почта обязательны.", "error")
            return redirect(url_for("profile"))
        exists = db.session.scalar(
            select(User).where(User.email == email, User.id != user.id)
        )
        if exists:
            flash("Эта почта уже используется.", "error")
            return redirect(url_for("profile"))
        user.username = username
        user.email = email
        if new_password:
            if len(new_password) < 6:
                flash("Новый пароль должен быть не короче 6 символов.", "error")
                return redirect(url_for("profile"))
            user.password_hash = generate_password_hash(new_password)
        db.session.commit()
        flash("Профиль обновлен.", "success")
        return redirect(url_for("profile"))
    return render_template("profile.html", user=user)


@app.route("/courses")
def courses_redirect():
    return redirect(url_for("learn"))


@app.route("/learn")
def learn():
    user = current_user()
    levels = db.session.scalars(select(Level).order_by(Level.sort_order)).all()
    items = []
    for lv in levels:
        items.append(
            {
                "level": lv,
                "unlocked": level_unlocked_for(user, lv),
                "exam_passed": (
                    user_passed_level_exam(user.id, lv.id) if user else guest_passed_level_exam(lv.id)
                ),
            }
        )
    sidebar_levels = [
        {"lv": lv, "unlocked": level_unlocked_for(user, lv), "active": False}
        for lv in levels
    ]
    return render_template(
        "learn.html",
        level_items=items,
        user=user,
        sidebar_levels=sidebar_levels,
    )


@app.route("/learn/<int:level_id>")
def level_view(level_id):
    user = current_user()
    level = db.session.get(Level, level_id)
    if not level:
        flash("Уровень не найден.", "error")
        return redirect(url_for("learn"))
    if not level_unlocked_for(user, level):
        flash("Сначала сдайте экзамен предыдущего уровня.", "error")
        return redirect(url_for("learn"))
    lessons = db.session.scalars(
        select(Lesson).where(Lesson.level_id == level_id).order_by(Lesson.order_index)
    ).all()
    levels = db.session.scalars(select(Level).order_by(Level.sort_order)).all()
    lesson_rows = []
    for les in lessons:
        ex_n = db.session.scalar(
            select(func.count()).select_from(Exercise).where(Exercise.lesson_id == les.id)
        )
        lesson_rows.append(
            {
                "lesson": les,
                "exercise_count": int(ex_n or 0),
                "accessible": can_access_lesson(user, les),
                "done": lesson_completed(user, les.id),
            }
        )
    sidebar_levels = [
        {"lv": lv, "unlocked": level_unlocked_for(user, lv), "active": lv.id == level_id}
        for lv in levels
    ]
    return render_template(
        "level_view.html",
        level=level,
        lesson_rows=lesson_rows,
        levels=levels,
        sidebar_levels=sidebar_levels,
        user=user,
    )


@app.route("/lesson/<int:lesson_id>")
def lesson_view(lesson_id):
    user = current_user()
    lesson = db.session.get(Lesson, lesson_id)
    if not lesson:
        abort(404)
    if not can_access_lesson(user, lesson):
        flash("Сначала завершите предыдущий урок или откройте уровень.", "error")
        return redirect(url_for("level_view", level_id=lesson.level_id))

    level = db.session.get(Level, lesson.level_id)
    levels = db.session.scalars(select(Level).order_by(Level.sort_order)).all()
    lessons = db.session.scalars(
        select(Lesson).where(Lesson.level_id == lesson.level_id).order_by(Lesson.order_index)
    ).all()
    lesson_rows = []
    for les in lessons:
        ex_n = db.session.scalar(
            select(func.count()).select_from(Exercise).where(Exercise.lesson_id == les.id)
        )
        lesson_rows.append(
            {
                "lesson": les,
                "exercise_count": int(ex_n or 0),
                "accessible": can_access_lesson(user, les),
                "done": lesson_completed(user, les.id),
            }
        )

    exercises = db.session.scalars(
        select(Exercise).where(Exercise.lesson_id == lesson_id).order_by(Exercise.order_index)
    ).all()
    exercise_ids = [e.id for e in exercises]
    completed_ids: list[int] = []
    if user and exercise_ids:
        rows = db.session.scalars(
            select(UserExerciseCompletion.exercise_id).where(
                UserExerciseCompletion.user_id == user.id,
                UserExerciseCompletion.exercise_id.in_(exercise_ids),
            )
        ).all()
        done_set = set(rows)
        completed_ids = [eid for eid in exercise_ids if eid in done_set]
    exercises_data = [
        {"id": e.id, "kind": e.kind, "prompt": e.prompt, "payload": e.payload()} for e in exercises
    ]
    sidebar_levels = [
        {"lv": lv, "unlocked": level_unlocked_for(user, lv), "active": lv.id == lesson.level_id}
        for lv in levels
    ]
    return render_template(
        "lesson.html",
        lesson=lesson,
        level=level,
        levels=levels,
        lesson_rows=lesson_rows,
        sidebar_levels=sidebar_levels,
        exercises_json=json.dumps(exercises_data, ensure_ascii=False),
        exercises_count=len(exercises),
        completed_ids_json=json.dumps(completed_ids),
        user=user,
        logged_in=bool(user),
    )


@app.post("/api/exercise/<int:exercise_id>/complete")
def api_complete_exercise(exercise_id):
    user = current_user()
    if not user:
        return jsonify({"ok": False, "reason": "guest"}), 403
    ex = db.session.get(Exercise, exercise_id)
    if not ex:
        return jsonify({"ok": False, "reason": "missing"}), 404
    exists = db.session.scalar(
        select(UserExerciseCompletion).where(
            UserExerciseCompletion.user_id == user.id,
            UserExerciseCompletion.exercise_id == exercise_id,
        )
    )
    if exists:
        return jsonify({"ok": True, "xp": user.xp, "already": True})
    db.session.add(
        UserExerciseCompletion(
            user_id=user.id,
            exercise_id=exercise_id,
            completed_at=datetime.now(timezone.utc),
        )
    )
    user.xp = (user.xp or 0) + 10
    db.session.commit()
    les = db.session.get(Lesson, ex.lesson_id)
    if les and lesson_fully_completed_user(user.id, les.id):
        maybe_award_level_exam(user.id, les)
    return jsonify({"ok": True, "xp": user.xp, "already": False})


@app.post("/api/exercise/<int:exercise_id>/writing")
def api_writing_submit(exercise_id):
    user = current_user()
    if not user:
        return jsonify({"ok": False, "reason": "guest"}), 403
    ex = db.session.get(Exercise, exercise_id)
    if not ex or ex.kind != "writing":
        return jsonify({"ok": False}), 400
    data = request.get_json(silent=True) or {}
    text = data.get("text") or ""
    sc = score_writing(text, ex.payload())
    if sc < 50:
        return jsonify({"ok": True, "passed": False, "score": sc})
    exists = db.session.scalar(
        select(UserExerciseCompletion).where(
            UserExerciseCompletion.user_id == user.id,
            UserExerciseCompletion.exercise_id == exercise_id,
        )
    )
    if exists:
        return jsonify({"ok": True, "passed": True, "score": sc, "already": True})
    db.session.add(
        UserExerciseCompletion(
            user_id=user.id,
            exercise_id=exercise_id,
            completed_at=datetime.now(timezone.utc),
        )
    )
    user.xp = (user.xp or 0) + 10
    db.session.commit()
    les = db.session.get(Lesson, ex.lesson_id)
    if les and lesson_fully_completed_user(user.id, les.id):
        maybe_award_level_exam(user.id, les)
    return jsonify({"ok": True, "passed": True, "score": sc})


@app.post("/api/guest/lesson-complete")
def api_guest_lesson_complete():
    data = request.get_json(silent=True) or {}
    lid = int(data.get("lesson_id") or 0)
    lesson = db.session.get(Lesson, lid)
    if not lesson:
        return jsonify({"ok": False}), 400
    user = current_user()
    if user:
        return jsonify({"ok": False}), 400
    _set_guest_lesson(lid)
    if lesson.is_exam:
        maybe_award_level_exam_guest(lesson)
    return jsonify({"ok": True})


@app.context_processor
def inject_user():
    return {"current_user": current_user()}


def _migrate_legacy_schema() -> None:
    """Старые версии использовали courses/ course_id — пересоздаём схему один раз."""
    try:
        insp = inspect(db.engine)
        names = insp.get_table_names()
        if "lessons" not in names:
            return
        cols = {c["name"] for c in insp.get_columns("lessons")}
        if "course_id" in cols and "level_id" not in cols:
            db.drop_all()
    except Exception:
        pass


with app.app_context():
    db.create_all()
    _migrate_legacy_schema()
    db.create_all()
    seed_full_curriculum()
    refresh_grammar_theory()
    refresh_grammar_lessons()

@app.route('/setup_admin')
def setup_admin():
    from sqlalchemy import text
    # Добавляем колонку is_admin, если её ещё нет
    try:
        db.session.execute(text('ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;'))
        db.session.commit()
    except Exception as e:
        if 'duplicate column' not in str(e).lower():
            return f"Ошибка: {e}"
    # Назначаем текущего пользователя админом
    user = current_user()
    if not user:
        return "Вы не залогинены. <a href='/login'>Войдите</a> сначала."
    user.is_admin = True
    db.session.commit()
    return f"✅ Пользователь {user.email} (ID: {user.id}) теперь администратор! Теперь удалите этот маршрут."

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
