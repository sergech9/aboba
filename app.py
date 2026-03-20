from fastapi import FastAPI, WebSocket, Request, Depends, Header, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel
import models
from database import engine, SessionLocal, Base
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import bcrypt

API_KEY = "aboba_key228"


Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="aboba_key228")

templates = Jinja2Templates(directory="templates")

app.mount("/static", StaticFiles(directory="static"), name="static")

connections = []


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TicketCreate(BaseModel):
    text: str

def verify_api_key(x_api_key: str = Header(None)):
    if x_api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key")
    
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})

@app.post("/login", response_class=HTMLResponse)
def login_post(request: Request, login: str = Form(...), password: str = Form(...), db=Depends(get_db)):
    user = db.query(models.User).filter(models.User.login == login).first()
    if not user or not bcrypt.checkpw(password.encode(), user.password.encode()):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Неверный логин или пароль"})
    # Сохраняем логин в сессии
    request.session["user"] = user.login
    return RedirectResponse("/dashboard", status_code=302)

# Защищённая страница
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db=Depends(get_db)):

    login = request.session.get("user")

    if not login:
        return RedirectResponse("/login", status_code=302)

    user = db.query(models.User).filter(models.User.login == login).first()

    tickets = db.query(models.Ticket).filter(models.Ticket.closed == False).all()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "name": user.username,
            "tickets": tickets
        }
    )

@app.get("/")
def root(request: Request):

    if request.session.get("user"):
        return RedirectResponse("/dashboard")

    return RedirectResponse("/login")

# Выход
@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    tickets = db.query(models.Ticket).filter_by(closed=False).all()
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "tickets": tickets}
    )


@app.post("/api/request")
async def create_ticket(ticket: TicketCreate, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    ticket = models.Ticket(text=ticket.text)
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    for ws in connections:
        await ws.send_json({
            "type": "new_ticket",
            "id": ticket.id,
            "text": ticket.text
        })

    return {"status": "ok"}


@app.delete("/api/request/{ticket_id}")
async def close_ticket(ticket_id: int, db: Session = Depends(get_db)):

    ticket = db.query(models.Ticket).get(ticket_id)
    ticket.closed = True
    db.commit()

    for ws in connections:
        await ws.send_json({
            "type": "close_ticket",
            "id": ticket_id
        })

    return {"status": "closed"}


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):

    await ws.accept()
    connections.append(ws)

    try:
        while True:
            await ws.receive_text()
    except:
        connections.remove(ws)