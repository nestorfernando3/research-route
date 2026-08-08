# Research Route Slim v2 efficiency replay

Date: 2026-08-08

## Method

A temporary project ran five equivalent routine tasks twice. The schema-v1 path used `init`, one `new`, `claim`, and `complete` per task, followed by `handoff` and structural `validate`. The schema-v2 path used `init`, one `advance --review-later` per task, followed by grouped `review --stage argument` and `validate --checkpoint argument`.

The comparison measured CLI invocations and wall-clock time. It did not compare scholarly quality, source verification, or publication readiness.

## Result

| Path | CLI invocations | Wall-clock time |
| --- | ---: | ---: |
| v1 detailed | 18 | 1.141 s |
| v2 adaptive | 8 | 0.518 s |

The adaptive path reduced invocations by 55.6% and elapsed time by 54.6% in this local synthetic replay. Critical work remained non-deferrable, and the argument review reported all deferred work together.

This result verifies the mechanics of the short path. Replays over PAIDEIA, *Suicidal Empathy*, fascism, and a multi-article project remain necessary before generalizing the percentage to scholarly workflows.
