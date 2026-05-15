import secrets

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import Interview, get_db


router = APIRouter()


def is_admin(request: Request) -> bool:
    return request.session.get("admin") is True


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise HTTPException(status_code=401, detail="Admin login required")


@router.get("/", response_class=HTMLResponse)
def root() -> RedirectResponse:
    return RedirectResponse("/admin", status_code=302)


@router.get("/admin/login", response_class=HTMLResponse)
def login_page(request: Request):
    return request.app.state.templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/admin/login", response_class=HTMLResponse)
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    settings = get_settings()
    if secrets.compare_digest(username, settings.admin_username) and secrets.compare_digest(
        password, settings.admin_password
    ):
        request.session["admin"] = True
        return RedirectResponse("/admin", status_code=303)
    return request.app.state.templates.TemplateResponse(
        "login.html",
        {"request": request, "error": "Invalid username or password"},
        status_code=401,
    )


@router.post("/admin/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin/login", status_code=303)


@router.get("/admin", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    interviews = db.query(Interview).order_by(desc(Interview.created_at)).all()
    return request.app.state.templates.TemplateResponse(
        "admin.html",
        {"request": request, "interviews": interviews, "base_url": get_settings().app_base_url.rstrip("/")},
    )


@router.post("/admin/interviews")
def create_interview(
    request: Request,
    candidate_name: str = Form(...),
    candidate_email: str = Form(...),
    role: str = Form(...),
    skills: str = Form(...),
    duration_minutes: int = Form(20),
    db: Session = Depends(get_db),
):
    require_admin(request)
    interview = Interview(
        token=secrets.token_urlsafe(24),
        candidate_name=candidate_name.strip(),
        candidate_email=candidate_email.strip(),
        role=role.strip(),
        skills=skills.strip(),
        duration_minutes=duration_minutes,
    )
    db.add(interview)
    db.commit()
    return RedirectResponse("/admin", status_code=303)


@router.get("/admin/interviews/{interview_id}", response_class=HTMLResponse)
def report_page(request: Request, interview_id: int, db: Session = Depends(get_db)):
    if not is_admin(request):
        return RedirectResponse("/admin/login", status_code=302)
    interview = db.get(Interview, interview_id)
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")
    return request.app.state.templates.TemplateResponse(
        "report.html",
        {"request": request, "interview": interview},
    )
