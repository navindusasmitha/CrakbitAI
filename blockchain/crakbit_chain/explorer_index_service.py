from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

from .explorer_index import ExternalExplorerIndex
from .genesis import Genesis


@dataclass(frozen=True)
class ExplorerIndexConfig:
    genesis_path: str = "runtime/genesis.json"
    source_data_dir: str = "runtime/comet-app"
    index_path: str = "runtime/explorer-index.sqlite3"
    sync_interval_seconds: float = 2.0

    @classmethod
    def from_env(cls) -> "ExplorerIndexConfig":
        value = cls(
            genesis_path=os.environ.get("CRAKBIT_EXPLORER_GENESIS", "runtime/genesis.json"),
            source_data_dir=os.environ.get("CRAKBIT_EXPLORER_SOURCE_DATA", "runtime/comet-app"),
            index_path=os.environ.get("CRAKBIT_EXPLORER_INDEX", "runtime/explorer-index.sqlite3"),
            sync_interval_seconds=float(os.environ.get("CRAKBIT_EXPLORER_SYNC_SECONDS", "2")),
        )
        value.validate()
        return value

    def validate(self) -> None:
        if not Path(self.genesis_path).is_file():
            raise ValueError("explorer genesis file was not found")
        if self.sync_interval_seconds < 0.25 or self.sync_interval_seconds > 300:
            raise ValueError("explorer sync interval must be between 0.25 and 300 seconds")


def create_app(config: ExplorerIndexConfig | None = None) -> FastAPI:
    config = config or ExplorerIndexConfig.from_env()
    genesis = Genesis.load(config.genesis_path)
    index = ExternalExplorerIndex(config.index_path, genesis)
    app = FastAPI(title="Crakbit External Explorer Index", version="0.16.0a1")
    app.state.index = index
    app.state.last_sync = None
    app.state.sync_error = None

    async def sync_loop() -> None:
        while True:
            try:
                app.state.last_sync = await asyncio.to_thread(
                    index.sync_from_source,
                    config.source_data_dir,
                )
                app.state.sync_error = None
            except Exception as exc:  # surfaced through health; loop continues for recovery
                app.state.sync_error = f"{type(exc).__name__}: {exc}"
            await asyncio.sleep(config.sync_interval_seconds)

    @app.on_event("startup")
    async def startup() -> None:
        app.state.sync_task = asyncio.create_task(sync_loop())

    @app.on_event("shutdown")
    async def shutdown() -> None:
        task = getattr(app.state, "sync_task", None)
        if task is not None:
            task.cancel()

    @app.get("/health")
    def health() -> dict:
        summary = index.summary()
        return {
            "ok": app.state.sync_error is None,
            "version": app.version,
            "source_data_dir": config.source_data_dir,
            "index_path": config.index_path,
            "sync_interval_seconds": config.sync_interval_seconds,
            "last_sync": app.state.last_sync,
            "sync_error": app.state.sync_error,
            "summary": summary,
            "production_ready": False,
        }

    @app.post("/sync")
    def sync_now() -> dict:
        try:
            result = index.sync_from_source(config.source_data_dir)
            app.state.last_sync = result
            app.state.sync_error = None
            return result
        except Exception as exc:
            app.state.sync_error = f"{type(exc).__name__}: {exc}"
            raise HTTPException(503, app.state.sync_error) from exc

    @app.get("/summary")
    def summary() -> dict:
        return index.summary()

    @app.get("/commits")
    def commits(limit: int = Query(default=20, ge=1, le=100)) -> dict:
        items = index.recent_commits(limit)
        return {"count": len(items), "items": items}

    @app.get("/transaction/{txid}")
    def transaction(txid: str) -> dict:
        result = index.transaction(txid.strip().lower())
        if result is None:
            raise HTTPException(404, "transaction not found in explorer index")
        return result

    @app.get("/account/{address}")
    def account(address: str, limit: int = Query(default=50, ge=1, le=100)) -> dict:
        return index.account(address.strip().lower(), limit)

    return app


app = create_app()
