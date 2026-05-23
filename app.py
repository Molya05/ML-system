import ast
import json
import os
import secrets
import sqlite3
import subprocess
import sys
import textwrap
import time
from datetime import datetime
from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
DATABASE_PATH = BASE_DIR / "lms.db"
LAB_ROOT = BASE_DIR / "user_labs"
ALLOWED_LANGS = {"en", "ru", "kz"}
STAGES = ["theory", "test", "practice", "homework"]
ROLE_CHOICES = ("student", "teacher")
SAFE_IMPORTS = {
    "math",
    "random",
    "statistics",
    "json",
    "csv",
    "datetime",
    "itertools",
    "functools",
    "collections",
    "pathlib",
    "matplotlib",
    "numpy",
}
BLOCKED_CALL_NAMES = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "globals",
    "locals",
    "vars",
}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")
app.config["MAX_CONTENT_LENGTH"] = 8 * 1024 * 1024


TRANSLATIONS = {
    "en": {
        "app_title": "NovaMind LMS",
        "login_title": "Adaptive AI Learning Platform",
        "login_subtitle": "15 modules, strict progression, integrated lab",
        "username": "Username",
        "password": "Password",
        "sign_in": "Sign in",
        "register": "Register",
        "create_account": "Create account",
        "already_have_account": "Already have an account?",
        "need_account": "Need an account?",
        "full_name": "Full name",
        "confirm_password": "Confirm password",
        "role": "Role",
        "student_role": "Student",
        "teacher_role": "Teacher",
        "register_subtitle": "Create a learner or teacher account with secure password hashing.",
        "go_to_login": "Go to login",
        "go_to_register": "Go to register",
        "menu": "Menu",
        "logout": "Logout",
        "dashboard": "Dashboard",
        "my_courses": "My Courses",
        "manage_courses": "Manage Courses",
        "courses": "Courses",
        "course": "Course",
        "course_title": "Course title",
        "course_description": "Course description",
        "create_course": "Create course",
        "edit_course": "Edit course",
        "available_courses": "Available courses",
        "enrolled_courses": "Enrolled courses",
        "enroll": "Enroll",
        "enrolled": "Enrolled",
        "access_denied": "Access denied",
        "course_modules": "Course modules",
        "assign_modules": "Assign modules",
        "save_course": "Save course",
        "view_course": "View course",
        "students_enrolled": "Students enrolled",
        "course_submissions": "Course submissions",
        "submission_history": "Submission history",
        "grade": "Grade",
        "comment": "Comment",
        "save_grade": "Save grade",
        "manage_course_subtitle": "Create courses, assign modules, and review enrolled learners.",
        "my_courses_subtitle": "Enroll in courses to unlock their modules and assignments.",
        "not_enrolled_message": "You must enroll in this course before accessing its modules.",
        "module_locked_by_course": "This module is locked until you enroll in its course.",
        "teacher_owner": "Teacher",
        "no_courses": "No courses available yet.",
        "module_count": "Modules",
        "course_progress": "Course progress",
        "view_students": "View students",
        "modules": "Modules",
        "teacher_panel": "Teacher Panel",
        "history": "History",
        "progress": "Progress",
        "current_stage": "Current stage",
        "locked": "Locked",
        "unlocked": "Unlocked",
        "theory": "Theory",
        "test": "Test",
        "practice": "Practical assignment",
        "homework": "Homework",
        "complete_theory": "Mark theory as completed",
        "submit_test": "Submit test",
        "submit_practice": "Submit practice",
        "submit_homework": "Submit homework",
        "complete_homework": "Complete homework",
        "run_code": "Run code",
        "stdin": "Program input",
        "test_locked_message": "The test is locked until theory is completed.",
        "upload_file": "Upload file",
        "download": "Download",
        "lab": "Code Lab",
        "output": "Output",
        "error_output": "Errors",
        "files": "Files",
        "artifacts": "Artifacts",
        "ai_tutor": "AI Tutor",
        "ask_ai": "Ask AI tutor",
        "admin_tools": "Admin tools",
        "save_changes": "Save changes",
        "student_overview": "Student overview",
        "language": "Language",
        "welcome": "Welcome back",
        "module_status": "Module status",
        "your_path": "Your adaptive learning path",
        "practical_prompt": "Describe your practical work or add results from the lab.",
        "homework_prompt": "Submit your homework reflection, solution, or summary.",
        "test_feedback": "Test feedback",
        "practice_feedback": "Practice feedback",
        "homework_feedback": "Homework feedback",
        "load_test": "Load test",
        "no_files": "No files uploaded yet",
        "score_label": "Score",
        "passed_message": "Passed. Practice unlocked.",
        "failed_message": "Not passed. Review the explanations below.",
        "choose_file_first": "Choose a file first.",
        "module_complete": "Complete",
        "edit_content": "Edit content, tests, and assignments",
        "modules_completed": "modules completed",
        "history_title": "Learning history",
        "history_subtitle": "Review completed modules, test attempts, and prior submissions.",
        "filter_module": "Filter by module",
        "all_modules": "All modules",
        "completed_modules_label": "Completed modules",
        "test_history": "Test results",
        "practice_history": "Practice history",
        "homework_history": "Homework history",
        "submitted_at": "Submitted at",
        "attempt_result": "Result",
        "view_submission": "View submission",
        "no_history": "No history yet for this filter.",
    },
    "ru": {
        "app_title": "NovaMind LMS",
        "login_title": "Адаптивная AI-платформа обучения",
        "login_subtitle": "15 модулей, строгая последовательность, встроенная лаборатория",
        "username": "Логин",
        "password": "Пароль",
        "sign_in": "Войти",
        "register": "Регистрация",
        "create_account": "Создать аккаунт",
        "already_have_account": "Уже есть аккаунт?",
        "need_account": "Нужен аккаунт?",
        "full_name": "Полное имя",
        "confirm_password": "Подтвердите пароль",
        "role": "Роль",
        "student_role": "Студент",
        "teacher_role": "Преподаватель",
        "register_subtitle": "Создайте аккаунт студента или преподавателя с безопасным хешированием пароля.",
        "go_to_login": "Перейти ко входу",
        "go_to_register": "Перейти к регистрации",
        "menu": "Меню",
        "logout": "Выйти",
        "dashboard": "Панель",
        "my_courses": "Мои курсы",
        "manage_courses": "Управление курсами",
        "courses": "Курсы",
        "course": "Курс",
        "course_title": "Название курса",
        "course_description": "Описание курса",
        "create_course": "Создать курс",
        "edit_course": "Редактировать курс",
        "available_courses": "Доступные курсы",
        "enrolled_courses": "Мои курсы",
        "enroll": "Записаться",
        "enrolled": "Записан",
        "access_denied": "Доступ запрещен",
        "course_modules": "Модули курса",
        "assign_modules": "Назначить модули",
        "save_course": "Сохранить курс",
        "view_course": "Открыть курс",
        "students_enrolled": "Записанные студенты",
        "course_submissions": "Отправки по курсу",
        "submission_history": "История отправок",
        "grade": "Оценка",
        "comment": "Комментарий",
        "save_grade": "Сохранить оценку",
        "manage_course_subtitle": "Создавайте курсы, назначайте модули и просматривайте студентов.",
        "my_courses_subtitle": "Запишитесь на курс, чтобы открыть его модули и задания.",
        "not_enrolled_message": "Сначала нужно записаться на курс, чтобы открыть его модули.",
        "module_locked_by_course": "Модуль будет доступен после записи на курс.",
        "teacher_owner": "Преподаватель",
        "no_courses": "Курсы пока не созданы.",
        "module_count": "Модули",
        "course_progress": "Прогресс по курсу",
        "view_students": "Просмотр студентов",
        "modules": "Модули",
        "teacher_panel": "Панель преподавателя",
        "history": "История",
        "progress": "Прогресс",
        "current_stage": "Текущий этап",
        "locked": "Заблокирован",
        "unlocked": "Открыт",
        "theory": "Теория",
        "test": "Тест",
        "practice": "Практика",
        "homework": "Домашняя работа",
        "complete_theory": "Отметить теорию как завершенную",
        "submit_test": "Отправить тест",
        "submit_practice": "Отправить практику",
        "submit_homework": "Отправить домашнюю работу",
        "complete_homework": "Завершить домашнюю работу",
        "run_code": "Запустить код",
        "stdin": "Входные данные программы",
        "test_locked_message": "Тест будет доступен после завершения теории.",
        "upload_file": "Загрузить файл",
        "download": "Скачать",
        "lab": "Code Lab",
        "output": "Вывод",
        "error_output": "Ошибки",
        "files": "Файлы",
        "artifacts": "Артефакты",
        "ai_tutor": "AI-тьютор",
        "ask_ai": "Спросить AI-тьютора",
        "admin_tools": "Инструменты администратора",
        "save_changes": "Сохранить изменения",
        "student_overview": "Обзор студентов",
        "language": "Язык",
        "welcome": "С возвращением",
        "module_status": "Статус модуля",
        "your_path": "Ваш адаптивный учебный маршрут",
        "practical_prompt": "Опишите практическую работу или добавьте результаты из лаборатории.",
        "homework_prompt": "Отправьте домашнюю работу, решение или краткое резюме.",
        "test_feedback": "Обратная связь по тесту",
        "practice_feedback": "Обратная связь по практике",
        "homework_feedback": "Обратная связь по домашней работе",
        "load_test": "Загрузить тест",
        "no_files": "Файлы пока не загружены",
        "score_label": "Результат",
        "passed_message": "Тест пройден. Практика открыта.",
        "failed_message": "Тест не пройден. Проверьте объяснения ниже.",
        "choose_file_first": "Сначала выберите файл.",
        "module_complete": "Завершен",
        "edit_content": "Редактировать контент, тесты и задания",
        "modules_completed": "модулей завершено",
        "history_title": "История обучения",
        "history_subtitle": "Просматривайте завершенные модули, результаты тестов и прошлые отправки.",
        "filter_module": "Фильтр по модулю",
        "all_modules": "Все модули",
        "completed_modules_label": "Завершенные модули",
        "test_history": "Результаты тестов",
        "practice_history": "История практики",
        "homework_history": "История домашней работы",
        "submitted_at": "Дата отправки",
        "attempt_result": "Результат",
        "view_submission": "Показать отправку",
        "no_history": "Для выбранного фильтра история пока отсутствует.",
    },
    "kz": {
        "app_title": "NovaMind LMS",
        "login_title": "AI негізіндегі бейімделмелі оқу платформасы",
        "login_subtitle": "15 модуль, қатаң реттілік, кіріктірілген зертхана",
        "username": "Пайдаланушы",
        "password": "Құпиясөз",
        "sign_in": "Кіру",
        "register": "Тіркелу",
        "create_account": "Тіркелгі жасау",
        "already_have_account": "Тіркелгіңіз бар ма?",
        "need_account": "Тіркелгі керек пе?",
        "full_name": "Толық аты-жөні",
        "confirm_password": "Құпиясөзді растау",
        "role": "Рөл",
        "student_role": "Студент",
        "teacher_role": "Оқытушы",
        "register_subtitle": "Қауіпсіз құпиясөз хэшімен студент не оқытушы тіркелгісін жасаңыз.",
        "go_to_login": "Кіру бетіне өту",
        "go_to_register": "Тіркелу бетіне өту",
        "menu": "Мәзір",
        "logout": "Шығу",
        "dashboard": "Басқару панелі",
        "my_courses": "Менің курстарым",
        "manage_courses": "Курстарды басқару",
        "courses": "Курстар",
        "course": "Курс",
        "course_title": "Курс атауы",
        "course_description": "Курс сипаттамасы",
        "create_course": "Курс құру",
        "edit_course": "Курсты өңдеу",
        "available_courses": "Қолжетімді курстар",
        "enrolled_courses": "Тіркелген курстар",
        "enroll": "Тіркелу",
        "enrolled": "Тіркелген",
        "access_denied": "Қолжетімділік жоқ",
        "course_modules": "Курс модульдері",
        "assign_modules": "Модульдерді бекіту",
        "save_course": "Курсты сақтау",
        "view_course": "Курсты ашу",
        "students_enrolled": "Тіркелген студенттер",
        "course_submissions": "Курс бойынша жіберімдер",
        "submission_history": "Жіберім тарихы",
        "grade": "Баға",
        "comment": "Пікір",
        "save_grade": "Бағаны сақтау",
        "manage_course_subtitle": "Курстар құрып, модульдерді бекітіп, студенттерді қадағалаңыз.",
        "my_courses_subtitle": "Модульдер мен тапсырмаларға қол жеткізу үшін курсқа тіркеліңіз.",
        "not_enrolled_message": "Модульдерді ашу үшін алдымен осы курсқа тіркелу керек.",
        "module_locked_by_course": "Бұл модуль курсқа тіркелгеннен кейін ашылады.",
        "teacher_owner": "Оқытушы",
        "no_courses": "Әзірге курс жоқ.",
        "module_count": "Модульдер",
        "course_progress": "Курс прогресі",
        "view_students": "Студенттерді көру",
        "modules": "Модульдер",
        "teacher_panel": "Оқытушы панелі",
        "history": "Тарих",
        "progress": "Прогресс",
        "current_stage": "Ағымдағы кезең",
        "locked": "Құлыпталған",
        "unlocked": "Ашық",
        "theory": "Теория",
        "test": "Тест",
        "practice": "Тәжірибелік тапсырма",
        "homework": "Үй жұмысы",
        "complete_theory": "Теория аяқталды деп белгілеу",
        "submit_test": "Тест жіберу",
        "submit_practice": "Практиканы жіберу",
        "submit_homework": "Үй жұмысын жіберу",
        "complete_homework": "Үй жұмысын аяқтау",
        "run_code": "Кодты іске қосу",
        "stdin": "Бағдарлама енгізуі",
        "test_locked_message": "Тест теория аяқталғаннан кейін ашылады.",
        "upload_file": "Файл жүктеу",
        "download": "Жүктеп алу",
        "lab": "Code Lab",
        "output": "Нәтиже",
        "error_output": "Қателер",
        "files": "Файлдар",
        "artifacts": "Артефактілер",
        "ai_tutor": "AI тәлімгер",
        "ask_ai": "AI тәлімгерден сұрау",
        "admin_tools": "Әкімші құралдары",
        "save_changes": "Өзгерістерді сақтау",
        "student_overview": "Студенттер көрінісі",
        "language": "Тіл",
        "welcome": "Қайта келдіңіз",
        "module_status": "Модуль күйі",
        "your_path": "Сіздің бейімделмелі оқу жолыңыз",
        "practical_prompt": "Практикалық жұмысты сипаттаңыз немесе зертхана нәтижесін қосыңыз.",
        "homework_prompt": "Үй жұмысының шешімін немесе қысқаша қорытындысын жіберіңіз.",
        "test_feedback": "Тест бойынша кері байланыс",
        "practice_feedback": "Практика бойынша кері байланыс",
        "homework_feedback": "Үй жұмысы бойынша кері байланыс",
        "load_test": "Тестті жүктеу",
        "no_files": "Файлдар әлі жүктелмеген",
        "score_label": "Ұпай",
        "passed_message": "Тест өтті. Практика ашылды.",
        "failed_message": "Тест өтпеді. Төмендегі түсіндірмелерді қараңыз.",
        "choose_file_first": "Алдымен файл таңдаңыз.",
        "module_complete": "Аяқталды",
        "edit_content": "Контентті, тесттерді және тапсырмаларды өңдеу",
        "modules_completed": "модуль аяқталды",
        "history_title": "Оқу тарихы",
        "history_subtitle": "Аяқталған модульдерді, тест нәтижелерін және алдыңғы жіберімдерді қараңыз.",
        "filter_module": "Модуль бойынша сүзгі",
        "all_modules": "Барлық модульдер",
        "completed_modules_label": "Аяқталған модульдер",
        "test_history": "Тест нәтижелері",
        "practice_history": "Практика тарихы",
        "homework_history": "Үй жұмысы тарихы",
        "submitted_at": "Жіберілген уақыты",
        "attempt_result": "Нәтиже",
        "view_submission": "Жіберімді көру",
        "no_history": "Бұл сүзгі үшін тарих әлі жоқ.",
    },
}


