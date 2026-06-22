"""ADAM OS entrypoint."""
import uvicorn

from ADAM.core.app import create_app

app = create_app()

if __name__ == "__main__":
    uvicorn.run(
        "ADAM.main:app",
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )
