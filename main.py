from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from subprocess import run, PIPE
from bs4 import BeautifulSoup
import requests
import json
import os
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # React 주소만 허용해도 됨
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
