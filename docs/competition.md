# PayPal AI Hackathon submission preparation

The [official overview](https://paypalaihackathon.devpost.com/) and
[rules](https://paypalaihackathon.devpost.com/rules) were checked on 14 October 2026.
The deadline is **12 November 2026, 12:00 PST**, equivalent to **13 November,
09:00 NZDT**. Check the official pages again before submission.

The entry must meaningfully combine PayPal Sandbox with AI, provide a functioning
build and complete run instructions or a hosted demo, and link a public open-source
repository with a visible license. A public YouTube demonstration under three
minutes must show the application working. Materials must be English or translated.
Existing projects need significant progress during the competition; reused software
remains subject to its license. Eligibility and access through judging are the
entrant's responsibility. These requirements come from the linked official rules.

Judging criteria are equally weighted: Technological Implementation, Design,
Potential Impact, Innovation/Idea and Presentation. Sponsor tools are optional
unless pursuing an award with specific sponsor requirements.

## This project's contribution

Refund Sentinel contributes the merchant workflow, strict recommendation schema,
real local Ollama provider, deterministic policy, Sandbox API adapter, consumer
executor/observations, isolated five-screen presentation and regression suites.
Agentic Intent Gate is reused externally at a fixed MIT-licensed v0.2.0 Git release;
its execution framework is not copied into the submission.

The genuine [historical Sandbox proof](../evidence/phase2-freeze/verified-refund.json)
records a NZD 5.00 partial refund verified COMPLETED with a durable Receipt and one
observed POST. The interactive UI separately runs genuine local Ollama on synthetic
input, while financial execution remains FakePayPal. A deterministic fallback is
clearly labeled. Simulation alone is not presented as proof of Sandbox integration.

Judges can run the credential-free [local presentation](PHASE3-UI-DEMO.md).
The README identifies Python 3.13, Git dependency access and optional Ollama setup.
No private PayPal credentials or historical grants need to be shared to run it.

## Remaining entrant work

Rehearse the [English demo script](DEMO-SCRIPT.md), record and publish the under-three-
minute video, verify entrant eligibility/rights, maintain judge access, and complete
the final entry. No recording, upload, hosted deployment or Devpost submission is
claimed completed by repository cleanup.

## Primary integration references

- [PayPal OAuth](https://developer.paypal.com/api/rest/authentication/)
- [Capture GET](https://developer.paypal.com/api/payments/v2/captures-get) and
  [Order GET](https://developer.paypal.com/api/orders/v2/orders-get)
- [Partial Refund POST](https://developer.paypal.com/api/payments/v2/captures-refund)
  and [Refund GET](https://developer.paypal.com/api/payments/v2/refunds-get)
- [PayPal idempotency](https://developer.paypal.com/api/rest/reference/idempotency/)
- [Ollama OpenAI compatibility](https://docs.ollama.com/api/openai-compatibility)
- [Pinned Runtime adapter guide](https://github.com/miku-wwl/agentic-intent-gate/blob/7261fdd2f47d2b15fabe8faac527eeee37338eb1/docs/ADAPTER_GUIDE.md)