MODULE_TOPICS = [
    "AI Learning Foundations",
    "Python for Adaptive Systems",
    "Data Structures for Education",
    "Assessment Automation",
    "Feedback Loop Design",
    "Student Analytics",
    "Data Visualization",
    "Machine Learning Basics",
    "Prompt Engineering",
    "Personalized Learning Paths",
    "NLP for Tutoring",
    "Code Evaluation Pipelines",
    "Model Monitoring",
    "Ethics and Safety",
    "Capstone Integration",
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def t(key):
    lang = session.get("lang", "en")
    return TRANSLATIONS.get(lang, TRANSLATIONS["en"]).get(key, key)


app.jinja_env.globals["t"] = t


def app_texts():
    keys = [
        "load_test",
        "submit_test",
        "score_label",
        "passed_message",
        "failed_message",
        "choose_file_first",
        "download",
        "no_files",
        "error_output",
        "test_locked_message",
    ]
    return {key: t(key) for key in keys}


app.jinja_env.globals["app_texts"] = app_texts


def ensure_column(cursor, table_name, column_name, definition):
    columns = {row["name"] for row in cursor.execute(f"PRAGMA table_info({table_name})").fetchall()}
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}")


def normalize_language_code(code):
    value = (code or "").strip().lower()
    if value.startswith("ru"):
        return "ru"
    if value.startswith("kk") or value.startswith("kz"):
        return "kz"
    return "en"


def detect_request_language():
    header = request.headers.get("Accept-Language", "")
    for raw_part in header.split(","):
        lang_code = raw_part.split(";")[0].strip()
        normalized = normalize_language_code(lang_code)
        if normalized in ALLOWED_LANGS:
            return normalized
    return "en"


