# Отчёт тестового прогона

| Метрика | Значение |
|---|---|
| cases | 73 |
| behavior_accuracy | 0.986 |
| citation_accuracy | 0.963 |
| false_answer_rate | 0.0 |
| escalation_recall | 0.875 |
| clarify_recall | 1.0 |
| missing_docs_flagged | 1.0 |
| judge_distortions | 19 |
| latency_ms_p50 | 4377 |
| latency_ms_p95 | 5710 |
| avg_cost_rub | 0.1947 |
| avg_llm_calls | 2.1 |
| duration_s | 382.9 |
| model | qwen3.6-35b-a3b |

| id | ожидали | получили | поведение | цитата | ₽ | мс |
|---|---|---|---|---|---|---|
| A01 | answer | answer | да | нет | 0.1797 | 5763 |
| A02 | answer | answer | да | да | 0.1853 | 3684 |
| A03 | answer | answer | да | да | 0.1709 | 4604 |
| A04 | answer | answer | да | да | 0.1723 | 3943 |
| A05 | answer | answer | да | да | 0.2072 | 5246 |
| A06 | answer | answer | да | да | 0.1969 | 4471 |
| A07 | answer | answer | да | да | 0.1764 | 4309 |
| A08 | answer | answer | да | да | 0.1932 | 4861 |
| A09 | answer | answer | да | да | 0.1602 | 3893 |
| A10 | answer | answer | да | да | 0.1933 | 4968 |
| A11 | answer | answer | да | да | 0.1781 | 4467 |
| A12 | answer | answer | да | да | 0.1724 | 4026 |
| A13 | answer | answer | да | да | 0.1898 | 4423 |
| A14 | answer | answer | да | да | 0.1699 | 3858 |
| A15 | answer | answer | да | да | 0.165 | 3772 |
| A16 | answer | answer | да | да | 0.1698 | 5033 |
| A17 | answer | answer | да | да | 0.1855 | 5768 |
| A18 | answer | answer | да | да | 0.1924 | 5699 |
| A19 | answer | answer | да | да | 0.2224 | 5354 |
| A20 | answer | answer | да | да | 0.1714 | 4742 |
| A21 | answer | answer | да | да | 0.1799 | 4405 |
| A22 | answer | answer | да | да | 0.178 | 4776 |
| A23 | answer | answer | да | да | 0.224 | 5778 |
| A24 | answer | not_found | нет | нет | 0.207 | 4455 |
| A25 | answer | answer | да | да | 0.1963 | 4493 |
| A26 | answer | answer | да | да | 0.1879 | 5142 |
| A27 | answer | answer | да | да | 0.2002 | 4449 |
| A28 | answer | answer | да | да | 0.1936 | 4638 |
| A29 | answer | answer | да | да | 0.1714 | 3908 |
| A30 | answer | answer | да | да | 0.1823 | 4356 |
| A31 | answer | answer | да | да | 0.1794 | 4916 |
| A32 | answer | answer | да | да | 0.1804 | 4377 |
| A33 | answer | answer | да | да | 0.1862 | 5134 |
| A34 | answer | answer | да | да | 0.1752 | 4270 |
| A35 | answer | answer | да | да | 0.2041 | 4757 |
| A36 | answer | answer | да | да | 0.2077 | 4718 |
| A37 | answer | answer | да | да | 0.194 | 4691 |
| A38 | answer | answer | да | да | 0.1815 | 4218 |
| A39 | answer | answer | да | да | 0.1713 | 4100 |
| A40 | answer | answer | да | да | 0.1847 | 3824 |
| B01 | clarify | clarify | да | да | 0.4048 | 4917 |
| B02 | clarify | clarify | да | да | 0.3802 | 5341 |
| B03 | clarify | clarify | да | да | 0.4105 | 4953 |
| B04 | clarify | clarify | да | да | 0.4287 | 4298 |
| B05 | clarify | clarify | да | да | 0.4433 | 4578 |
| B06 | clarify | clarify | да | да | 0.4229 | 4043 |
| B07 | clarify | clarify | да | да | 0.5415 | 6222 |
| B08 | clarify | clarify | да | да | 0.3875 | 5526 |
| C01 | answer | answer | да | да | 0.3469 | 4965 |
| C02 | answer | answer | да | да | 0.3006 | 4740 |
| C03 | answer | answer | да | да | 0.2968 | 5710 |
| D01 | not_found | not_found | да | - | 0.1677 | 3481 |
| D02 | not_found | not_found | да | - | 0.1656 | 3761 |
| D03 | not_found | not_found | да | - | 0.1605 | 4137 |
| D04 | not_found | not_found | да | - | 0.1567 | 3793 |
| D05 | not_found | not_found | да | - | 0.1645 | 3183 |
| D06 | not_found | out_of_scope | да | - | 0.0591 | 1486 |
| D07 | not_found | not_found | да | - | 0.1773 | 3455 |
| D08 | not_found | not_found | да | - | 0.1596 | 3495 |
| E01 | out_of_scope | out_of_scope | да | - | 0.0588 | 1526 |
| E02 | out_of_scope | out_of_scope | да | - | 0.0596 | 1278 |
| E03 | out_of_scope | out_of_scope | да | - | 0.0566 | 1171 |
| E04 | out_of_scope | out_of_scope | да | - | 0.0566 | 1206 |
| F01 | off_task | off_task | да | - | 0.0554 | 1164 |
| F02 | off_task | off_task | да | - | 0.059 | 1289 |
| F03 | off_task | off_task | да | - | 0.059 | 1574 |
| F04 | off_task | off_task | да | - | 0.0592 | 1474 |
| G01 | answer | answer | да | да | 0.1916 | 4501 |
| G02 | answer | answer | да | да | 0.1701 | 3817 |
| G03 | answer | answer | да | да | 0.186 | 4248 |
| H01 | document | document | да | - | 0.0636 | 1587 |
| H02 | document | document | да | - | 0.0649 | 1415 |
| I01 | greeting | greeting | да | - | 0.0575 | 1253 |
