"""
EX Agent Gateway & Multi-Channel Daemon.
Hosts OpenAI-compatible API server (:8642), embedded cron scheduler,
and external messaging bridges (Telegram, Discord, Slack).
"""
from ex_agent.gateway.server import create_gateway_app, run_gateway
from ex_agent.gateway.scheduler import CronScheduler

__all__ = ["create_gateway_app", "run_gateway", "CronScheduler"]
