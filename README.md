# Sheet + Proxy Tool

Ung dung macOS de:

- nhap `Google Sheet URL`
- lay 20 dong dau tien trong sheet `people` co cot `L` trong
- hien thi du lieu va bam de copy nhanh
- cap nhat `LIVE` / `UP ID` vao cot `L`
- cap nhat so dien thoai vao cot `M`
- doi proxy qua API `proxyno1`

## Yeu cau

- macOS
- Xcode Command Line Tools

App nay khong can `pip install`, khong can Homebrew, khong can mo port local.

## File Google can co

De app doc/ghi Google Sheet private, trong thu muc du an can co:

- file service account JSON, vi du:
  `carbide-booth-492715-t7-b0686577f711.json`

Google Sheet phai duoc share cho:

- `congviec@carbide-booth-492715-t7.iam.gserviceaccount.com`

## Chay tren may moi

Neu may moi chua co `git`, cai bang lenh:

```bash
xcode-select --install
```

Sau khi cai xong, mo lai Terminal roi chay:

```bash
git clone https://github.com/lamm314/AutoReg_PP.git
cd AutoReg_PP
./setup.command
```

Hoac tach ra tung buoc:

1. Clone repo:

```bash
git clone https://github.com/lamm314/AutoReg_PP.git
cd AutoReg_PP
```

2. Chay setup:

```bash
./setup.command
```

Neu may chua co Xcode Command Line Tools, script se mo hop thoai cai dat. Cai dat xong thi chay lai:

```bash
./setup.command
```

3. Sau khi setup xong, tu lan sau chi can chay:

```bash
./run_app.command
```

## Cach dung

1. Mo app.
2. Nhap `Google Sheet URL`.
3. Nhap `Proxy API key`.
4. Bam `Luu cau hinh` neu muon luu lai.
5. Bam `Lay 20 dong`.
6. Chon 1 dong o ben trai.
7. Bam vao tung truong o ben phai de copy.
8. Chon `LIVE` hoac `UP ID`.
9. Nhap so dien thoai.
10. Bam `Xac nhan va ghi vao sheet`.
11. Bam `Doi proxy` khi can.

## Luu y Google Sheet

App uu tien doc/ghi bang service account neu trong thu muc co file service account JSON.

Neu khong co service account JSON, app se fallback sang doc bang link CSV public. Nghia la:

- sheet can truy cap duoc bang link
- neu sheet private, app se khong doc duoc theo cach hien tai

## File quan trong

- `SheetProxyNative.swift`: source code giao dien va logic
- `run_app.command`: build va mo app
- `setup.command`: script chay tren may moi
- `app_config.json`: file tu sinh de luu `sheet_url` va `proxy_key`
- `.gitignore`: bo qua file build va file secret

## Neu macOS chan app

Neu macOS canh bao app khong mo duoc, vao:

- `System Settings`
- `Privacy & Security`
- tim thong bao lien quan den app vua mo
- chon `Open Anyway`

## Lenh nhanh

Build + mo app:

```bash
./run_app.command
```

Setup tren may moi:

```bash
./setup.command
```

## Bao mat

Khong nen commit cac file sau len repo public:

- service account JSON
- `client_secret_*.json`
- `app_config.json`
