# Отчёт тестового прогона

| Метрика | Значение |
|---|---|
| cases | 73 |
| behavior_accuracy | 0.932 |
| citation_accuracy | 0.906 |
| false_answer_rate | 0.0 |
| escalation_recall | 0.875 |
| clarify_recall | 0.875 |
| missing_docs_flagged | 1.0 |
| judge_distortions | 0 |
| latency_ms_p50 | 11036 |
| latency_ms_p95 | 19759 |
| avg_cost_rub | 0.714 |
| avg_llm_calls | 1.82 |
| duration_s | 835.6 |
| model | qwen3.6-35b-a3b |

| id | ожидали | получили | поведение | цитата | ₽ | мс |
|---|---|---|---|---|---|---|
| A01 | answer | answer | да | да | 0.8219 | 13222 |
| A02 | answer | answer | да | да | 0.834 | 12095 |
| A03 | answer | answer | да | да | 0.8331 | 10253 |
| A04 | answer | answer | да | да | 0.5451 | 9452 |
| A05 | answer | answer | да | да | 1.2074 | 19759 |
| A06 | answer | answer | да | да | 1.0989 | 14789 |
| A07 | answer | answer | да | да | 0.4964 | 8281 |
| A08 | answer | answer | да | да | 0.641 | 9181 |
| A09 | answer | answer | да | да | 0.9177 | 13319 |
| A10 | answer | answer | да | да | 0.5382 | 10880 |
| A11 | answer | answer | да | да | 0.9359 | 15310 |
| A12 | answer | answer | да | да | 0.5347 | 11231 |
| A13 | answer | answer | да | да | 0.1883 | 4514 |
| A14 | answer | answer | да | да | 0.9778 | 12137 |
| A15 | answer | answer | да | да | 0.7849 | 11717 |
| A16 | answer | answer | да | да | 0.8079 | 10163 |
| A17 | answer | answer | да | да | 1.0635 | 12691 |
| A18 | answer | answer | да | да | 0.5392 | 9235 |
| A19 | answer | answer | да | да | 1.39 | 19810 |
| A20 | answer | answer | да | да | 0.5385 | 7870 |
| A21 | answer | answer | да | нет | 1.2065 | 19120 |
| A22 | answer | answer | да | да | 0.6691 | 11036 |
| A23 | answer | answer | да | да | 0.4899 | 10196 |
| A24 | answer | answer | да | да | 0.217 | 6016 |
| A25 | answer | answer | да | да | 1.0304 | 12372 |
| A26 | answer | answer | да | да | 1.1582 | 18013 |
| A27 | answer | answer | да | да | 0.5592 | 9880 |
| A28 | answer | answer | да | да | 1.1968 | 16160 |
| A29 | answer | answer | да | да | 0.657 | 11188 |
| A30 | answer | answer | да | да | 1.0919 | 15354 |
| A31 | answer | answer | да | да | 1.0594 | 12225 |
| A32 | answer | answer | да | да | 1.0132 | 12469 |
| A33 | answer | out_of_scope | нет | нет | 0.3961 | 4948 |
| A34 | answer | answer | да | да | 0.1683 | 4359 |
| A35 | answer | answer | да | да | 0.4897 | 9350 |
| A36 | answer | not_found | нет | нет | 0.1993 | 5143 |
| A37 | answer | not_found | нет | нет | 0.9829 | 13037 |
| A38 | answer | answer | да | да | 0.929 | 13948 |
| A39 | answer | answer | да | да | 0.5404 | 9176 |
| A40 | answer | answer | да | да | 0.7893 | 9778 |
| B01 | clarify | clarify | да | да | 1.106 | 16468 |
| B02 | clarify | answer | нет | - | 0.7974 | 15610 |
| B03 | clarify | clarify | да | да | 0.8847 | 12615 |
| B04 | clarify | clarify | да | да | 0.6739 | 15743 |
| B05 | clarify | clarify | да | да | 1.5488 | 38665 |
| B06 | clarify | clarify | да | да | 0.6477 | 18790 |
| B07 | clarify | clarify | да | да | 1.8454 | 19174 |
| B08 | clarify | clarify | да | да | 1.5618 | 16711 |
| C01 | answer | answer | да | нет | 0.633 | 11518 |
| C02 | answer | answer | да | да | 0.7105 | 12073 |
| C03 | answer | answer | да | да | 0.2572 | 8001 |
| D01 | not_found | not_found | да | - | 0.5236 | 9305 |
| D02 | not_found | not_found | да | - | 0.8232 | 9324 |
| D03 | not_found | not_found | да | - | 0.9413 | 12186 |
| D04 | not_found | not_found | да | - | 0.8212 | 9996 |
| D05 | not_found | not_found | да | - | 0.7351 | 8821 |
| D06 | not_found | out_of_scope | нет | - | 0.3748 | 6109 |
| D07 | not_found | not_found | да | - | 0.4735 | 15984 |
| D08 | not_found | not_found | да | - | 0.7205 | 11847 |
| E01 | out_of_scope | out_of_scope | да | - | 0.055 | 2466 |
| E02 | out_of_scope | out_of_scope | да | - | 0.4269 | 5868 |
| E03 | out_of_scope | out_of_scope | да | - | 0.3381 | 4440 |
| E04 | out_of_scope | out_of_scope | да | - | 0.35 | 8513 |
| F01 | off_task | off_task | да | - | 0.0516 | 1909 |
| F02 | off_task | off_task | да | - | 0.3084 | 8644 |
| F03 | off_task | off_task | да | - | 0.3487 | 10179 |
| F04 | off_task | off_task | да | - | 0.393 | 4760 |
| G01 | answer | answer | да | да | 0.2128 | 6008 |
| G02 | answer | answer | да | да | 1.3711 | 24578 |
| G03 | answer | answer | да | да | 1.1684 | 20589 |
| H01 | document | document | да | - | 0.0581 | 1693 |
| H02 | document | document | да | - | 0.3708 | 5505 |
| I01 | greeting | greeting | да | - | 0.0537 | 1621 |
