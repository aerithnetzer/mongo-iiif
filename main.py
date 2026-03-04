import os
from fastapi import FastAPI, HTTPException, Body, Request, Header
from fastapi.responses import JSONResponse
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

client = MongoClient(os.getenv("MONGODB_OCR_DEVELOPMENT_CONN_STRING_IMPULSE"))
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
    """
    Store a full IIIF Manifest JSON document.
    Requires a valid Bearer token in the Authorization header.
    The item_id becomes the Mongo _id, and the manifest's id field
    is set to the full URL of this endpoint.
    """
    verify_token(authorization)
    base_url = str(request.base_url).rstrip("/")
    full_id = f"{base_url}/works/{item_id}"
    manifest["_id"] = item_id
    manifest["id"] = full_id    # IIIF v3
    manifest["@id"] = full_id   # IIIF v2 compatibility
    works_coll.replace_one({"_id": item_id}, manifest, upsert=True)
    return {"success": True, "id": full_id}


@app.get("/works/{item_id}")
def get_work(item_id: str, request: Request):
    """
    Return the stored IIIF manifest JSON, with id reflecting the live request URL.
    """
    manifest = works_coll.find_one({"_id": item_id})
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")
    base_url = str(request.base_url).rstrip("/")
    full_id = f"{base_url}/works/{item_id}"
    manifest.pop("_id", None)
    manifest["id"] = full_id    # IIIF v3
    manifest["@id"] = full_id   # IIIF v2 compatibility
    return JSONResponse(content=manifest)


# ── Collections ────────────────────────────────────────────────────────────────

@app.put("/collections/{item_id}")
def put_collection(
    item_id: str,
    request: Request,
    manifest: dict = Body(...),
    authorization: str | None = Header(default=None),
):
    """
    Store a full IIIF Collection JSON document.
    Requires a valid Bearer token in the Authorization header.
    The item_id becomes the Mongo _id, and the manifest's id field
    is set to the full URL of this endpoint.
    """
    verify_token(authorization)
    base_url = str(request.base_url).rstrip("/")
    full_id = f"{base_url}/collections/{item_id}"
    manifest["_id"] = item_id
    manifest["id"] = full_id    # IIIF v3
    manifest["@id"] = full_id   # IIIF v2 compatibility
    collections_coll.replace_one({"_id": item_id}, manifest, upsert=True)
    return {"success": True, "id": full_id}


@app.get("/collections/{item_id}")
def get_collection(item_id: str, request: Request):
    """
    Return the stored IIIF collection JSON, with id reflecting the live request URL.
    """
    manifest = collections_coll.find_one({"_id": item_id})
    if not manifest:
        raise HTTPException(status_code=404, detail="Collection not found")
    base_url = str(request.base_url).rstrip("/")
    full_id = f"{base_url}/collections/{item_id}"
    manifest.pop("_id", None)
    manifest["id"] = full_id    # IIIF v3
    manifest["@id"] = full_id   # IIIF v2 compatibility
    return JSONResponse(content=manifest)
