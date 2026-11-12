# shopee-open-sdk — SDK Python cho Shopee Open API v2

Thư viện Python gọi **Shopee Open API v2**, kèm tài liệu triển khai thực chiến.
Phù hợp cho đội đã có app Shopee riêng và muốn dựng hệ thống đồng bộ đơn / sản phẩm /
tài chính / quảng cáo.

## Có gì trong repo

| File | Nội dung |
|---|---|
| [`HUONG-DAN-SU-DUNG.md`](HUONG-DAN-SU-DUNG.md) | **Tài liệu chính.** Cài đặt → authorize shop → gọi API → 4 mảnh bắt buộc trước khi lên production → 21 bẫy dữ liệu đã trả giá thật → bẫy vận hành app (hạn khoá partner, IP, webhook) → tra cứu nhanh |
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

## Cập nhật 12/11/2026

Thư viện không đổi (vẫn 2.1.1). Tài liệu bổ sung kiến thức chạy thật từ 08 đến 11/2026,
quan trọng nhất:

- **Tiền về = `escrow_amount + total_adjustment_amount`.** Trả hàng, bồi thường sau khi đã
  giải ngân không sửa `escrow_amount` mà nằm ở khối điều chỉnh — chỉ đọc `escrow_amount` là
  doanh thu cao hơn thật.
- **Quyết toán phải kéo lại** khi đơn có trả hàng hoặc có giao dịch ví mới; kéo lại thì đừng
  ghi đè số cũ bằng phản hồi rỗng.
- **Đơn có thể đổi trạng thái mà `update_time` đứng yên** (trả hàng bị huỷ, đơn về
  `COMPLETED`) — quét theo `update_time` sẽ bỏ sót.
- **Live Partner Key hết hạn sau ~6 tháng**; xoay khoá có 24 giờ chuyển tiếp, không làm mất
  token shop.
- **IP whitelist đã dời sang "PII Necessity Declaration"**; khai IP xong cần ~4 phút mới thông đều.
- **GMV Max chỉ chịu ~3 lệnh gọi sát nhau mỗi shop.**

Chi tiết và cách làm: mục 6–8 của [HUONG-DAN-SU-DUNG.md](HUONG-DAN-SU-DUNG.md).

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