def ensure_schema(cursor):
    ensure_column(cursor, "users", "preferred_language", "TEXT DEFAULT 'en'")
    ensure_column(cursor, "users", "created_at", "TEXT DEFAULT CURRENT_TIMESTAMP")
    ensure_column(cursor, "modules", "course_id", "INTEGER")
    ensure_column(cursor, "practice_submissions", "score", "INTEGER")
    ensure_column(cursor, "practice_submissions", "teacher_comment", "TEXT")
    ensure_column(cursor, "homework_submissions", "teacher_comment", "TEXT")
    ensure_column(cursor, "progress_tracking", "completed_at", "TEXT")
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_progress_user_module ON progress_tracking(user_id, module_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_lab_logs_user_module ON lab_execution_logs(user_id, module_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_test_results_user_module ON test_results(user_id, module_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_modules_course_id ON modules(course_id)"
    )
    cursor.execute(
        "CREATE INDEX IF NOT EXISTS idx_enrollments_student_course ON enrollments(student_id, course_id)"
    )


def init_db():
    LAB_ROOT.mkdir(exist_ok=True)
    db = sqlite3.connect(DATABASE_PATH)
    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS roles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        );

        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            full_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            role_id INTEGER NOT NULL,
            preferred_language TEXT DEFAULT 'en',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (role_id) REFERENCES roles(id)
        );

        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY,
            sort_order INTEGER NOT NULL,
            title_en TEXT NOT NULL,
            title_ru TEXT NOT NULL,
            title_kz TEXT NOT NULL,
            summary_en TEXT NOT NULL,
            summary_ru TEXT NOT NULL,
            summary_kz TEXT NOT NULL,
            course_id INTEGER,
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );

        CREATE TABLE IF NOT EXISTS courses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            teacher_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (teacher_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS enrollments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            course_id INTEGER NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, course_id),
            FOREIGN KEY (student_id) REFERENCES users(id),
            FOREIGN KEY (course_id) REFERENCES courses(id)
        );

        CREATE TABLE IF NOT EXISTS lessons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER UNIQUE NOT NULL,
            theory_en TEXT NOT NULL,
            theory_ru TEXT NOT NULL,
            theory_kz TEXT NOT NULL,
            FOREIGN KEY (module_id) REFERENCES modules(id)
        );

        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER NOT NULL,
            question_en TEXT NOT NULL,
            question_ru TEXT NOT NULL,
            question_kz TEXT NOT NULL,
            options_json TEXT NOT NULL,
            correct_answer TEXT NOT NULL,
            explanation_en TEXT NOT NULL,
            explanation_ru TEXT NOT NULL,
            explanation_kz TEXT NOT NULL,
            FOREIGN KEY (module_id) REFERENCES modules(id)
        );

        CREATE TABLE IF NOT EXISTS assignments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            module_id INTEGER NOT NULL,
            stage_type TEXT NOT NULL,
            prompt_en TEXT NOT NULL,
            prompt_ru TEXT NOT NULL,
            prompt_kz TEXT NOT NULL,
            FOREIGN KEY (module_id) REFERENCES modules(id)
        );

        CREATE TABLE IF NOT EXISTS practice_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            module_id INTEGER NOT NULL,
            submission_text TEXT NOT NULL,
            ai_feedback TEXT NOT NULL,
            score INTEGER,
            teacher_comment TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (module_id) REFERENCES modules(id)
        );

        CREATE TABLE IF NOT EXISTS homework_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            module_id INTEGER NOT NULL,
            submission_text TEXT NOT NULL,
            ai_feedback TEXT NOT NULL,
            score INTEGER NOT NULL,
            teacher_comment TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (module_id) REFERENCES modules(id)
        );

        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            module_id INTEGER NOT NULL,
            score INTEGER NOT NULL,
            total INTEGER NOT NULL,
            passed INTEGER NOT NULL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (module_id) REFERENCES modules(id)
        );

        CREATE TABLE IF NOT EXISTS progress_tracking (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            module_id INTEGER NOT NULL,
            theory_completed INTEGER DEFAULT 0,
            test_completed INTEGER DEFAULT 0,
            practice_completed INTEGER DEFAULT 0,
            homework_completed INTEGER DEFAULT 0,
            module_completed INTEGER DEFAULT 0,
            completed_at TEXT,
            UNIQUE (user_id, module_id),
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (module_id) REFERENCES modules(id)
        );

        CREATE TABLE IF NOT EXISTS lab_execution_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            module_id INTEGER NOT NULL,
            code TEXT NOT NULL,
            stdout TEXT,
            stderr TEXT,
            status TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (module_id) REFERENCES modules(id)
        );
        """
    )
    ensure_schema(cursor)

    for role_name in ("admin", "teacher", "student"):
        cursor.execute("INSERT OR IGNORE INTO roles(name) VALUES (?)", (role_name,))

    role_map = {
        row["name"]: row["id"] for row in cursor.execute("SELECT id, name FROM roles").fetchall()
    }

    # Remove legacy seeded demo accounts so authentication relies only on real registered users.
    cursor.execute(
        """
        DELETE FROM users
        WHERE (username = 'admin' AND full_name = 'Platform Admin')
           OR (username = 'teacher' AND full_name = 'Lead Teacher')
           OR (username = 'student' AND full_name = 'Demo Student')
        """
    )

    for idx, topic in enumerate(MODULE_TOPICS, start=1):
        title_en = f"Module {idx}. {topic}"
        title_ru = f"Модуль {idx}. {topic}"
        title_kz = f"{idx}-модуль. {topic}"
        summary_en = f"Master {topic.lower()} through theory, test, practice, and homework."
        summary_ru = f"Освойте тему {topic.lower()} через теорию, тест, практику и домашнюю работу."
        summary_kz = f"{topic.lower()} бағытын теория, тест, практика және үй жұмысы арқылы меңгеріңіз."
        cursor.execute(
            """
            INSERT OR IGNORE INTO modules(
                id, sort_order, title_en, title_ru, title_kz, summary_en, summary_ru, summary_kz
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (idx, idx, title_en, title_ru, title_kz, summary_en, summary_ru, summary_kz),
        )

        theory_en = textwrap.dedent(
            f"""
            In {title_en}, learners build a structured understanding of {topic.lower()} within an AI-driven LMS.
            Focus on how content, assessment, and hands-on experimentation reinforce each other.
            Key ideas:
            1. Break complex learning goals into measurable steps.
            2. Use data and feedback to adapt instruction.
            3. Validate learning through tests, practical work, and reflective homework.
            Mini example:
            - Input: student performance history
            - Process: identify strengths and gaps
            - Output: next best learning activity
            """
        ).strip()
        theory_ru = textwrap.dedent(
            f"""
            В {title_ru} студент изучает тему {topic.lower()} в структуре AI-платформы.
            Важно связать контент, проверку знаний и практическую работу в единую учебную цепочку.
            Ключевые идеи:
            1. Делить цель обучения на измеримые шаги.
            2. Использовать данные и обратную связь для адаптации обучения.
            3. Подтверждать результат тестом, практикой и домашней работой.
            Мини-пример:
            - Вход: история успеваемости студента
            - Процесс: поиск сильных сторон и пробелов
            - Выход: следующая лучшая учебная активность
            """
        ).strip()
        theory_kz = textwrap.dedent(
            f"""
            {title_kz} бөлімінде студент {topic.lower()} тақырыбын AI платформасы контекстінде меңгереді.
            Контент, тексеру және тәжірибені біртұтас оқу ағымына біріктіру маңызды.
            Негізгі идеялар:
            1. Оқу мақсатын өлшенетін қадамдарға бөлу.
            2. Оқытуды бейімдеу үшін дерек пен кері байланысты пайдалану.
            3. Нәтижені тест, практика және үй жұмысы арқылы растау.
            Қысқа мысал:
            - Кіріс: студенттің үлгерім тарихы
            - Үдеріс: күшті және әлсіз жақтарын анықтау
            - Нәтиже: келесі тиімді оқу әрекеті
            """
        ).strip()
        cursor.execute(
            """
            INSERT OR IGNORE INTO lessons(module_id, theory_en, theory_ru, theory_kz)
            VALUES (?, ?, ?, ?)
            """,
            (idx, theory_en, theory_ru, theory_kz),
        )

        existing_tests = cursor.execute(
            "SELECT COUNT(*) FROM tests WHERE module_id = ?",
            (idx,),
        ).fetchone()[0]
        test_rows = [
            (
                f"What is the main goal of {topic.lower()} in this module?",
                f"Какова основная цель темы {topic.lower()} в этом модуле?",
                f"Бұл модульде {topic.lower()} тақырыбының негізгі мақсаты қандай?",
                json.dumps(
                    [
                        "Support structured learning decisions",
                        "Replace all teachers",
                        "Ignore student feedback",
                        "Avoid practical work",
                    ]
                ),
                "Support structured learning decisions",
                "The module emphasizes guided, measurable, data-informed learning decisions.",
                "Модуль подчеркивает управляемые и измеримые решения на основе данных.",
                "Модуль дерекке сүйенген құрылымды оқу шешімдерін қолдайды.",
            ),
            (
                "Which stage comes immediately after theory?",
                "Какой этап идет сразу после теории?",
                "Теориядан кейін бірден қай кезең келеді?",
                json.dumps(["Test", "Homework", "Practice", "Certification"]),
                "Test",
                "The platform enforces Theory → Test → Practice → Homework.",
                "Платформа строго соблюдает порядок Теория → Тест → Практика → Домашняя работа.",
                "Платформа Теория → Тест → Практика → Үй жұмысы тәртібін қатаң сақтайды.",
            ),
            (
                "Why is progress tracking essential?",
                "Почему отслеживание прогресса критично?",
                "Неліктен прогресті қадағалау маңызды?",
                json.dumps(
                    [
                        "It unlocks the next validated stage",
                        "It removes the need for assignments",
                        "It lets students skip modules",
                        "It disables feedback",
                    ]
                ),
                "It unlocks the next validated stage",
                "Progress data is used to enforce the sequence and personalize help.",
                "Данные прогресса нужны для соблюдения последовательности и персонализации помощи.",
                "Прогресс деректері реттілікті сақтау мен көмекті бейімдеу үшін қолданылады.",
            ),
            (
                "Which artifact is best suited for the integrated code lab?",
                "Какой артефакт лучше всего подходит для встроенной code lab?",
                "Кіріктірілген code lab үшін қай артефакт ең қолайлы?",
                json.dumps(["Python notebook-style script", "Printed poster", "Audio-only note", "Paper form"]),
                "Python notebook-style script",
                "The lab is designed around browser-based Python execution and outputs.",
                "Лаборатория рассчитана на запуск Python-кода в браузере и анализ результатов.",
                "Зертхана браузерде Python кодын іске қосуға және нәтижені қарауға арналған.",
            ),
        ]
        if existing_tests == 0:
            for row in test_rows:
                cursor.execute(
                    """
                    INSERT INTO tests(
                        module_id, question_en, question_ru, question_kz, options_json,
                        correct_answer, explanation_en, explanation_ru, explanation_kz
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (idx, *row),
                )

        existing_assignments = cursor.execute(
            "SELECT COUNT(*) FROM assignments WHERE module_id = ?",
            (idx,),
        ).fetchone()[0]
        assignments = [
            (
                "practice",
                f"Build a short Python experiment for {topic.lower()} and explain what the output means.",
                f"Соберите небольшой Python-эксперимент по теме {topic.lower()} и объясните результат.",
                f"{topic.lower()} бойынша шағын Python тәжірибесін жасап, нәтижесін түсіндіріңіз.",
            ),
            (
                "homework",
                f"Submit a reflective homework note showing how you would apply {topic.lower()} in a learning workflow.",
                f"Отправьте домашнюю работу с описанием того, как применить {topic.lower()} в учебном процессе.",
                f"{topic.lower()} тақырыбын оқу үдерісінде қалай қолданатыныңызды сипаттап, үй жұмысын жіберіңіз.",
            ),
        ]
        if existing_assignments == 0:
            for stage_type, prompt_en, prompt_ru, prompt_kz in assignments:
                cursor.execute(
                    """
                    INSERT INTO assignments(module_id, stage_type, prompt_en, prompt_ru, prompt_kz)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (idx, stage_type, prompt_en, prompt_ru, prompt_kz),
                )

    db.commit()
    db.close()


