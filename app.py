from fastapi import FastAPI
import aiohttp
import bs4
import aioredis
from fastapi_cache import FastAPICache
from fastapi_cache.decorator import cache
from fastapi_cache.backends.redis import RedisBackend
from datetime import timedelta
from pydantic import BaseSettings, RedisDsn

# from fastapi.middleware.cors import CORSMiddleware


class Environment(BaseSettings):
    redis_url: RedisDsn


app = FastAPI()
env = Environment(_env_file=".env", _env_file_encoding="utf-8")  # type: ignore

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )


URL = "http://pocae.tstgo.cl/PortalCAE-WAR-MODULE/SesionPortalServlet"


def gen_balance_data(bip_number: int):
    return {
        "accion": 6,
        "NumDistribuidor": 99,
        "NomUsuario": "usuInternet",
        "NomHost": "AFT",
        "NomDominio": "aft.cl",
        "Trx": "",
        "RutUsuario": 0,
        "NumTarjeta": str(bip_number),
        "bloqueable": "",
    }


def parse_balance_html(html: str, bip_number: int):
    soup = bs4.BeautifulSoup(html, "lxml")
    tag = soup.find("td", text=str(bip_number), attrs={"class": "verdanabold-ckc"})
    print(soup)
    print(soup.prettify())
    if tag and tag.parent and tag.parent.parent:
        data_table = tag.parent.parent
        data: "list[bs4.Tag]" = data_table.find_all(
            "td", attrs={"class": "verdanabold-ckc"}
        )
        return dict([[data[i].text, data[i + 1].text] for i in range(0, len(data), 2)])


@app.get("/balance/{bip_number}", name="Obtener datos de Bip!", tags=["Bip!"])
@cache(expire=int(timedelta(hours=2).total_seconds()))
async def get_balance(bip_number: int):
    async with aiohttp.ClientSession() as session:
        async with session.post(URL, data=gen_balance_data(bip_number)) as response:
            return parse_balance_html(await response.text(), bip_number)


@app.on_event("startup")
async def startup():
    redis = aioredis.from_url(env.redis_url, encoding="utf8", decode_responses=True)
    FastAPICache.init(RedisBackend(redis), prefix="fastapi-cache")
