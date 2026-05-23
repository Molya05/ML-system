# AI-powered adaptive 15-module learning system

Production-style Flask LMS with:

- 15 sequential modules
- strict `Theory -> Test -> Practice -> Homework` stage enforcement
- multilingual UI (`EN`, `RU`, `KZ`)
- teacher/admin content management
- integrated browser Python code lab with upload/download and artifact previews
- AI-style local tutor, feedback, and dynamic test workflow

## Project structure

```text
ML-system/
├── app.py
├── lms.db                      # created on first run
├── requirements.txt
├── README.md
├── user_labs/                  # created automatically for per-user lab workspaces
├── static/
│   ├── css/
│   │   └── styles.css
│   └── js/
│       └── app.js
└── templates/
    ├── base.html
    ├── dashboard.html
    ├── login.html
    ├── module.html
    ├── student_progress.html
    ├── teacher.html
    └── teacher_module.html
```

## Database schema

SQLite tables created automatically:

- `roles`
- `users`
- `modules`
- `lessons`
- `tests`
- `assignments`
- `practice_submissions`
- `homework_submissions`
- `progress_tracking`
- `lab_execution_logs`

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Then open [http://127.0.0.1:5000](http://127.0.0.1:5000)

## Notes

- The lab runs Python code in a per-user, per-module, per-session workspace under `user_labs/`.
- Generated image files such as `.png` are shown as artifacts after execution.
- The stage lock logic is enforced server-side; users cannot skip modules or later stages.
