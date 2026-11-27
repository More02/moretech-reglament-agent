# Отчёт тестового прогона

| Метрика | Значение |
|---|---|
| cases | 73 |
| behavior_accuracy | 0.973 |
| citation_accuracy | 0.926 |
| false_answer_rate | 0.0 |
| escalation_recall | 0.875 |
| clarify_recall | 1.0 |
| missing_docs_flagged | 0.667 |
| judge_distortions | 0 |
| latency_ms_p50 | 4402 |
| latency_ms_p95 | 5354 |
| avg_cost_rub | 0.1884 |
| avg_llm_calls | 2.08 |
| duration_s | 292.6 |
| model | qwen3.6-35b-a3b |

| id | ожидали | получили | поведение | цитата | ₽ | мс |
|---|---|---|---|---|---|---|
| A01 | answer | answer | да | да | 0.1617 | 4879 |
| A02 | answer | answer | да | да | 0.1703 | 4980 |
| A03 | answer | answer | да | да | 0.1687 | 4648 |
| A04 | answer | answer | да | да | 0.1751 | 4982 |
| A05 | answer | answer | да | да | 0.1874 | 4987 |
| A06 | answer | answer | да | нет | 0.1883 | 5056 |
| A07 | answer | answer | да | да | 0.1737 | 3821 |
| A08 | answer | answer | да | да | 0.1867 | 4402 |
| A09 | answer | answer | да | да | 0.1557 | 3482 |
| A10 | answer | answer | да | да | 0.1709 | 4115 |
| A11 | answer | answer | да | да | 0.1859 | 4174 |
| A12 | answer | answer | да | да | 0.1679 | 4169 |
| A13 | answer | answer | да | да | 0.1947 | 4925 |
| A14 | answer | answer | да | да | 0.1741 | 8481 |
| A15 | answer | answer | да | да | 0.1725 | 4096 |
| A16 | answer | answer | да | да | 0.1566 | 3683 |
| A17 | answer | answer | да | да | 0.1808 | 5167 |
| A18 | answer | answer | да | да | 0.1879 | 4426 |
| A19 | answer | answer | да | да | 0.2127 | 4996 |
| A20 | answer | answer | да | да | 0.1648 | 3875 |
| A21 | answer | answer | да | да | 0.1908 | 4595 |
| A22 | answer | answer | да | да | 0.1687 | 3956 |
| A23 | answer | answer | да | нет | 0.1881 | 4663 |
| A24 | answer | answer | да | да | 0.206 | 4361 |
| A25 | answer | answer | да | да | 0.1862 | 4527 |
| A26 | answer | answer | да | да | 0.2024 | 4660 |
| A27 | answer | answer | да | да | 0.1967 | 4298 |
| A28 | answer | answer | да | да | 0.2131 | 5539 |
| A29 | answer | answer | да | да | 0.1605 | 4129 |
| A30 | answer | answer | да | да | 0.1812 | 4154 |
| A31 | answer | answer | да | да | 0.1877 | 4439 |
| A32 | answer | answer | да | да | 0.1721 | 3924 |
| A33 | answer | answer | да | да | 0.1608 | 4360 |
| A34 | answer | answer | да | да | 0.171 | 4453 |
| A35 | answer | answer | да | да | 0.1906 | 4650 |
| A36 | answer | answer | да | да | 0.2227 | 5354 |
| A37 | answer | answer | да | да | 0.1813 | 4631 |
| A38 | answer | answer | да | да | 0.1788 | 4425 |
| A39 | answer | answer | да | да | 0.1672 | 3779 |
| A40 | answer | answer | да | да | 0.1906 | 4531 |
| B01 | clarify | clarify | да | да | 0.3908 | 5097 |
| B02 | clarify | clarify | да | да | 0.3757 | 4392 |
| B03 | clarify | clarify | да | да | 0.4059 | 4511 |
| B04 | clarify | clarify | да | да | 0.417 | 4457 |
| B05 | clarify | clarify | да | да | 0.4374 | 4705 |
| B06 | clarify | clarify | да | да | 0.4432 | 4626 |
| B07 | clarify | clarify | да | да | 0.4808 | 5907 |
| B08 | clarify | clarify | да | да | 0.3779 | 4416 |
| C01 | answer | answer | да | нет | 0.3216 | 5269 |
| C02 | answer | answer | да | да | 0.3095 | 4869 |
| C03 | answer | answer | да | да | 0.3024 | 7458 |
| D01 | not_found | not_found | да | - | 0.1589 | 3538 |
| D02 | not_found | not_found | да | - | 0.1551 | 5287 |
| D03 | not_found | not_found | да | - | 0.1625 | 3654 |
| D04 | not_found | not_found | да | - | 0.1718 | 3884 |
| D05 | not_found | not_found | да | - | 0.1563 | 3613 |
| D06 | not_found | out_of_scope | нет | - | 0.0574 | 1412 |
| D07 | not_found | not_found | да | - | 0.1541 | 3526 |
| D08 | not_found | not_found | да | - | 0.1551 | 3641 |
| E01 | out_of_scope | out_of_scope | да | - | 0.0571 | 1534 |
| E02 | out_of_scope | out_of_scope | да | - | 0.0566 | 1204 |
| E03 | out_of_scope | out_of_scope | да | - | 0.0561 | 1278 |
| E04 | out_of_scope | out_of_scope | да | - | 0.0549 | 1184 |
| F01 | off_task | off_task | да | - | 0.0555 | 1216 |
| F02 | off_task | off_task | да | - | 0.0573 | 1249 |
| F03 | off_task | off_task | да | - | 0.0573 | 1248 |
| F04 | off_task | off_task | да | - | 0.0575 | 1244 |
| G01 | answer | answer | да | да | 0.1943 | 4597 |
| G02 | answer | document | нет | нет | 0.0608 | 1715 |
| G03 | answer | answer | да | да | 0.1804 | 4428 |
| H01 | document | document | да | - | 0.0619 | 1553 |
| H02 | document | document | да | - | 0.0632 | 1422 |
| I01 | greeting | greeting | да | - | 0.0545 | 1474 |
