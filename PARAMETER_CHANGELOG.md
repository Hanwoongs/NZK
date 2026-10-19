# Parameter changelog (branch pc-params-update, base NZK_Della_1013)

All edits applied identically to Ref/ and NDC/. Decisions taken: WACC kept tech-specific; CO2 cap kept (GCAM); battery basis = NREL ATB; CCS capture = 95% for coal and gas.

| # | Parameter | Files | Old | New | Source |
|---|---|---|---|---|---|
| 1 | Coal CCS `capture_rate` / `emission_rate` | coalpowerCCS_25..50 | 0.4398 / 0.0232 (sum 0.463 > fuel carbon 0.3405) | 0.323475 / 0.017025 (95% of 0.3405; sum = 0.3405) | Mass balance with `emission_rate` of coal 0.3405 tCO2/MWh_fuel (model, README 7.3); 95% capture per NREL ATB 2024 fossil technologies page (PC modelled at 95% and 99%) |
| 2 | Gas CCS `capture_rate` / `emission_rate` | NaturalGasPowerCCS_25..50 | 0.162943412 / 0.018104824 (90%) | 0.1719958242 / 0.0090524118 (95%; sum = 0.181048236) | Same mass balance; NREL ATB 2024 fossil page (NGCC modelled at 95% and 97%) |
| 3 | Coal CCS OCC 2030 | coalpowerCCS_30 | 2,509,255.25 | 2,402,346.97 | 1012_techno_params/option1_BNEF/capex_params.csv (Coal_CCS, 2030) |
| 4 | Gas CCS OCC 2030 | NaturalGasPowerCCS_30 | 1,718,027.80 | 1,208,525.44 | Option 1 CSV (Gas_CCS, 2030) |
| 5 | Gas CCS OCC 2035-2050 | NaturalGasPowerCCS_35..50 | 1,208,525.44 | 1,182,953.38 | Option 1 CSV (Gas_CCS, 2035+) |
| 6 | Battery 2021 `can_expand` | assets_2021/batterys.csv | TRUE | FALSE | README: 2021 is calibration year, `can_expand = FALSE` for all |
| 7 | Offshore wind CF, coastal provinces with potential but CF = 0 | system/availability.csv: PUS, USN, GWN, GGI, JNB `_offwind-dc` | all zeros | copy of nearest coastal series: PUS<-GNA, USN<-GNB, GWN<-GNB, GGI<-INC, JNB<-CNA | PROXY, not new ERA5 data. Replace with province-specific ERA5 CF when available |

## Not changed yet (need data not reachable from this session)
- Gas CCS `fuel_consumption` (energy penalty): needs NREL ATB / NETL heat rates (ATB data download blocked from this session).
- Battery costs on NREL ATB basis: ATB page gives only indices (2035 Moderate = 63, 2050 = 49 of 2022) and FOM 2.5% of CAPEX, RTE 85%; absolute $/kW and the $/kWh vs $/kW split are in the ATB data workbook.
- Wind and solar FOM per year (BNEF Korea xlsx not in repo).
- Retirement schedules, nuclear availability, VOLL, solar/onshore CF, fuel prices, docs alignment.
