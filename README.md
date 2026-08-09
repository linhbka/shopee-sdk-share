# shopee-open-sdk — SDK Python cho Shopee Open API v2

Thư viện Python gọi **Shopee Open API v2**, kèm tài liệu triển khai thực chiến.
Phù hợp cho đội đã có app Shopee riêng và muốn dựng hệ thống đồng bộ đơn / sản phẩm /
tài chính / quảng cáo.

## Có gì trong repo

| File | Nội dung |
|---|---|
| [`HUONG-DAN-SU-DUNG.md`](HUONG-DAN-SU-DUNG.md) | **Tài liệu chính.** Cài đặt → authorize shop → gọi API → 4 mảnh bắt buộc trước khi lên production → 11 bẫy đã trả giá thật |
| [`vi_du_nhanh.py`](vi_du_nhanh.py) | Script chạy được ngay: phân trang lấy đơn 24h, chi tiết theo lô, đọc tiền thực về ví |
| `shopee_open_sdk-2.1.1-py3-none-any.whl` | Thư viện (license MIT) |

## Cài đặt

```bash
pip install requests
pip install shopee_open_sdk-2.1.1-py3-none-any.whl
```

Package runtime là `pyshopee2` (Open API **v2**). Trong wheel còn `pyshopee` là bản v1 cũ,
Shopee đã ngưng — không dùng.

```python
from pyshopee2 import Client, ShopeeRequestError
```

## Ba điều nên biết trước khi viết dòng đầu tiên

1. **`get_token()` / `get_access_token()` trả về tuple**, không phải dict:
   `access_token, expire_in, refresh_token = client.get_token(...)`.
2. **SDK ném `ShopeeRequestError` cho cả lỗi nghiệp vụ** — không trả dict lỗi. Mọi lời gọi
   phải bọc `try/except`; kiểm `resp["error"]` là code chết.
3. **`refresh_token` của Shopee dùng-một-lần.** Hai tiến trình cùng refresh = một bên cầm
   token chết = 403 hàng loạt. Mẫu refresh có khoá đúng nằm ở mục 5.1 của tài liệu chính —
   đọc trước khi tự viết.

Chi tiết đầy đủ: [HUONG-DAN-SU-DUNG.md](HUONG-DAN-SU-DUNG.md).

## Yêu cầu

Python ≥ 3.9 · phụ thuộc duy nhất `requests` · cần app Shopee Open Platform riêng
(`partner_id` + `partner_key` + `redirect_url` đã khai).

⚠️ Một `partner_id` chỉ phục vụ một hệ thống — môi trường dev và production phải là hai app
khác nhau. Lý do ở mục 2 của tài liệu.
