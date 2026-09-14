"""Ishga tushirish: python run.py  (yoki: uvicorn app.main:app --reload --port 8080)"""
import os, sys
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("AQ_PORT", "8080"))
    uvicorn.run("app.main:app", host="127.0.0.1", port=port, reload="--reload" in sys.argv)
