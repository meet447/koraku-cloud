"""Run the Koraku SDK HTTP server (self-host / embed)."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("koraku.server_sdk:app", host="0.0.0.0", port=8000, reload=True)
