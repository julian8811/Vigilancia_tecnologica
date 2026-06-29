"""Tests for app.tasks.safe (the S5 background-task wrapper)."""

from __future__ import annotations

import asyncio

import pytest

from app.tasks.safe import safe_background_task


@pytest.mark.asyncio
async def test_safe_background_task_runs_coro_to_completion():
    """A coroutine wrapped in safe_background_task runs to completion."""
    completed = asyncio.Event()

    async def coro():
        completed.set()
        return "ok"

    task = safe_background_task(coro, task_name="test_completion")
    await asyncio.wait_for(completed.wait(), timeout=2)
    assert completed.is_set()
    # Drain the task so it doesn't leak.
    await task


@pytest.mark.asyncio
async def test_safe_background_task_swallows_exceptions():
    """A coroutine that raises is logged but does NOT propagate the error.

    The user already got their 200 response from the request that
    scheduled the task; if the background failure propagated it would
    crash the event loop.
    """
    async def coro():
        raise RuntimeError("background failure")

    task = safe_background_task(coro, task_name="test_swallows")
    # Wait for the task to finish without re-raising.
    await asyncio.wait_for(task, timeout=2)
    # If we got here, the exception was swallowed as expected.
    assert task.done()
    # The outer task is _runner() which itself did NOT raise (it caught
    # the exception in the inner try/except), so task.exception() is None.
    # The original RuntimeError is logged but does not surface.
    assert task.exception() is None


@pytest.mark.asyncio
async def test_safe_background_task_inner_coro_did_raise():
    """The inner coroutine is the one that raised; we can't easily observe
    it from the outer Task handle, but we can verify the call returned
    cleanly (no exception propagated to the test)."""
    raised = asyncio.Event()

    async def coro():
        try:
            raise ValueError("expected")
        except ValueError:
            raised.set()

    task = safe_background_task(coro, task_name="test_inner_raised")
    await asyncio.wait_for(task, timeout=2)
    assert raised.is_set()
    assert task.exception() is None  # coro caught its own exception


@pytest.mark.asyncio
async def test_safe_background_task_forwards_args_and_kwargs():
    """Positional and keyword arguments are forwarded to the coroutine."""
    captured: dict = {}

    async def coro(pos_a, pos_b, *, kw_a=None, kw_b=None):
        captured["pos_a"] = pos_a
        captured["pos_b"] = pos_b
        captured["kw_a"] = kw_a
        captured["kw_b"] = kw_b

    task = safe_background_task(
        coro, "alpha", 42, kw_a="beta", kw_b=99, task_name="test_args",
    )
    await asyncio.wait_for(task, timeout=2)
    assert captured == {"pos_a": "alpha", "pos_b": 42, "kw_a": "beta", "kw_b": 99}


@pytest.mark.asyncio
async def test_safe_background_task_uses_qualname_as_default_task_name():
    """Without an explicit task_name, the function's qualname is used."""

    async def my_named_coro():
        pass

    task = safe_background_task(my_named_coro)
    assert task.get_name().endswith("my_named_coro")
    await task
