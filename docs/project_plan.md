# Project Plan

## Objective

Build and evaluate a transparent day-ahead model for Great Britain National Demand at settlement-period level.

The project is designed around a realistic forecasting constraint: features must only use information that would genuinely have been available when the day-ahead forecast was issued.

## Primary analytical question

Using only information that would have been available when the day-ahead forecast was issued, how accurately can a transparent model forecast Great Britain National Demand for each half-hourly settlement period, where are its errors concentrated, and how does it compare with a seasonal benchmark and NESO's operational day-ahead forecast?

## Analytical grain

One row per:

- settlement date;
- settlement period.

The target is National Demand in MW.

Settlement days are not assumed to contain exactly 48 periods. UK daylight-saving transitions produce 46- and 50-period days and will be retained.

## Modelling principles

The project will use chronological validation rather than random train/test splitting.

Every candidate feature must pass the following test:

> Would this exact information genuinely have been available when the day-ahead forecast was issued?

Features that fail that test will not be used.

Model progression will remain deliberately limited:

1. seasonal or naive benchmark;
2. transparent statistical or regression model;
3. at most one stronger nonlinear model if it adds useful evidence;
4. comparison with NESO's operational forecast.

The aim is not to create a model zoo or to claim that an independent portfolio model can replace NESO's operational forecasting process.

## Evaluation

Primary evaluation will use absolute forecast error, supported by:

- MAE;
- RMSE;
- percentage error where appropriate;
- signed bias;
- error analysis by settlement period and other operationally useful groupings.

NESO's published error calculations will not be reused blindly. Project metrics will be calculated consistently for both the independent model and the NESO benchmark.

## Planned outputs

The completed project should contain:

- reproducible data acquisition;
- source/provenance documentation;
- data-quality checks;
- dbt staging and analytical models;
- leakage register;
- chronological validation;
- baseline and transparent forecasting models;
- comparison with NESO;
- focused error diagnostics;
- a small set of decision-useful visualisations;
- clear conclusions and limitations.
