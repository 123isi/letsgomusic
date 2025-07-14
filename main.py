from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from subprocess import run, PIPE
from bs4 import BeautifulSoup
import requests
import sqlite3
import json
from db import init_db
import os
from fastapi import Request
from fastapi import Response
from datetime import datetime, timedelta
from fastapi.responses import Response

import re
app = FastAPI()
init_db()
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://letsgomusic-4nbo.vercel.app/",
    ]
    ,  # React 주소만 허용해도 됨
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/melon")
async def get_melon_chart():
    url = "https://www.melon.com/chart/index.htm"
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")

    songs = soup.select("div.ellipsis.rank01 a")
    artists = [artist.find('a') for artist in soup.select("div.ellipsis.rank02")]

    result = []
    for i in range(min(len(songs), len(artists))):
        result.append({
            "rank": i + 1,
            "title": songs[i].get_text(strip=True),
            "artist": artists[i].get_text(strip=True),
        })

    return JSONResponse(content=result)

@app.get("/melon/search")
def search_youtube(q: str = Query(..., min_length=1)):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(base_dir, "yt-search.js")

    result = run(["node", script_path, q], stdout=PIPE, stderr=PIPE)

    if result.returncode != 0:
        print("Node stderr:", result.stderr.decode())  # 👈 로그 확인
        return {"error": result.stderr.decode()}

    print("Node stdout:", result.stdout.decode())  # 👈 정상 출력도 확인
    return json.loads(result.stdout)

@app.get("/playlist")
async def get_playlist():
    try:
        with sqlite3.connect("playlist.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS playlist (
                    rank INTEGER,
                    title TEXT,
                    artist TEXT,
                    albumImageUrl TEXT
                )
            """)
            cursor.execute("SELECT rank, title, artist, albumImageUrl FROM playlist")
            rows = cursor.fetchall()
            return [
                {"rank": r, "title": t, "artist": a, "albumImageUrl": img}
                for r, t, a, img in rows
            ]
    except Exception as e:
        print("플레이리스트 조회 에러:", e)
        return []


@app.post("/playlist")

async def save_playlist(request: Request):
    print("hello ples")
    try:
        data = await request.json()
    except Exception as e:
        print("request.json() 파싱 에러:", e)
        return {"error": "Invalid JSON"}

    songs = data.get("songs", [])
    if not songs:
        return {"message": "No songs to save."}

    filtered_songs = [
        {
            "rank": s["rank"],
            "title": s["title"],
            "artist": s["artist"]
        }
        for s in songs
    ]

    try:
        with sqlite3.connect("playlist.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlist (
                rank INTEGER,
                title TEXT,
                artist TEXT,
                albumImageUrl TEXT
            )
            """)

            cursor.execute("DELETE FROM playlist")  # 기존 데이터 삭제
            for song in filtered_songs:
                cursor.execute(
                    "INSERT INTO playlist (rank, title, artist, albumImageUrl) VALUES (?, ?, ?, ?)",
                    (song["rank"], song["title"], song["artist"], song.get("albumImageUrl"))
                )

            conn.commit()

        return {"message": "Playlist saved successfully."}
    except Exception as e:
        print("DB 저장 에러:", e)
        return {"error": str(e)}

@app.delete("/playlist/{rank}")
async def delete_song(rank: int):
    try:
        with sqlite3.connect("playlist.db") as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM playlist WHERE rank = ?", (rank,))
            conn.commit()
        return {"message": "삭제됨"}
    except Exception as e:
        return {"error": str(e)}
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

import re  # 정규표현식 추가

@app.post("/register")
async def register_user(data: dict):
    username = data.get("username", "").strip()
    password = data.get("password", "").strip()

    if not username or not password:
        return {"error": "아이디와 비밀번호는 필수입니다."}

    if not re.fullmatch(r"[a-zA-Z0-9]{4,}", username):
        return {"error": "아이디는 영문 또는 숫자로 4자 이상이어야 합니다."}

    if not re.fullmatch(r"(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z\d]{8,}", password):
        return {"error": "비밀번호는 8자 이상, 영문과 숫자를 포함해야 합니다."}

    hashed = pwd_context.hash(password)

    try:
        with sqlite3.connect("playlist.db") as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password TEXT NOT NULL
                )
            """)
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", (username, hashed))
            conn.commit()
        return {"message": "회원가입 성공"}
    except sqlite3.IntegrityError:
        return {"error": "이미 존재하는 사용자입니다."}


from jose import jwt, JWTError

SECRET_KEY = "mysecretkey"  # 실제론 환경변수로
ALGORITHM = "HS256"
@app.post("/login")
async def login_user(data: dict, response: Response):
    username = data.get("username")
    password = data.get("password")

    with sqlite3.connect("playlist.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()

    if not row:
        return {"error": "존재하지 않는 사용자입니다"}

    hashed_pw = row[0]
    if not pwd_context.verify(password, hashed_pw):
        return {"error": "비밀번호가 틀렸습니다"}

    # ✅ 토큰 만료 시간 설정 (60000ms = 60초)
    expire = datetime.utcnow() + timedelta(milliseconds=60000)
    token_payload = {
        "username": username,
        "exp": expire  # 👈 여기에 만료 시간 넣기
    }

    token = jwt.encode(token_payload, SECRET_KEY, algorithm=ALGORITHM)

    res = JSONResponse(content={"message": "로그인 성공"})
    res.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax"
    )
    return res


@app.get("/me")
def my_info(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return JSONResponse(status_code=401, content={"error": "로그인 필요"})

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"username": payload.get("username")}
    except JWTError:
        return JSONResponse(status_code=401, content={"error": "토큰 오류"})
