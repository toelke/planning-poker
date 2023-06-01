import os
import logging
import sys
import asyncio
import json

import structlog
from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ValidationError, validator
from typing import Optional


class Move(BaseModel):
    player_id: str
    points: Optional[int]

    @validator('points')
    def points_must_be_fibonacci(cls, v):
        if v not in (None, 1, 2, 3, 5, 8, 13, 21):
            raise ValueError("points not fibonacci")
        return v


class UserNameUpdate(BaseModel):
    userName: str


def setup_logging(name="<app>", level=None):
    """
    Setup logging. Returns a struct-logger.

    Usage:
    ```
    log = setup_logging()
    log.warn("This is a warning!", some_value=679)
    ```
    """
    log_level = os.environ.get("LOG_LEVEL", "INFO" if level is None else level)

    # Setup logging for us
    log = structlog.getLogger(name)
    structlog.configure(wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(log_level)))

    # Setup logging for libraries using the default logger
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=logging.INFO)

    # Log as JSON if not on a terminal
    if not sys.stdout.isatty():
        structlog.configure(
            processors=[
                structlog.processors.add_log_level,
                structlog.processors.TimeStamper(fmt="iso", key="ts"),
                structlog.processors.dict_tracebacks,
                structlog.processors.JSONRenderer(),
            ]
        )

    return log


log = setup_logging('planning-poker')


class Bus:
    def __init__(self):
        self.sockets = set()

    def register(self, sock):
        self.sockets.add(sock)

    def unregister(self, sock):
        self.sockets.remove(sock)

    async def emit(self, msg):
        for sock in self.sockets:
            asyncio.create_task(sock.send_json(msg))


class Participant(BaseModel):
    points: int = None
    userName: str = ""


class Game:
    def __init__(self):
        self.bus = Bus()

        self.participants = {}
        self.opened = False

    async def update_username(self, id, username):
        self.participants[id].userName = username
        await self.send_state()

    async def send_state(self):
        if self.opened:
            state = {"participants": {k: self.participants[k].dict() for k in self.participants}}
        else:
            state = {
                "participants": {k: {"userName": self.participants[k].userName, "points": (self.participants[k].points is not None)} for k in self.participants}
            }

        state["opened"] = self.opened
        await self.bus.emit(state)

    async def join(self, id, sock: WebSocket):
        if id in self.participants:
            log.error("Participant joined twice", id=id)
            await sock.send_json({"error": "You can't join twice"})
            await sock.close()
            return False
        self.bus.register(sock)
        self.participants[id] = Participant()
        await self.send_state()
        return True

    async def leave(self, id, sock):
        self.bus.unregister(sock)
        self.participants.pop(id)
        await self.send_state()

    async def handle_msg(self, id, msg):
        msg['player_id'] = id
        try:
            move = Move(**msg)
        except ValidationError:
            log.error("Cannot unmarshal move", msg=msg)
            return
        log.info("New move received", id=id, move=move)
        self.participants[id].points = move.points
        await self.send_state()

    async def clear(self):
        for id in self.participants:
            self.participants[id].points = None
            self.opened = False
        await self.send_state()

    async def open(self):
        if all((v.points is not None for v in self.participants.values())):
            self.opened = True
            await self.send_state()
            return True
        return False


GAME = Game()


def make_app(prefix_router):
    @prefix_router.on_event("startup")
    async def startup():
        app.state.dummy = 7
        log.info("API registered")

    @prefix_router.post("/clear")
    async def clear_game():
        await GAME.clear()
        return "cleared"

    @prefix_router.post("/open")
    async def open_game():
        if await GAME.open():
            return "opened"
        return "not opened"

    @prefix_router.post('/participant/{id}/userName')
    async def userName(id: str, userName: UserNameUpdate):
        await GAME.update_username(id, userName.userName)
        log.info("Received new username", id=id, userName=userName.userName)
        return "Thanks"

    @prefix_router.websocket('/participant/{id}')
    async def participant_endpoint(websocket: WebSocket, id: str):
        await websocket.accept()
        log.info("Client connected!", id=id)
        if await GAME.join(id, websocket):
            try:
                while True:
                    try:
                        msg = await websocket.receive_json()
                        log.info("message received", id=id, msg=msg)
                        await GAME.handle_msg(id, msg)
                    except json.decoder.JSONDecodeError:
                        log.error("invalid message received", id=id)

            except WebSocketDisconnect:
                await GAME.leave(id, websocket)


def get_root_app():
    root_app = FastAPI()
    make_app(root_app)
    return root_app


app = FastAPI()
prefix_router = APIRouter(prefix="/api")
make_app(prefix_router)
app.include_router(prefix_router)

try:
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
except RuntimeError:
    pass