def module_text(row, prefix):
    lang = session.get("lang", "en")
    return row[f"{prefix}_{lang}"]


def fetch_user_by_username(username):
    return get_db().execute(
        """
        SELECT users.*, roles.name AS role_name
        FROM users JOIN roles ON roles.id = users.role_id
        WHERE username = ?
        """,
        (username,),
    ).fetchone()


def login_user(user):
    session.clear()
    session["user_id"] = user["id"]
    session["role_name"] = user["role_name"]
    session["lang"] = user["preferred_language"] or "en"
    session["lab_token"] = secrets.token_hex(8)
    ensure_progress_rows(user["id"])


def role_label(role_name):
    return {
        "student": t("student_role"),
        "teacher": t("teacher_role"),
        "admin": "Admin",
    }.get(role_name, role_name.title())


app.jinja_env.globals["role_label"] = role_label


def is_student():
    return bool(g.user and g.user["role_name"] == "student")


def is_teacher_user():
    return bool(g.user and g.user["role_name"] in {"teacher", "admin"})


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("login"))
        return view(*args, **kwargs)

    return wrapped


def teacher_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not g.user:
            return redirect(url_for("login"))
        if g.user["role_name"] not in {"admin", "teacher"}:
            abort(403)
        return view(*args, **kwargs)

    return wrapped


@app.before_request
def load_logged_in_user():
    if session.get("lang") not in ALLOWED_LANGS:
        session["lang"] = detect_request_language()
    user_id = session.get("user_id")
    g.user = None
    if user_id:
        g.user = get_db().execute(
            """
            SELECT users.*, roles.name AS role_name
            FROM users JOIN roles ON roles.id = users.role_id
            WHERE users.id = ?
            """,
            (user_id,),
        ).fetchone()
        if not g.user:
            session.clear()
            return
        session["role_name"] = g.user["role_name"]
        if session.get("lang") not in ALLOWED_LANGS:
            session["lang"] = g.user["preferred_language"] or detect_request_language()


def require_module_id(module_id):
    if not 1 <= module_id <= 15:
        abort(404)


def get_module_or_404(module_id):
    require_module_id(module_id)
    module = get_db().execute("SELECT * FROM modules WHERE id = ? AND sort_order <= 15", (module_id,)).fetchone()
    if not module:
        abort(404)
    return module


def enforce_module_access(user_id, module_id):
    require_module_id(module_id)
    if not is_module_unlocked(user_id, module_id):
        abort(403)


def ensure_progress_rows(user_id):
    db = get_db()
    for module_id in range(1, 16):
        db.execute(
            "INSERT OR IGNORE INTO progress_tracking(user_id, module_id) VALUES (?, ?)",
            (user_id, module_id),
        )
    db.commit()


def get_module_progress(user_id, module_id):
    ensure_progress_rows(user_id)
    progress = get_db().execute(
        "SELECT * FROM progress_tracking WHERE user_id = ? AND module_id = ?",
        (user_id, module_id),
    ).fetchone()
    return progress


def is_module_unlocked(user_id, module_id):
    if module_id == 1:
        return True
    previous = get_module_progress(user_id, module_id - 1)
    return bool(previous["module_completed"])


def current_stage(progress):
    if not progress["theory_completed"]:
        return "theory"
    if not progress["test_completed"]:
        return "test"
    if not progress["practice_completed"]:
        return "practice"
    if not progress["homework_completed"]:
        return "homework"
    return "completed"


def stage_allowed(user_id, module_id, stage_name):
    progress = get_module_progress(user_id, module_id)
    if not is_module_unlocked(user_id, module_id):
        return False, progress
    return stage_name == current_stage(progress), progress


def complete_stage(user_id, module_id, stage_name):
    db = get_db()
    if stage_name == "theory":
        db.execute(
            "UPDATE progress_tracking SET theory_completed = 1 WHERE user_id = ? AND module_id = ?",
            (user_id, module_id),
        )
    elif stage_name == "test":
        db.execute(
            "UPDATE progress_tracking SET test_completed = 1 WHERE user_id = ? AND module_id = ?",
            (user_id, module_id),
        )
    elif stage_name == "practice":
        db.execute(
            "UPDATE progress_tracking SET practice_completed = 1 WHERE user_id = ? AND module_id = ?",
            (user_id, module_id),
        )
    elif stage_name == "homework":
        db.execute(
            """
            UPDATE progress_tracking
            SET homework_completed = 1, module_completed = 1, completed_at = ?
            WHERE user_id = ? AND module_id = ?
            """,
            (datetime.utcnow().isoformat(), user_id, module_id),
        )
    db.commit()


def get_user_lab_dir(user_id, module_id):
    session_token = session.setdefault("lab_token", secrets.token_hex(8))
    path = LAB_ROOT / f"user_{user_id}" / f"module_{module_id}" / session_token
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_student_enrolled_course_ids(user_id):
    rows = get_db().execute(
        "SELECT course_id FROM enrollments WHERE student_id = ?",
        (user_id,),
    ).fetchall()
    return [row["course_id"] for row in rows]


def get_module_course(module_id):
    return get_db().execute(
        """
        SELECT courses.*
        FROM modules
        JOIN courses ON courses.id = modules.course_id
        WHERE modules.id = ?
        """,
        (module_id,),
    ).fetchone()


def is_enrolled(user_id, course_id):
    row = get_db().execute(
        "SELECT 1 FROM enrollments WHERE student_id = ? AND course_id = ?",
        (user_id, course_id),
    ).fetchone()
    return bool(row)


def student_can_access_module(user_id, module_id):
    course = get_module_course(module_id)
    if not course:
        return True
    return is_enrolled(user_id, course["id"])


