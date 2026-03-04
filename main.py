import os
import requests
from fastapi import FastAPI, HTTPException, Body, Request, Header
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from pymongo.auth_oidc import OIDCCallback, OIDCCallbackContext, OIDCCallbackResult
from dotenv import load_dotenv

load_dotenv()

CLIENT_ID = os.getenv("PUBLIC_KEY")
CLIENT_SECRET = os.getenv("PRIVATE_KEY")
CLUSTER = os.getenv("MONGO_CLUSTER")


def fetch_oidc_token() -> str:
    resp = requests.post(
        "https://services.cloud.mongodb.com/api/client/v2.0/auth/token",
        json={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        },
    )
    resp.raise_for_status()
    return resp.json()["access_token"]


class ServiceAccountCallback(OIDCCallback):
    def fetch(self, context: OIDCCallbackContext) -> OIDCCallbackResult:
        return OIDCCallbackResult(access_token=fetch_oidc_token())


uri = f"mongodb+srv://{CLUSTER}/?authMechanism=MONGODB-OIDC"

app = FastAPI()
client = MongoClient(
    uri,
    authMechanism="MONGODB-OIDC",
    authMechanismProperties={
        "OIDC_CALLBACK": ServiceAccountCallback(),
        "ENVIRONMENT": "test",
    },
)
db = client["iiif"]
works_coll = db["works"]
collections_coll = db["collections"]

ALLOWED_TOKENS = set(os.getenv("IIIF_API_TOKENS", "").split(","))


def verify_token(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or malformed Authorization header")
    token = authorization.removeprefix("Bearer ")
    if token not in ALLOWED_TOKENS:
        raise HTTPException(status_code=403, detail="Invalid API token")


# ── Works ──────────────────────────────────────────────────────────────────────

@app.put("/works/{item_id}")
def put_work(
    item_id: str,
    request: Request,
    manifest: dict = Body(...),
    authorization: str | None = Header(default=None),
):
    verify_token(authorization)
    base_url = str(request.base_url).rstrip("/")
    full_id = f"{base_url}/works/{item_id}"
    manifest["_id"] = item_id
    manifest["id"] = full_id
    manifest["@id"] = full_id
    works_coll.replace_one({"_id": item_id}, manifest, upsert=True)
    return {"success": True, "id": full_id}


@app.get("/works/{item_id}")
def get_work(item_id: str, request: Request):
    manifest = works_coll.find_one({"_id": item_id})
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")
    base_url = str(request.base_url).rstrip("/")
    full_id = f"{base_url}/works/{item_id}"
    manifest.pop("_id", None)
    manifest["id"] = full_id
    manifest["@id"] = full_id
    return JSONResponse(content=manifest)


# ── Collections ────────────────────────────────────────────────────────────────

@app.put("/collections/{item_id}")
def put_collection(
    item_id: str,
    request: Request,
    manifest: dict = Body(...),
    authorization: str | None = Header(default=None),
):
    verify_token(authorization)
    base_url = str(request.base_url).rstrip("/")
    full_id = f"{base_url}/collections/{item_id}"
    manifest["_id"] = item_id
    manifest["id"] = full_id
    manifest["@id"] = full_id
    collections_coll.replace_one({"_id": item_id}, manifest, upsert=True)
    return {"success": True, "id": full_id}


@app.get("/collections/{item_id}")
def get_collection(item_id: str, request: Request):
    manifest = collections_coll.find_one({"_id": item_id})
    if not manifest:
        raise HTTPException(status_code=404, detail="Collection not found")
    base_url = str(request.base_url).rstrip("/")
    full_id = f"{base_url}/collections/{item_id}"
    manifest.pop("_id", None)
    manifest["id"] = full_id
    manifest["@id"] = full_id
    return JSONResponse(content=manifest)
