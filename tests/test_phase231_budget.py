"""Deterministic latency experiments; refund delays are assumptions, never live measurements."""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx
import pytest
from test_phase23_preflight import MockRefundHTTP
from test_phase231_deadlines import prepare_refund
from test_providers import sandbox_settings

from refund_sentinel import integration
from refund_sentinel.integration import RefundExecutor, composition, provision
from refund_sentinel.paypal import SandboxPayPal

PROFILES = {
    "warm_mid": (False, 0.8, 0.8, "Succeeded"),
    "warm_edge": (False, 1.3, 1.3, "Succeeded"),
    "cold_mid": (True, 0.8, 0.8, "Succeeded"),
    "cold_edge": (True, 1.3, 1.3, "Unknown"),
    "warm_tail": (False, 2.0, 1.4, "Unknown"),
    "warm_over_budget": (False, 2.5, 2.0, "Unknown"),
}


def existing_read_observations():
    reports = [
        Path("evidence/phase-2.3/readonly-real.json"),
        Path("evidence/phase-2.3/real-model-plan.json"),
    ]
    result = []
    for path in reports:
        data = json.loads(path.read_text("utf-8"))
        requests = data.get("requests", data.get("pay_pal_requests"))
        result.append(
            {
                row["operation"]: row["elapsed_seconds"]
                for row in requests
                if row["operation"] in {"oauth", "capture_get", "order_get"}
            }
        )
    return result


@pytest.mark.parametrize("profile_name", PROFILES)
@pytest.mark.parametrize("read_mode", ["serial_reference", "parallel_current"])
def test_full_five_second_path_distribution(tmp_path, monkeypatch, profile_name, read_mode):
    async def run():
        trials = []
        cold, post_delay, get_delay, expected = PROFILES[profile_name]
        if read_mode == "parallel_current" and profile_name != "warm_over_budget":
            expected = "Succeeded"
        for index, observations in enumerate(existing_read_observations()):
            directory = tmp_path / f"trial-{index}"
            settings = sandbox_settings()
            provision(directory, settings)
            delays = observations | {"refund_post": post_delay, "refund_get": get_delay}
            network = MockRefundHTTP(directory / "mock.sqlite3", "completed", delays=delays)

            class ObservedExecutor(RefundExecutor):
                observed_http = network

                async def execute(self, spec, effect_key, context):
                    self.observed_http.context_deadline = context.deadline
                    return await super().execute(spec, effect_key, context)

            monkeypatch.setattr(integration, "RefundExecutor", ObservedExecutor)

            class ReferenceClient(SandboxPayPal):
                async def capture(self, capture_id, *, expected_order_id=None):
                    hint = expected_order_id if read_mode == "parallel_current" else None
                    return await super().capture(capture_id, expected_order_id=hint)

            client = ReferenceClient(settings, transport=httpx.MockTransport(network.handle))
            timings, starts = [], {}

            def profile(frame, event, arg, starts=starts, timings=timings):
                filename, name = frame.f_code.co_filename, frame.f_code.co_name
                selected = (
                    (
                        filename.endswith("sqlite_action_execution.py")
                        and name in {"claim", "finish"}
                    )
                    or (
                        filename.endswith("refund_sentinel\\store.py")
                        and name in {"get", "observe"}
                    )
                    or (
                        filename.endswith("refund_sentinel/store.py") and name in {"get", "observe"}
                    )
                    or (filename.endswith("integration.py") and name == "validate_arguments")
                )
                if selected and event == "call":
                    starts[id(frame)] = time.perf_counter()
                elif selected and event == "return":
                    timings.append(
                        {"operation": name, "seconds": time.perf_counter() - starts.pop(id(frame))}
                    )

            with composition(
                directory, settings, paypal=client, predecessor_stopped=True
            ) as resources:
                runtime, store, _, model, _ = resources
                principal, command = await prepare_refund(
                    runtime, store, client, model, settings, directory
                )
                assert network.post_count() == 0
                if cold:
                    client._until = 0
                telemetry_start = len(client.telemetry)
                network.executing = True
                network.started = time.perf_counter()
                previous = sys.getprofile()
                try:
                    sys.setprofile(profile)
                    result = await runtime.gateway.execute(
                        command, principal, deadline=asyncio.get_running_loop().time() + 30
                    )
                finally:
                    sys.setprofile(previous)
                wall = time.perf_counter() - network.started
                assert result.action.state.value == expected
                assert runtime.actions.get(command.action_id).state.value == expected
                assert network.post_count() == len(network.effects()) == 1
                assert not network.dispatch_after_deadline
                assert (await runtime.gateway.execute(command, principal)).replayed
                assert network.post_count() == 1
                trials.append(
                    {
                        "observed_read_pair": index,
                        "source": "EXISTING_REAL_READ_LATENCIES_AND_ASSUMED_REFUND_DELAYS",
                        "cold_oauth": cold,
                        "read_mode": read_mode,
                        "requested_delays_seconds": delays,
                        "refund_delays_are_hypothetical": True,
                        "action_state": expected,
                        "gateway_wall_seconds": round(wall, 6),
                        "runtime_adapter_limit_seconds": runtime.gateway.tool_timeout_seconds,
                        "caller_deadline_seconds": 30,
                        "requests": client.telemetry[telemetry_start:],
                        "local_timings": timings,
                        "local_timings_overlap": "validation includes read; timings overlap",
                        "refund_posts": network.post_count(),
                        "duplicate_dispatch": False,
                        "late_dispatch": False,
                    }
                )
            await client.close()
        (tmp_path / "budget-evidence.json").write_text(
            json.dumps(
                {"profile": profile_name, "read_mode": read_mode, "trials": trials}, indent=2
            ),
            "utf-8",
        )

    asyncio.run(run())
