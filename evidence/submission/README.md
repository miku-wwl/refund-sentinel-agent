# Curated submission evidence

The [immutable sanitized PayPal proof](../phase2-freeze/verified-refund.json)
records one genuine NZD 5.00 Sandbox partial refund from a completed NZD 20.00
payment: Refund POST **201**, independent Refund GET **200 / COMPLETED**, one
observed POST, Succeeded v4 and durable historical Receipt. Its observed time is
13 October 2026. Viewing this archive makes no current PayPal query and establishes
neither today's refund balance nor universal exactly-once delivery.

The four files in `phase2-freeze/` are unchanged historical integrity contracts.
The two files in `phase-2.3/` are sanitized historical read-latency inputs actually
consumed by offline regression tests; their presence never causes network access.

The [final qualification summary](qa-summary.json) identifies its actual tested code
commit, fresh model inference, clean installation and mock/simulation boundaries.
[Screenshot hashes](screenshots-manifest.json) cover the original representative
pre-cleanup image bytes; the UI source is unchanged and was revalidated after cleanup.
Screenshots represent multiple isolated synthetic or read-only historical sessions,
not another PayPal transaction. Their displayed model time is their own observation,
not the later qualification run's measurement.

| Capture | Purpose |
| --- | --- |
| [Overview](overview.png) | Product entry and archived genuine result |
| [Local AI proposal](local-ai-proposal.png) | Genuine `phi4-mini` proposal; payment stays simulated |
| [Approval](approve-plan.jpg) | Exact synthetic Plan confirmation |
| [Authorization](authorize-action.jpg) | Separate synthetic Action grant |
| [Execute Simulation](execute-simulation.jpg) | Third independent one-time simulation permission |
| [Simulated Receipt](simulated-receipt.jpg) | Durable local fake-provider result |
| [Historical evidence](historical-evidence.png) | Archived PayPal HTTP results and Receipt provenance |
| [Mobile review](mobile-review.png) | Corrected narrow-screen payment facts |

[Deletion manifest](cleanup-manifest.json) records every removed public evidence
path, checked references and replacement/archive. Superseded safe artifacts remain
in the pinned [pre-cleanup checkpoint](https://github.com/miku-wwl/refund-sentinel-agent/tree/86a179fc6ca02568a849c51e765d6dca123dced7).
Original private financial state, raw provider records and local diagnostics are
retained locally and are not part of these public artifacts.
