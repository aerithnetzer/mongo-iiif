import os
from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.responses import JSONResponse
from pymongo import MongoClient

app = FastAPI()
client = MongoClient(os.getenv("MONGODB_OCR_DEVELOPMENT_CONN_STRING_IMPULSE"))
db = client["iiif"]
coll = db["works"]

@app.put("/works/{item_id}")
def put_manifest(item_id: str, request: Request, manifest: dict = Body(...)):
    """
    Store a full IIIF Manifest JSON document.
    The item_id becomes the Mongo _id, and the manifest's id field
    is set to the full URL of this endpoint.
    """
    base_url = str(request.base_url).rstrip("/")
    full_id = f"{base_url}/works/{item_id}"

    manifest["_id"] = item_id
    manifest["id"] = full_id  # IIIF v3
    manifest["@id"] = full_id  # IIIF v2 compatibility

    coll.replace_one({"_id": item_id}, manifest, upsert=True)
    return {"success": True, "id": full_id}

@app.get("/works/{item_id}")
def get_manifest(item_id: str, request: Request):
    """
    Return the stored IIIF manifest JSON, with id reflecting the live request URL.
    """
    manifest = coll.find_one({"_id": item_id})
    if not manifest:
        raise HTTPException(status_code=404, detail="Manifest not found")

    base_url = str(request.base_url).rstrip("/")
    full_id = f"{base_url}/works/{item_id}"

    manifest.pop("_id", None)
    manifest["id"] = full_id   # IIIF v3
    manifest["@id"] = full_id  # IIIF v2 compatibility

    return JSONResponse(content=manifest)