def require_course_access_for_student(user_id, module_id):
    if not is_student():
        return
    if not student_can_access_module(user_id, module_id):
        abort(403)


def get_course_progress_snapshot(user_id, course_id):
    row = get_db().execute(
        """
        SELECT COUNT(modules.id) AS total_modules,
               COALESCE(SUM(progress_tracking.module_completed), 0) AS completed_modules
        FROM modules
        LEFT JOIN progress_tracking
          ON progress_tracking.module_id = modules.id
         AND progress_tracking.user_id = ?
        WHERE modules.course_id = ?
        """,
        (user_id, course_id),
    ).fetchone()
    return {
        "total_modules": row["total_modules"] or 0,
        "completed_modules": row["completed_modules"] or 0,
    }


def build_dashboard_modules(user_id):
    db = get_db()
    ensure_progress_rows(user_id)
    extra_where = " AND modules.id BETWEEN 1 AND 15"
    params = [user_id]
    if g.user and g.user["role_name"] == "student":
        enrolled_course_ids = get_student_enrolled_course_ids(user_id)
        if enrolled_course_ids:
            placeholders = ",".join("?" for _ in enrolled_course_ids)
            extra_where += f" AND modules.course_id IN ({placeholders})"
            params.extend(enrolled_course_ids)
        else:
            return []
    modules = db.execute(
        """
        SELECT modules.*, progress_tracking.theory_completed, progress_tracking.test_completed,
               progress_tracking.practice_completed, progress_tracking.homework_completed,
               progress_tracking.module_completed
        FROM modules
        JOIN progress_tracking ON progress_tracking.module_id = modules.id
        WHERE progress_tracking.user_id = ? 
        """ + extra_where + """
        ORDER BY modules.sort_order
        """,
        params,
    ).fetchall()
    cards = []
    for row in modules:
        cards.append(
            {
                "id": row["id"],
                "title": module_text(row, "title"),
                "summary": module_text(row, "summary"),
                "unlocked": is_module_unlocked(user_id, row["id"]),
                "status": current_stage(row),
                "module_completed": bool(row["module_completed"]),
            }
        )
    return cards


