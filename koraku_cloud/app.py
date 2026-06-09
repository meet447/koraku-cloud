"""Koraku Cloud product FastAPI app — SDK routes plus Supabase-backed product APIs."""
from __future__ import annotations

from koraku_cloud.bootstrap import bootstrap_cloud

bootstrap_cloud()

from koraku_cloud.api.admin_routes import router as admin_router
from koraku_cloud.api.automation_events_routes import router as automation_events_router
from koraku_cloud.api.composio_trigger_events_routes import router as composio_trigger_events_router
from koraku_cloud.api.automations_routes import router as automations_router
from koraku_cloud.api.detached_runs import router as detached_runs_router
from koraku_cloud.api.memory_routes import router as memory_router
from koraku_cloud.api.personalization_routes import router as personalization_router
from koraku_cloud.api.profile_routes import router as profile_router
from koraku_cloud.api.skills_routes import router as skills_router
from koraku_cloud.api.sendblue_routes import router as sendblue_router
from koraku_cloud.api.workspace_routes import router as workspace_router
from koraku.api.usage_routes import router as usage_router
from koraku.server_sdk import create_sdk_app

# Re-export startup agent for tests.
from koraku.server_sdk import _AGENT, _MODE  # noqa: F401


def create_cloud_app():
    from fastapi import FastAPI

    app: FastAPI = create_sdk_app(
        enable_automation_scheduler=True,
        index_variant="cloud",
    )
    app.include_router(admin_router)
    app.include_router(detached_runs_router)
    app.include_router(personalization_router)
    app.include_router(profile_router)
    app.include_router(skills_router)
    app.include_router(memory_router)
    app.include_router(automations_router)
    app.include_router(automation_events_router)
    app.include_router(composio_trigger_events_router)
    app.include_router(workspace_router)
    app.include_router(sendblue_router)
    app.include_router(usage_router)
    return app


app = create_cloud_app()
