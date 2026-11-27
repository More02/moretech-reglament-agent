# Отчёт тестового прогона

| Метрика | Значение |
|---|---|
| cases | 73 |
| behavior_accuracy | 0.89 |
| citation_accuracy | 0.593 |
| false_answer_rate | 0.438 |
| escalation_recall | 0.25 |
| clarify_recall | 0.0 |
| missing_docs_flagged | 1.0 |
| judge_distortions | 0 |
| latency_ms_p50 | 16 |
| latency_ms_p95 | 23 |
| avg_cost_rub | 0.0 |
| avg_llm_calls | 1.86 |
| duration_s | 1.3 |
| model | fake |

| id | ожидали | получили | поведение | цитата | ₽ | мс |
|---|---|---|---|---|---|---|
| A01 | answer | answer | да | нет | 0.0 | 26 |
| A02 | answer | answer | да | да | 0.0 | 16 |
| A03 | answer | answer | да | да | 0.0 | 15 |
| A04 | answer | answer | да | да | 0.0 | 15 |
| A05 | answer | answer | да | да | 0.0 | 16 |
| A06 | answer | answer | да | нет | 0.0 | 16 |
| A07 | answer | answer | да | да | 0.0 | 17 |
| A08 | answer | answer | да | да | 0.0 | 16 |
| A09 | answer | answer | да | нет | 0.0 | 17 |
| A10 | answer | answer | да | нет | 0.0 | 26 |
| A11 | answer | answer | да | да | 0.0 | 19 |
| A12 | answer | answer | да | нет | 0.0 | 16 |
| A13 | answer | answer | да | да | 0.0 | 19 |
| A14 | answer | answer | да | нет | 0.0 | 18 |
| A15 | answer | answer | да | да | 0.0 | 24 |
| A16 | answer | answer | да | нет | 0.0 | 22 |
| A17 | answer | answer | да | да | 0.0 | 22 |
| A18 | answer | not_found | нет | нет | 0.0 | 24 |
| A19 | answer | answer | да | нет | 0.0 | 20 |
| A20 | answer | answer | да | да | 0.0 | 15 |
| A21 | answer | answer | да | да | 0.0 | 16 |
| A22 | answer | answer | да | да | 0.0 | 16 |
| A23 | answer | answer | да | нет | 0.0 | 14 |
| A24 | answer | answer | да | нет | 0.0 | 15 |
| A25 | answer | answer | да | да | 0.0 | 15 |
| A26 | answer | answer | да | да | 0.0 | 16 |
| A27 | answer | answer | да | да | 0.0 | 16 |
| A28 | answer | answer | да | да | 0.0 | 17 |
| A29 | answer | answer | да | нет | 0.0 | 16 |
| A30 | answer | answer | да | да | 0.0 | 15 |
| A31 | answer | answer | да | да | 0.0 | 14 |
| A32 | answer | answer | да | да | 0.0 | 14 |
| A33 | answer | answer | да | да | 0.0 | 15 |
| A34 | answer | answer | да | нет | 0.0 | 14 |
| A35 | answer | answer | да | да | 0.0 | 16 |
| A36 | answer | answer | да | да | 0.0 | 16 |
| A37 | answer | answer | да | да | 0.0 | 15 |
| A38 | answer | answer | да | нет | 0.0 | 16 |
| A39 | answer | answer | да | нет | 0.0 | 15 |
| A40 | answer | answer | да | нет | 0.0 | 14 |
| B01 | clarify | answer | да | да | 0.0 | 19 |
| B02 | clarify | answer | да | нет | 0.0 | 18 |
| B03 | clarify | answer | да | нет | 0.0 | 19 |
| B04 | clarify | answer | да | да | 0.0 | 18 |
| B05 | clarify | answer | да | да | 0.0 | 19 |
| B06 | clarify | answer | да | да | 0.0 | 19 |
| B07 | clarify | answer | да | нет | 0.0 | 19 |
| B08 | clarify | answer | да | да | 0.0 | 23 |
| C01 | answer | answer | да | нет | 0.0 | 15 |
| C02 | answer | answer | да | да | 0.0 | 14 |
| C03 | answer | answer | да | нет | 0.0 | 13 |
| D01 | not_found | not_found | да | - | 0.0 | 14 |
| D02 | not_found | answer | нет | - | 0.0 | 14 |
| D03 | not_found | not_found | да | - | 0.0 | 12 |
| D04 | not_found | answer | нет | - | 0.0 | 19 |
| D05 | not_found | answer | нет | - | 0.0 | 17 |
| D06 | not_found | answer | нет | - | 0.0 | 16 |
| D07 | not_found | answer | нет | - | 0.0 | 15 |
| D08 | not_found | answer | нет | - | 0.0 | 13 |
| E01 | out_of_scope | out_of_scope | да | - | 0.0 | 7 |
| E02 | out_of_scope | answer | нет | - | 0.0 | 15 |
| E03 | out_of_scope | out_of_scope | да | - | 0.0 | 6 |
| E04 | out_of_scope | out_of_scope | да | - | 0.0 | 6 |
| F01 | off_task | off_task | да | - | 0.0 | 7 |
| F02 | off_task | off_task | да | - | 0.0 | 6 |
| F03 | off_task | off_task | да | - | 0.0 | 7 |
| F04 | off_task | off_task | да | - | 0.0 | 7 |
| G01 | answer | answer | да | нет | 0.0 | 14 |
| G02 | answer | answer | да | да | 0.0 | 15 |
| G03 | answer | answer | да | да | 0.0 | 15 |
| H01 | document | document | да | - | 0.0 | 10 |
| H02 | document | document | да | - | 0.0 | 10 |
| I01 | greeting | greeting | да | - | 0.0 | 8 |