def ai_feedback(stage_type, content):
    length = len(content.strip())
    score = min(100, max(40, length // 2))
    if stage_type == "practice":
        feedback = (
            f"AI review: your practical write-up is {length} characters long. "
            "You show clear execution intent. To strengthen it, mention inputs, code output, and one improvement."
        )
    else:
        feedback = (
            f"AI review: your homework submission is {length} characters long. "
            "The structure is acceptable. Add one reflection, one technical detail, and one applied classroom scenario."
        )
    return score, feedback


def tutor_response(module_title, theory_text, question):
    query = question.lower()
    if "code" in query or "python" in query or "error" in query:
        return (
            f"For {module_title}, start with a minimal Python example, run it in the lab, "
            "and verify the output before adding complexity. If you hit an error, share the traceback and I’ll help map it to the concept."
        )
    if "test" in query or "quiz" in query:
        return (
            f"Focus on the sequence and the purpose of the module. The test checks whether you understand the theory, "
            f"the progression rule, and the practical role of {module_title}."
        )
    return (
        f"Here is the key idea for {module_title}: {theory_text.splitlines()[0]} "
        "Think in terms of measurable learning steps, evidence, and feedback-driven adaptation."
    )


def validate_lab_code(code):
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, f"Syntax error: {exc}"

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            module_names = []
            if isinstance(node, ast.Import):
                module_names = [alias.name.split(".")[0] for alias in node.names]
            else:
                module_names = [(node.module or "").split(".")[0]]
            for name in module_names:
                if name and name not in SAFE_IMPORTS:
                    return False, f"Import '{name}' is not allowed in the lab."
        elif isinstance(node, ast.Call):
            call_name = None
            if isinstance(node.func, ast.Name):
                call_name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                call_name = node.func.attr
            if call_name in BLOCKED_CALL_NAMES:
                return False, f"Operation '{call_name}' is blocked in the lab."
    return True, None


def build_runner_script():
    return textwrap.dedent(
        """
        import io
        import os
        import runpy
        import sys

        try:
            import resource
        except ImportError:  # pragma: no cover
            resource = None

        SCRIPT_PATH = sys.argv[1]
        STDIN_DATA = sys.argv[2] if len(sys.argv) > 2 else ""

        if resource is not None:
            try:
                resource.setrlimit(resource.RLIMIT_CPU, (3, 3))
                resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 * 1024, 256 * 1024 * 1024))
                resource.setrlimit(resource.RLIMIT_FSIZE, (5 * 1024 * 1024, 5 * 1024 * 1024))
            except Exception:
                pass

        sys.stdin = io.StringIO(STDIN_DATA)
        sys.argv = [SCRIPT_PATH]

        os.environ.clear()
        runpy.run_path(SCRIPT_PATH, run_name="__main__")
        """
    ).strip()


def cleanup_lab_dir(lab_dir):
    for path in lab_dir.iterdir():
        if path.is_file() and path.name.startswith("runner_"):
            path.unlink(missing_ok=True)


@app.route("/language/<lang>")
def set_language(lang):
    if lang in ALLOWED_LANGS:
        session["lang"] = lang
        if g.user:
            get_db().execute(
                "UPDATE users SET preferred_language = ? WHERE id = ?",
                (lang, g.user["id"]),
            )
            get_db().commit()
    next_url = request.args.get("next")
    return redirect(next_url or request.referrer or url_for("dashboard"))


@app.route("/")
def index():
    if g.user:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if g.user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = fetch_user_by_username(username)
        password_ok = False
        if user:
            stored_secret = user["password_hash"]
            password_ok = check_password_hash(stored_secret, password)
            if not password_ok and stored_secret == password:
                get_db().execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (generate_password_hash(password), user["id"]),
                )
                get_db().commit()
                user = fetch_user_by_username(username)
                password_ok = True
        if not user or not password_ok:
            flash("Invalid credentials")
        else:
            login_user(user)
            return redirect(url_for("dashboard"))
    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if g.user:
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        role_name = request.form.get("role", "student").strip().lower()
        lang = session.get("lang") if session.get("lang") in ALLOWED_LANGS else detect_request_language()

        error = None
        if not full_name:
            error = "Full name is required."
        elif len(username) < 3:
            error = "Username must be at least 3 characters."
        elif role_name not in ROLE_CHOICES:
            error = "Invalid role selected."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif password != confirm_password:
            error = "Passwords do not match."
        elif fetch_user_by_username(username):
            error = "Username already exists."

        if error:
            flash(error)
        else:
            role_row = get_db().execute("SELECT id, name FROM roles WHERE name = ?", (role_name,)).fetchone()
            get_db().execute(
                """
                INSERT INTO users(username, full_name, password_hash, role_id, preferred_language)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, full_name, generate_password_hash(password), role_row["id"], lang),
            )
            get_db().commit()
            user = fetch_user_by_username(username)
            login_user(user)
            flash("Registration complete.")
            return redirect(url_for("dashboard"))

    return render_template("register.html", role_choices=ROLE_CHOICES)


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/dashboard")
@login_required
def dashboard():
    modules = build_dashboard_modules(g.user["id"])
    progress_summary = {
        "completed_modules": sum(1 for item in modules if item["module_completed"]),
        "total_modules": len(modules),
    }
    enrolled_courses = []
    if g.user["role_name"] == "student":
        rows = get_db().execute(
            """
            SELECT courses.*, users.full_name AS teacher_name
            FROM enrollments
            JOIN courses ON courses.id = enrollments.course_id
            JOIN users ON users.id = courses.teacher_id
            WHERE enrollments.student_id = ?
            ORDER BY courses.created_at DESC
            """,
            (g.user["id"],),
        ).fetchall()
        for row in rows:
            snapshot = get_course_progress_snapshot(g.user["id"], row["id"])
            enrolled_courses.append({**dict(row), **snapshot})
    return render_template(
        "dashboard.html",
        modules=modules,
        progress_summary=progress_summary,
        enrolled_courses=enrolled_courses,
    )


@app.route("/my-courses")
@login_required
def my_courses():
    if g.user["role_name"] != "student":
        return redirect(url_for("dashboard"))
    db = get_db()
    enrolled_ids = set(get_student_enrolled_course_ids(g.user["id"]))
    rows = db.execute(
        """
        SELECT courses.*, users.full_name AS teacher_name,
               COUNT(modules.id) AS module_count
        FROM courses
        JOIN users ON users.id = courses.teacher_id
        LEFT JOIN modules ON modules.course_id = courses.id
        GROUP BY courses.id
        ORDER BY courses.created_at DESC
        """
    ).fetchall()
    enrolled_courses = []
    available_courses = []
    for row in rows:
        card = dict(row)
        card.update(get_course_progress_snapshot(g.user["id"], row["id"]))
        if row["id"] in enrolled_ids:
            enrolled_courses.append(card)
        else:
            available_courses.append(card)
    return render_template(
        "my_courses.html",
        enrolled_courses=enrolled_courses,
        available_courses=available_courses,
    )


@app.route("/courses/<int:course_id>")
@login_required
def course_detail(course_id):
    db = get_db()
    course = db.execute(
        """
        SELECT courses.*, users.full_name AS teacher_name
        FROM courses
        JOIN users ON users.id = courses.teacher_id
        WHERE courses.id = ?
        """,
        (course_id,),
    ).fetchone()
    if not course:
        abort(404)
    enrolled = not is_student() or is_enrolled(g.user["id"], course_id)
    modules = db.execute(
        """
        SELECT modules.*, progress_tracking.theory_completed, progress_tracking.test_completed,
               progress_tracking.practice_completed, progress_tracking.homework_completed,
               progress_tracking.module_completed
        FROM modules
        LEFT JOIN progress_tracking
          ON progress_tracking.module_id = modules.id
         AND progress_tracking.user_id = ?
        WHERE modules.course_id = ?
        ORDER BY modules.sort_order
        """,
        (g.user["id"], course_id),
    ).fetchall()
    module_cards = []
    for row in modules:
        module_cards.append(
            {
                "id": row["id"],
                "title": module_text(row, "title"),
                "summary": module_text(row, "summary"),
                "unlocked": enrolled and is_module_unlocked(g.user["id"], row["id"]),
                "status": current_stage(row) if row["theory_completed"] is not None else "theory",
                "module_completed": bool(row["module_completed"]) if row["module_completed"] is not None else False,
            }
        )
    return render_template("course_detail.html", course=course, modules=module_cards, enrolled=enrolled)


@app.route("/courses/<int:course_id>/enroll", methods=["POST"])
@login_required
def enroll_course(course_id):
    if g.user["role_name"] != "student":
        abort(403)
    db = get_db()
    course = db.execute("SELECT id FROM courses WHERE id = ?", (course_id,)).fetchone()
    if not course:
        abort(404)
    db.execute(
        "INSERT OR IGNORE INTO enrollments(student_id, course_id) VALUES (?, ?)",
        (g.user["id"], course_id),
    )
    db.commit()
    flash("Enrollment completed.")
    return redirect(request.referrer or url_for("my_courses"))


@app.route("/module/<int:module_id>")
@login_required
def module_view(module_id):
    module = get_module_or_404(module_id)
    if is_student() and not student_can_access_module(g.user["id"], module_id):
        flash(t("not_enrolled_message"))
        return redirect(url_for("my_courses"))
    if not is_module_unlocked(g.user["id"], module_id):
        flash("This module is locked until the previous module is fully completed.")
        return redirect(url_for("dashboard"))
    db = get_db()
    lesson = db.execute("SELECT * FROM lessons WHERE module_id = ?", (module_id,)).fetchone()
    progress = get_module_progress(g.user["id"], module_id)
    assignments = db.execute(
        "SELECT * FROM assignments WHERE module_id = ? ORDER BY stage_type",
        (module_id,),
    ).fetchall()
    assignment_map = {row["stage_type"]: row for row in assignments}
    return render_template(
        "module.html",
        module=module,
        lesson=lesson,
        progress=progress,
        stage=current_stage(progress),
        practice_assignment=assignment_map.get("practice"),
        homework_assignment=assignment_map.get("homework"),
    )


@app.route("/module/<int:module_id>/theory/complete", methods=["POST"])
@login_required
def complete_theory_route(module_id):
    require_course_access_for_student(g.user["id"], module_id)
    enforce_module_access(g.user["id"], module_id)
    allowed, _progress = stage_allowed(g.user["id"], module_id, "theory")
    if not allowed:
        return jsonify({"ok": False, "message": "Theory is not available right now."}), 400
    complete_stage(g.user["id"], module_id, "theory")
    return jsonify({"ok": True, "next_stage": "test"})


@app.route("/api/module/<int:module_id>/test")
@login_required
def get_test(module_id):
    require_course_access_for_student(g.user["id"], module_id)
    enforce_module_access(g.user["id"], module_id)
    allowed, progress = stage_allowed(g.user["id"], module_id, "test")
    if not allowed and current_stage(progress) != "completed":
        return jsonify({"ok": False, "message": "Test is locked."}), 403
    rows = get_db().execute("SELECT * FROM tests WHERE module_id = ?", (module_id,)).fetchall()
    questions = []
    lang = session.get("lang", "en")
    for row in rows:
        options = json.loads(row["options_json"])
        questions.append(
            {
                "id": row["id"],
                "question": row[f"question_{lang}"],
                "options": options,
            }
        )
    return jsonify({"ok": True, "questions": questions})


@app.route("/api/module/<int:module_id>/test/submit", methods=["POST"])
@login_required
def submit_test(module_id):
    require_course_access_for_student(g.user["id"], module_id)
    enforce_module_access(g.user["id"], module_id)
    allowed, _progress = stage_allowed(g.user["id"], module_id, "test")
    if not allowed:
        return jsonify({"ok": False, "message": "Test is not available right now."}), 400
    payload = request.get_json(force=True)
    answers = payload.get("answers", {})
    rows = get_db().execute("SELECT * FROM tests WHERE module_id = ?", (module_id,)).fetchall()
    total = len(rows)
    score = 0
    feedback = []
    lang = session.get("lang", "en")
    for row in rows:
        user_answer = answers.get(str(row["id"]), "").strip()
        correct = row["correct_answer"]
        if user_answer == correct:
            score += 1
        else:
            feedback.append(
                {
                    "question": row[f"question_{lang}"],
                    "correct_answer": correct,
                    "explanation": row[f"explanation_{lang}"],
                }
            )
    passed = score == total
    get_db().execute(
        """
        INSERT INTO test_results(user_id, module_id, score, total, passed)
        VALUES (?, ?, ?, ?, ?)
        """,
        (g.user["id"], module_id, score, total, int(passed)),
    )
    get_db().commit()
    if passed:
        complete_stage(g.user["id"], module_id, "test")
    return jsonify(
        {
            "ok": True,
            "passed": passed,
            "score": score,
            "total": total,
            "feedback": feedback,
            "next_stage": "practice" if passed else "test",
        }
    )


@app.route("/api/module/<int:module_id>/practice/submit", methods=["POST"])
@login_required
def submit_practice(module_id):
    require_course_access_for_student(g.user["id"], module_id)
    enforce_module_access(g.user["id"], module_id)
    allowed, _progress = stage_allowed(g.user["id"], module_id, "practice")
    if not allowed:
        return jsonify({"ok": False, "message": "Practice is locked."}), 400
    content = request.get_json(force=True).get("submission", "").strip()
    if len(content) < 40:
        return jsonify({"ok": False, "message": "Practice submission is too short."}), 400
    score, feedback = ai_feedback("practice", content)
    get_db().execute(
        """
        INSERT INTO practice_submissions(user_id, module_id, submission_text, ai_feedback, score)
        VALUES (?, ?, ?, ?, ?)
        """,
        (g.user["id"], module_id, content, feedback, score),
    )
    get_db().commit()
    complete_stage(g.user["id"], module_id, "practice")
    return jsonify({"ok": True, "feedback": feedback, "score": score, "next_stage": "homework"})


@app.route("/api/module/<int:module_id>/homework/submit", methods=["POST"])
@login_required
def submit_homework(module_id):
    require_course_access_for_student(g.user["id"], module_id)
    enforce_module_access(g.user["id"], module_id)
    allowed, _progress = stage_allowed(g.user["id"], module_id, "homework")
    if not allowed:
        return jsonify({"ok": False, "message": "Homework is locked."}), 400
    content = request.get_json(force=True).get("submission", "").strip()
    if not content:
        assignment = get_db().execute(
            "SELECT prompt_en, prompt_ru, prompt_kz FROM assignments WHERE module_id = ? AND stage_type = 'homework'",
            (module_id,),
        ).fetchone()
        lang = session.get("lang", "en")
        content = f"Homework acknowledged. Instruction: {assignment[f'prompt_{lang}']}"
    elif len(content) < 60:
        return jsonify({"ok": False, "message": "Homework submission is too short."}), 400
    score, feedback = ai_feedback("homework", content)
    get_db().execute(
        """
        INSERT INTO homework_submissions(user_id, module_id, submission_text, ai_feedback, score)
        VALUES (?, ?, ?, ?, ?)
        """,
        (g.user["id"], module_id, content, feedback, score),
    )
    get_db().commit()
    if score >= 60:
        complete_stage(g.user["id"], module_id, "homework")
    return jsonify({"ok": True, "feedback": feedback, "score": score, "completed": score >= 60})


@app.route("/history")
@login_required
def history():
    db = get_db()
    selected_module = request.args.get("module", "").strip()
    module_filter = None
    if selected_module.isdigit():
        module_id = int(selected_module)
        if 1 <= module_id <= 15:
            module_filter = module_id

    modules = db.execute(
        "SELECT id, title_en, title_ru, title_kz FROM modules WHERE id BETWEEN 1 AND 15 ORDER BY id"
    ).fetchall()

    params = [g.user["id"]]
    module_sql = ""
    if module_filter:
        module_sql = " AND module_id = ?"
        params.append(module_filter)

    test_rows = db.execute(
        f"""
        SELECT test_results.*, modules.title_en, modules.title_ru, modules.title_kz
        FROM test_results
        JOIN modules ON modules.id = test_results.module_id
        WHERE test_results.user_id = ?{module_sql}
        ORDER BY test_results.created_at DESC
        """,
        params,
    ).fetchall()

    practice_rows = db.execute(
        f"""
        SELECT practice_submissions.*, modules.title_en, modules.title_ru, modules.title_kz
        FROM practice_submissions
        JOIN modules ON modules.id = practice_submissions.module_id
        WHERE practice_submissions.user_id = ?{module_sql}
        ORDER BY practice_submissions.created_at DESC
        """,
        params,
    ).fetchall()

    homework_rows = db.execute(
        f"""
        SELECT homework_submissions.*, modules.title_en, modules.title_ru, modules.title_kz
        FROM homework_submissions
        JOIN modules ON modules.id = homework_submissions.module_id
        WHERE homework_submissions.user_id = ?{module_sql}
        ORDER BY homework_submissions.created_at DESC
        """,
        params,
    ).fetchall()

    completed_rows = db.execute(
        f"""
        SELECT progress_tracking.*, modules.title_en, modules.title_ru, modules.title_kz
        FROM progress_tracking
        JOIN modules ON modules.id = progress_tracking.module_id
        WHERE progress_tracking.user_id = ? AND progress_tracking.module_completed = 1
        {"AND progress_tracking.module_id = ?" if module_filter else ""}
        ORDER BY progress_tracking.completed_at DESC
        """,
        params,
    ).fetchall()

    return render_template(
        "history.html",
        modules=modules,
        selected_module=module_filter,
        test_rows=test_rows,
        practice_rows=practice_rows,
        homework_rows=homework_rows,
        completed_rows=completed_rows,
    )


@app.route("/api/module/<int:module_id>/tutor", methods=["POST"])
@login_required
def tutor(module_id):
    require_course_access_for_student(g.user["id"], module_id)
    enforce_module_access(g.user["id"], module_id)
    db = get_db()
    module = get_module_or_404(module_id)
    lesson = db.execute("SELECT * FROM lessons WHERE module_id = ?", (module_id,)).fetchone()
    question = request.get_json(force=True).get("question", "").strip()
    if not question:
        return jsonify({"ok": False, "message": "Question is required."}), 400
    lang = session.get("lang", "en")
    answer = tutor_response(module[f"title_{lang}"], lesson[f"theory_{lang}"], question)
    return jsonify({"ok": True, "answer": answer})


@app.route("/api/module/<int:module_id>/lab/files")
@login_required
def lab_files(module_id):
    require_course_access_for_student(g.user["id"], module_id)
    enforce_module_access(g.user["id"], module_id)
    lab_dir = get_user_lab_dir(g.user["id"], module_id)
    files = []
    for file_path in sorted(lab_dir.iterdir()):
        if file_path.is_file():
            files.append(
                {
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                    "download_url": url_for("download_lab_file", module_id=module_id, filename=file_path.name),
                }
            )
    return jsonify({"ok": True, "files": files})


@app.route("/api/module/<int:module_id>/lab/upload", methods=["POST"])
@login_required
def upload_lab_file(module_id):
    require_course_access_for_student(g.user["id"], module_id)
    enforce_module_access(g.user["id"], module_id)
    file = request.files.get("file")
    if not file or not file.filename:
        return jsonify({"ok": False, "message": "No file uploaded."}), 400
    filename = secure_filename(file.filename)
    file.save(get_user_lab_dir(g.user["id"], module_id) / filename)
    return jsonify({"ok": True, "message": "File uploaded."})


@app.route("/lab/<int:module_id>/download/<path:filename>")
@login_required
def download_lab_file(module_id, filename):
    require_course_access_for_student(g.user["id"], module_id)
    enforce_module_access(g.user["id"], module_id)
    return send_from_directory(get_user_lab_dir(g.user["id"], module_id), secure_filename(filename), as_attachment=True)


@app.route("/lab/<int:module_id>/artifact/<path:filename>")
@login_required
def view_artifact(module_id, filename):
    require_course_access_for_student(g.user["id"], module_id)
    enforce_module_access(g.user["id"], module_id)
    return send_from_directory(get_user_lab_dir(g.user["id"], module_id), secure_filename(filename))


@app.route("/api/module/<int:module_id>/lab/run", methods=["POST"])
@login_required
def run_lab_code(module_id):
    require_course_access_for_student(g.user["id"], module_id)
    enforce_module_access(g.user["id"], module_id)
    payload = request.get_json(force=True)
    code = payload.get("code", "")
    stdin_data = payload.get("stdin", "")
    if not code.strip():
        return jsonify({"ok": False, "message": "Code cannot be empty."}), 400
    if len(stdin_data) > 2000:
        return jsonify({"ok": False, "message": "Input is too large."}), 400
    ok, validation_message = validate_lab_code(code)
    if not ok:
        return jsonify({"ok": False, "message": validation_message}), 400

    lab_dir = get_user_lab_dir(g.user["id"], module_id)
    script_path = lab_dir / "main.py"
    script_path.write_text(code, encoding="utf-8")
    runner_path = lab_dir / f"runner_{secrets.token_hex(6)}.py"
    runner_path.write_text(build_runner_script(), encoding="utf-8")

    start = time.time()
    before_files = {p.name for p in lab_dir.iterdir() if p.is_file()}
    try:
        result = subprocess.run(
            [sys.executable, "-I", str(runner_path), str(script_path), stdin_data],
            cwd=lab_dir,
            capture_output=True,
            text=True,
            timeout=10,
            env={},
        )
        status = "success" if result.returncode == 0 else "error"
        stdout = result.stdout
        stderr = result.stderr
    except subprocess.TimeoutExpired:
        status = "timeout"
        stdout = ""
        stderr = "Execution timed out after 10 seconds."
    finally:
        cleanup_lab_dir(lab_dir)

    new_artifacts = []
    for path in sorted(lab_dir.iterdir()):
        if path.is_file() and path.name != "main.py":
            if path.name not in before_files or path.stat().st_mtime >= start - 1:
                if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".svg"}:
                    new_artifacts.append(
                        {
                            "name": path.name,
                            "url": url_for("view_artifact", module_id=module_id, filename=path.name),
                        }
                    )

    get_db().execute(
        """
        INSERT INTO lab_execution_logs(user_id, module_id, code, stdout, stderr, status)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (g.user["id"], module_id, code, stdout, stderr, status),
    )
    get_db().commit()

    return jsonify(
        {
            "ok": True,
            "status": status,
            "stdout": stdout,
            "stderr": stderr,
            "artifacts": new_artifacts,
        }
    )


@app.route("/teacher")
@teacher_required
def teacher_panel():
    db = get_db()
    modules = db.execute("SELECT * FROM modules WHERE id BETWEEN 1 AND 15 ORDER BY sort_order").fetchall()
    courses = db.execute(
        """
        SELECT courses.*, COUNT(modules.id) AS module_count
        FROM courses
        LEFT JOIN modules ON modules.course_id = courses.id
        WHERE courses.teacher_id = ?
        GROUP BY courses.id
        ORDER BY courses.created_at DESC
        """,
        (g.user["id"],),
    ).fetchall()
    students = db.execute(
        """
        SELECT users.id, users.username, users.full_name,
               SUM(progress_tracking.module_completed) AS completed_modules
        FROM users
        JOIN roles ON roles.id = users.role_id
        LEFT JOIN progress_tracking ON progress_tracking.user_id = users.id
        WHERE roles.name = 'student'
        GROUP BY users.id
        ORDER BY users.full_name
        """
    ).fetchall()
    return render_template("teacher.html", modules=modules, students=students, courses=courses)


@app.route("/teacher/courses")
@teacher_required
def teacher_courses():
    db = get_db()
    courses = db.execute(
        """
        SELECT courses.*, COUNT(modules.id) AS module_count
        FROM courses
        LEFT JOIN modules ON modules.course_id = courses.id
        WHERE courses.teacher_id = ?
        GROUP BY courses.id
        ORDER BY courses.created_at DESC
        """,
        (g.user["id"],),
    ).fetchall()
    return render_template("teacher_courses.html", courses=courses)


@app.route("/teacher/courses/create", methods=["GET", "POST"])
@teacher_required
def teacher_course_create():
    db = get_db()
    modules = db.execute(
        "SELECT * FROM modules WHERE id BETWEEN 1 AND 15 ORDER BY sort_order"
    ).fetchall()
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        selected_modules = [int(value) for value in request.form.getlist("module_ids") if value.isdigit()]
        if not title or not description:
            flash("Title and description are required.")
        else:
            cursor = db.execute(
                "INSERT INTO courses(title, description, teacher_id) VALUES (?, ?, ?)",
                (title, description, g.user["id"]),
            )
            course_id = cursor.lastrowid
            if selected_modules:
                placeholders = ",".join("?" for _ in selected_modules)
                db.execute(
                    f"UPDATE modules SET course_id = ? WHERE id IN ({placeholders})",
                    [course_id, *selected_modules],
                )
            db.commit()
            return redirect(url_for("teacher_course_detail", course_id=course_id))
    return render_template("teacher_course_form.html", course=None, modules=modules, selected_module_ids=set())


def ensure_teacher_owns_course(course_id):
    course = get_db().execute(
        "SELECT * FROM courses WHERE id = ? AND teacher_id = ?",
        (course_id, g.user["id"]),
    ).fetchone()
    if not course:
        abort(404)
    return course


@app.route("/teacher/courses/<int:course_id>", methods=["GET", "POST"])
@teacher_required
def teacher_course_detail(course_id):
    db = get_db()
    course = ensure_teacher_owns_course(course_id)
    modules = db.execute(
        "SELECT * FROM modules WHERE id BETWEEN 1 AND 15 ORDER BY sort_order"
    ).fetchall()
    selected_module_ids = {
        row["id"] for row in db.execute("SELECT id FROM modules WHERE course_id = ?", (course_id,)).fetchall()
    }
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        selected_ids = {int(value) for value in request.form.getlist("module_ids") if value.isdigit()}
        if not title or not description:
            flash("Title and description are required.")
        else:
            db.execute(
                "UPDATE courses SET title = ?, description = ? WHERE id = ?",
                (title, description, course_id),
            )
            db.execute("UPDATE modules SET course_id = NULL WHERE course_id = ?", (course_id,))
            if selected_ids:
                placeholders = ",".join("?" for _ in selected_ids)
                db.execute(
                    f"UPDATE modules SET course_id = ? WHERE id IN ({placeholders})",
                    [course_id, *sorted(selected_ids)],
                )
            db.commit()
            return redirect(url_for("teacher_course_detail", course_id=course_id))

    enrolled_students = db.execute(
        """
        SELECT users.id, users.full_name, users.username, enrollments.created_at
        FROM enrollments
        JOIN users ON users.id = enrollments.student_id
        WHERE enrollments.course_id = ?
        ORDER BY enrollments.created_at DESC
        """,
        (course_id,),
    ).fetchall()
    test_rows = db.execute(
        """
        SELECT test_results.*, users.full_name, modules.title_en, modules.title_ru, modules.title_kz
        FROM test_results
        JOIN users ON users.id = test_results.user_id
        JOIN modules ON modules.id = test_results.module_id
        WHERE modules.course_id = ?
        ORDER BY test_results.created_at DESC
        """,
        (course_id,),
    ).fetchall()
    practice_rows = db.execute(
        """
        SELECT practice_submissions.*, users.full_name, modules.title_en, modules.title_ru, modules.title_kz
        FROM practice_submissions
        JOIN users ON users.id = practice_submissions.user_id
        JOIN modules ON modules.id = practice_submissions.module_id
        WHERE modules.course_id = ?
        ORDER BY practice_submissions.created_at DESC
        """,
        (course_id,),
    ).fetchall()
    homework_rows = db.execute(
        """
        SELECT homework_submissions.*, users.full_name, modules.title_en, modules.title_ru, modules.title_kz
        FROM homework_submissions
        JOIN users ON users.id = homework_submissions.user_id
        JOIN modules ON modules.id = homework_submissions.module_id
        WHERE modules.course_id = ?
        ORDER BY homework_submissions.created_at DESC
        """,
        (course_id,),
    ).fetchall()
    return render_template(
        "teacher_course_form.html",
        course=course,
        modules=modules,
        selected_module_ids=selected_module_ids,
        enrolled_students=enrolled_students,
        test_rows=test_rows,
        practice_rows=practice_rows,
        homework_rows=homework_rows,
    )


@app.route("/teacher/courses/<int:course_id>/grade/<submission_type>/<int:submission_id>", methods=["POST"])
@teacher_required
def teacher_grade_submission(course_id, submission_type, submission_id):
    ensure_teacher_owns_course(course_id)
    db = get_db()
    score = request.form.get("score", "").strip()
    comment = request.form.get("comment", "").strip()
    score_value = int(score) if score.isdigit() else None
    if submission_type == "practice":
        db.execute(
            """
            UPDATE practice_submissions
            SET score = ?, teacher_comment = ?
            WHERE id = ? AND module_id IN (SELECT id FROM modules WHERE course_id = ?)
            """,
            (score_value, comment, submission_id, course_id),
        )
    elif submission_type == "homework":
        db.execute(
            """
            UPDATE homework_submissions
            SET score = COALESCE(?, score), teacher_comment = ?
            WHERE id = ? AND module_id IN (SELECT id FROM modules WHERE course_id = ?)
            """,
            (score_value, comment, submission_id, course_id),
        )
    else:
        abort(400)
    db.commit()
    return redirect(url_for("teacher_course_detail", course_id=course_id))


@app.route("/teacher/module/<int:module_id>", methods=["GET", "POST"])
@teacher_required
def teacher_module(module_id):
    db = get_db()
    module = get_module_or_404(module_id)
    lesson = db.execute("SELECT * FROM lessons WHERE module_id = ?", (module_id,)).fetchone()
    practice_assignment = db.execute(
        "SELECT * FROM assignments WHERE module_id = ? AND stage_type = 'practice'",
        (module_id,),
    ).fetchone()
    homework_assignment = db.execute(
        "SELECT * FROM assignments WHERE module_id = ? AND stage_type = 'homework'",
        (module_id,),
    ).fetchone()
    tests = db.execute("SELECT * FROM tests WHERE module_id = ?", (module_id,)).fetchall()

    if request.method == "POST":
        db.execute(
            """
            UPDATE modules
            SET title_en = ?, title_ru = ?, title_kz = ?, summary_en = ?, summary_ru = ?, summary_kz = ?
            WHERE id = ?
            """,
            (
                request.form["title_en"],
                request.form["title_ru"],
                request.form["title_kz"],
                request.form["summary_en"],
                request.form["summary_ru"],
                request.form["summary_kz"],
                module_id,
            ),
        )
        db.execute(
            """
            UPDATE lessons
            SET theory_en = ?, theory_ru = ?, theory_kz = ?
            WHERE module_id = ?
            """,
            (
                request.form["theory_en"],
                request.form["theory_ru"],
                request.form["theory_kz"],
                module_id,
            ),
        )
        db.execute(
            "UPDATE assignments SET prompt_en = ?, prompt_ru = ?, prompt_kz = ? WHERE id = ?",
            (
                request.form["practice_en"],
                request.form["practice_ru"],
                request.form["practice_kz"],
                practice_assignment["id"],
            ),
        )
        db.execute(
            "UPDATE assignments SET prompt_en = ?, prompt_ru = ?, prompt_kz = ? WHERE id = ?",
            (
                request.form["homework_en"],
                request.form["homework_ru"],
                request.form["homework_kz"],
                homework_assignment["id"],
            ),
        )
        for test in tests:
            prefix = f"test_{test['id']}"
            options = [
                request.form[f"{prefix}_option_1"],
                request.form[f"{prefix}_option_2"],
                request.form[f"{prefix}_option_3"],
                request.form[f"{prefix}_option_4"],
            ]
            db.execute(
                """
                UPDATE tests
                SET question_en = ?, question_ru = ?, question_kz = ?, options_json = ?,
                    correct_answer = ?, explanation_en = ?, explanation_ru = ?, explanation_kz = ?
                WHERE id = ?
                """,
                (
                    request.form[f"{prefix}_question_en"],
                    request.form[f"{prefix}_question_ru"],
                    request.form[f"{prefix}_question_kz"],
                    json.dumps(options),
                    request.form[f"{prefix}_answer"],
                    request.form[f"{prefix}_explanation_en"],
                    request.form[f"{prefix}_explanation_ru"],
                    request.form[f"{prefix}_explanation_kz"],
                    test["id"],
                ),
            )
        db.commit()
        flash("Module updated.")
        return redirect(url_for("teacher_module", module_id=module_id))

    return render_template(
        "teacher_module.html",
        module=module,
        lesson=lesson,
        practice_assignment=practice_assignment,
        homework_assignment=homework_assignment,
        tests=tests,
        json=json,
    )


@app.route("/teacher/student/<int:user_id>")
@teacher_required
def teacher_student(user_id):
    db = get_db()
    ensure_progress_rows(user_id)
    student = db.execute(
        """
        SELECT users.*, roles.name AS role_name
        FROM users JOIN roles ON roles.id = users.role_id
        WHERE users.id = ?
        """,
        (user_id,),
    ).fetchone()
    if not student:
        abort(404)
    progress_rows = db.execute(
        """
        SELECT modules.id, modules.title_en, modules.title_ru, modules.title_kz,
               progress_tracking.*
        FROM progress_tracking
        JOIN modules ON modules.id = progress_tracking.module_id
        WHERE progress_tracking.user_id = ? AND modules.id BETWEEN 1 AND 15
        ORDER BY modules.id
        """,
        (user_id,),
    ).fetchall()
    return render_template("student_progress.html", student=student, rows=progress_rows)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
