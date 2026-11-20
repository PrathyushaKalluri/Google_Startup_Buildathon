"""Start Circuit:  python run.py   then open http://localhost:8000"""
import uvicorn
if __name__ == "__main__":
    uvicorn.run("circuit.app:app", host="127.0.0.1", port=8000)
