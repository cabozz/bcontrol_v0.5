import asyncio
import uvicorn

from app import create_app
from app.config import settings
from app.db import init_db_pool
from app.tcp_server import start_tcp_server
from app.poller import alive_poller


async def main():
    # 1) Init DB pool and schema
    await init_db_pool()

    # 2) Create FastAPI app
    app = create_app()

    # 3) Start both TCP server and API in same event loop
    config = uvicorn.Config(app, host=settings.API_HOST, port=settings.API_PORT, loop="asyncio")
    server = uvicorn.Server(config)

    await asyncio.gather(
        start_tcp_server(),
        server.serve(),
        alive_poller(),
    )


if __name__ == "__main__":
    asyncio.run(main())
