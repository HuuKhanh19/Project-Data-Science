# Bao cao ky thuat: Pipeline du lieu bao cao tai chinh

Tai lieu nay mo ta pipeline finance sau khi da duoc chuan hoa lai de tranh look-ahead bias va thong nhat schema cho toan repo.

## 1) Muc tieu

- Thu thap ratio tai chinh theo quy cho ma `TCB`.
- Luu raw input theo mot schema wide duy nhat.
- Suy ra `period_end_date` va `effective_date` de merge theo thoi diem co hieu luc.
- Tao `features_finance` dung truc tiep cho `merged_features` va model training.

## 2) Thanh phan

- `data_collection/collect_finance.py`
- `preprocessing/process_finance.py`
- `preprocessing/finance_utils.py`

Luong xu ly:

1. `collect_finance` lay ratio theo quy va ghi vao `raw_finance`.
2. `process_finance` doc `raw_finance`, tinh feature, giu dung `NaN` dau ky va ghi vao `features_finance`.
3. `merge_features` join finance vao gia theo nguyen tac `effective_date <= trading_date`.

## 3) Schema raw_finance

`raw_finance` la wide-format. Moi dong dai dien cho mot quy va co cac cot timing bat buoc:

- `symbol`
- `date` theo ma quy, vi du `2024-Q1`
- `period_end_date`
- `effective_date`
- cac cot ratio nhu `roe`, `roa`, `debt_to_equity`, `pe_ratio`, `pb_ratio`, `eps_vnd`, `bvps_vnd`

Khong con su dung long-format `ticker / quarter / metric_name / value`.

## 4) Quy tac effective_date

`effective_date` duoc suy ra tu config `FINANCE_REPORT_LAG_DAYS`:

- `Q1 = 30 ngay`
- `Q2 = 45 ngay`
- `Q3 = 30 ngay`
- `Q4 = 90 ngay`

`date` van la ma ky bao cao. Thoi diem du lieu duoc phep xuat hien trong feature pipeline la `effective_date`.

## 5) Xu ly features_finance

`process_finance.py` thuc hien:

- chuan hoa quarter code
- bo sung `period_end_date`, `effective_date` neu raw data chua co
- sap xep theo thoi gian
- chi `forward fill`, khong `backfill`
- tinh `roe_yoy`, `roa_yoy`, `roe_lag4`, `roa_lag4`
- giu `NaN` cho giai doan chua du lich su thay vi suy dien nguoc

Dau ra duoc ghi vao bang `features_finance`.

## 6) Merge voi gia co phieu

`preprocessing/merge_features.py` khong con fallback sang raw finance hoac ten bang finance cu.

Finance duoc join bang `merge_asof` theo:

- khoa sap xep: `effective_date`
- quy tac: lay ban ghi finance gan nhat ma `effective_date <= trade_date`

Dieu nay loai bo look-ahead bias khi model hoc tren du lieu gia hang ngay.

## 7) Kiem soat chat luong

Nhung diem can kiem tra:

- `raw_finance` chi co mot schema wide duy nhat
- `effective_date` luon lon hon hoac bang `period_end_date`
- `features_finance` khong co backfill cho cac cot YoY / lag
- `merged_features` khong duoc nhin thay quy moi truoc `effective_date`

## 8) Lenh van hanh

1. `python -m database.schema`
2. `python -m data_collection.collect_finance`
3. `python -m preprocessing.process_finance`
4. `python -m preprocessing.merge_features`

## 9) Dau ra mong doi

- `raw_finance`: ratio goc theo quy, wide-format
- `features_finance`: finance features da xu ly, co `effective_date`
- `merged_features`: da map finance vao moi ngay giao dich theo timing hop le
