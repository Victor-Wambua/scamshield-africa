# Offline evaluation of the message analysis engine

**All data is SYNTHETIC and written by the engineers who wrote the rules**, so scores are optimistic regression guards, not real-world accuracy. Dataset: `app/evaluation/dataset.jsonl` (218 items: 178 template-generated English/Swahili messages, 40 blind hand-written hold-out; origin "synthetic test data"). Reproduce: `uv run python -m scamshield evaluate`.

Method: positive = engine label "several" or "some" warning signs. Thresholds and rule tweaks (removing a bare "congratulations" trigger, ignoring "never share your PIN" warnings, requiring a verb for till/paybill, T_SOME 0.30) were made while looking at the dev/test splits, so those are NOT clean held-out sets. The 40-item hold-out was written after freezing the rules and run once.

| Split | n | Precision | Recall | F1 | TP/FP/FN/TN |
|---|---|---|---|---|---|
| dev | 89 | 1.000 | 1.000 | 1.000 | 50/0/0/39 |
| test (seen during tuning) | 89 | 1.000 | 1.000 | 1.000 | 51/0/0/38 |
| hold-out (blind) | 40 | 0.952 | 1.000 | 0.976 | 20/1/0/19 |
| all | 218 | 0.992 | 1.000 | 0.996 | 121/1/0/96 |

Hold-out confusion (true -> engine label): benign -> few 19, benign -> some 1; suspicious -> several 9, some 11. The one false positive: a benign bank message saying "confirm your account details by visiting the branch". Recall is likely overstated because the author wrote the scam wording; expect misses on novel scams. A real evaluation needs consented, independently labelled messages.
