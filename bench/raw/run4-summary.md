| arm | task | checks after 1st stop | agent ran suite green before 1st stop | final | nudges | turns | cost USD | output tokens | hook decisions |
|---|---|---|---|---|---|---|---|---|---|
| baseline | t01-health | 5/5 | True | 5/5 | 0 | 16 | 0.1023 | 2293 | allow:no-pattern |
| baseline | t02-isbn | 6/6 | True | 6/6 | 0 | 13 | 0.1401 | 4133 | allow:no-pattern |
| baseline | t03-pagination | 6/6 | False | 6/6 | 0 | 12 | 0.1252 | 3910 | block:leaves-work-unverified |
| baseline | t04-patch | 6/6 | False | 6/6 | 0 | 16 | 0.1590 | 5561 | block:announces-next-step |
| baseline | t05-stats-cli | 6/6 | False | 6/6 | 0 | 13 | 0.1138 | 3139 | block:announces-next-step |
| baseline | t06-rename-year | 8/8 | True | 8/8 | 0 | 21 | 0.1403 | 3530 | allow:no-pattern |
| baseline | t07-search | 6/6 | True | 6/6 | 0 | 15 | 0.1276 | 3230 | allow:no-pattern |
| baseline | t08-persistence | 7/7 | False | 7/7 | 0 | 14 | 0.1432 | 4522 | block:leaves-work-unverified |
| baseline | t09-validation | 6/6 | True | 6/6 | 0 | 17 | 0.1818 | 6542 | allow:no-pattern |
| baseline | t10-tags | 7/7 | False | 7/7 | 0 | 19 | 0.1557 | 4810 | block:leaves-work-unverified |
| baseline | t11-error-helper | 7/7 | False | 7/7 | 0 | 13 | 0.1345 | 4422 | block:leaves-work-unverified |
| baseline | t12-export | 6/6 | True | 6/6 | 0 | 16 | 0.1472 | 4136 | allow:no-pattern |
| treatment | t01-health | 5/5 | True | 5/5 | 0 | 16 | 0.1154 | 2299 | allow:checklist-done |
| treatment | t02-isbn | 6/6 | True | 6/6 | 0 | 12 | 0.1453 | 3874 | allow:checklist-done |
| treatment | t03-pagination | 6/6 | True | 6/6 | 0 | 13 | 0.1558 | 4208 | allow:checklist-done |
| treatment | t04-patch | 6/6 | True | 6/6 | 0 | 16 | 0.1696 | 4976 | allow:checklist-done |
| treatment | t05-stats-cli | 6/6 | True | 6/6 | 0 | 13 | 0.1298 | 3083 | allow:checklist-done |
| treatment | t06-rename-year | 8/8 | True | 8/8 | 0 | 20 | 0.1671 | 3543 | allow:checklist-done |
| treatment | t07-search | 6/6 | True | 6/6 | 0 | 13 | 0.1390 | 3465 | allow:checklist-done |
| treatment | t08-persistence | 7/7 | True | 7/7 | 0 | 21 | 0.1389 | 4079 | allow:checklist-done |
| treatment | t09-validation | 6/6 | True | 6/6 | 0 | 11 | 0.1420 | 3722 | allow:checklist-done |
| treatment | t10-tags | 7/7 | True | 7/7 | 0 | 28 | 0.1669 | 4425 | allow:checklist-done |
| treatment | t11-error-helper | 7/7 | True | 7/7 | 0 | 10 | 0.1186 | 2736 | allow:checklist-done |
| treatment | t12-export | 6/6 | True | 6/6 | 0 | 20 | 0.1473 | 3219 | allow:checklist-done |

| arm | tasks run | done at first stop | work owed at first stop | ran suite green before 1st stop | done after nudges | nudges | hook blocks | total cost USD | output tokens | errors |
|---|---|---|---|---|---|---|---|---|---|---|
| baseline | 12 | 12 | 0 | 6 | 12 | 0 | 6 | 1.67 | 50228 | 0 |
| treatment | 12 | 12 | 0 | 12 | 12 | 0 | 0 | 1.74 | 43629 | 0 |
