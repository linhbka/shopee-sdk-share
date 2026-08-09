# shopee-open-sdk 2.1.1 — Hướng dẫn dùng Shopee Open API v2 bằng Python

> Wheel kèm theo: `shopee_open_sdk-2.1.1-py3-none-any.whl` (license MIT). Python ≥ 3.9,
> phụ thuộc duy nhất: `requests`.
>
> Bên trong có 2 package: **`pyshopee2` (Open API v2 — dùng cái này)** và `pyshopee`
> (v1 cũ, Shopee đã ngưng, chỉ để tham khảo).
>
> Tài liệu này viết cho **dev triển khai thật**, không phải bản demo: ngoài cách gọi API
> còn có 4 mảnh bắt buộc phải có trước khi lên production (mục 5) và các bẫy đã trả giá
> thật (mục 6). Mọi tham số đều đúng tên trong tài liệu chính thức
> <https://open.shopee.com/documents> — SDK không đổi tên gì.

---

## 1. Cài đặt

```bash
pip install requests
pip install shopee_open_sdk-2.1.1-py3-none-any.whl
```

## 2. App Shopee — một điều duy nhất phải nhắc

Bạn đã có app riêng rồi nên bỏ qua phần đăng ký. Chỉ còn một luật **không được vi phạm**:

⚠️ **Một `partner_id` chỉ phục vụ MỘT hệ thống.** `refresh_token` của Shopee là
**dùng-một-lần**: refresh xong thì token cũ chết ngay. Nếu hai hệ thống (hoặc máy dev +
máy production, hoặc hai worker không khoá) cùng dùng chung một bộ credential, chúng sẽ
giành nhau — một bên cầm token đã chết → **403 hàng loạt**. Một sự cố thực tế: hàng chục
nghìn lỗi 403 trong vài tuần chỉ vì đúng nguyên nhân này. Môi trường dev và production
phải là hai app khác nhau.

## 3. Authorize shop (làm một lần cho mỗi shop)

```python
from pyshopee2 import Client

client = Client(
    shop_id=None,                     # chưa có, nhận được sau khi shop duyệt
    partner_id=YOUR_PARTNER_ID,       # int
    partner_key="YOUR_PARTNER_KEY",
    redirect_url="https://your-domain.com/shopee/callback",
    # test_env=True,                  # bật nếu chạy sandbox
)

# Bước 1 — sinh URL để CHỦ SHOP bấm duyệt
print(client.shop_authorization())    # trả về str (URL)
# Chủ shop mở URL bằng tài khoản Shopee → duyệt → Shopee redirect về
# redirect_url kèm ?code=...&shop_id=...

# Bước 2 — đổi code lấy token (code sống vài phút, dùng một lần)
access_token, expire_in, refresh_token = client.get_token(
    code="CODE_TU_CALLBACK", shop_id=SHOP_ID_TU_CALLBACK
)
```

> ⚠️ `get_token()` và `get_access_token()` trả về **tuple 3 phần tử**
> `(access_token, expire_in, refresh_token)` — **không phải dict**. `expire_in` là số
> giây (thường 14400 = 4 giờ).

Lưu ngay `access_token` + `refresh_token` + `shop_id` + **thời điểm hết hạn**
(`now + expire_in`) vào DB. Cách refresh đúng: xem mục 5.1.

## 4. Gọi API và bắt lỗi

```python
client = Client(
    shop_id=shop_id,
    partner_id=YOUR_PARTNER_ID,
    partner_key="YOUR_PARTNER_KEY",
    redirect_url="...",
    access_token=access_token_dang_luu,
)

resp = client.order.get_order_list(
    time_range_field="create_time",
    time_from=1754600000, time_to=1754700000,   # unix giây, khoảng ≤ 15 ngày
    page_size=100,                              # tối đa 100
    cursor="",
)
```

> ⚠️ **SDK NÉM exception cho cả lỗi nghiệp vụ**, không trả về dict lỗi. Nghĩa là
> `if resp.get("error")` là code chết — không bao giờ chạy. Mọi lời gọi phải nằm trong
> `try/except ShopeeRequestError`. Khi thành công, `resp` là dict và dữ liệu nằm ở
> `resp["response"]`.

```python
from pyshopee2 import ShopeeRequestError

try:
    resp = client.order.get_order_list(...)
    orders = resp["response"]["order_list"]
except ShopeeRequestError as e:
    # e.status_code · e.error (mã lỗi Shopee) · e.request_id · e.payload
    # payload đã tự động che access_token/refresh_token/partner_key/sign → log an toàn
    log.error("shopee_fail", code=e.error, req_id=e.request_id)
```

`e.request_id` là thứ Shopee support hỏi đầu tiên khi bạn báo lỗi — **luôn log nó**.

Các module có sẵn: `order · product · logistics · payment · discount · voucher · returns ·
media · mediaspace · shop · merchant · chat · ads · ams · shopflashsale · bundledeal ·
addondeal · firstmile · accounthealth · public · push · livestream · video · sbs · fbs ·
globalproduct · toppicks · shopcategory · followprize`.

Endpoint mới chưa có method riêng → gọi thẳng:

```python
resp = client.call(uri="/api/v2/order/get_order_list", method="GET", payload={...})
```

## 5. Bốn mảnh BẮT BUỘC trước khi lên production

Thiếu bất kỳ mảnh nào dưới đây thì hệ thống chạy được vài ngày rồi hỏng.

### 5.1. Refresh token — có khoá và có kiểm-lại-sau-khi-khoá

Đây là chỗ dễ hỏng nhất vì `refresh_token` dùng-một-lần. Mẫu đã chạy production:

```python
def ensure_fresh_token(shop_id: int) -> Token:
    token = store.get(shop_id)
    # Refresh SỚM 2 phút, đừng đợi hết hạn mới refresh
    if token.expires_at - 120 > now():
        return token

    before_updated = token.updated_at
    with lock_for(shop_id):                     # khoá theo shop
        current = store.get(shop_id)            # ĐỌC LẠI sau khi giành được khoá
        if current.updated_at > before_updated: # ← luồng khác vừa refresh xong rồi
            return current                      #    dùng luôn, TUYỆT ĐỐI không refresh nữa
        access, expire_in, refresh = client.get_access_token(
            refresh_token=current.refresh_token, shop_id=shop_id
        )
        fresh = Token(
            access_token=access,
            refresh_token=refresh or current.refresh_token,
            expires_at=now() + int(expire_in or 0),
            updated_at=now(),
        )
        store.save(fresh)                       # ghi đè ngay, trong cùng transaction
        return fresh
```

Ba chi tiết không được bỏ:

- **Kiểm lại sau khi giành khoá** (`current.updated_at > before_updated`). Không có bước
  này thì 5 luồng cùng thấy token hết hạn sẽ xếp hàng refresh 5 lần liên tiếp — lần đầu
  thành công, 4 lần sau dùng token đã chết → hỏng cả cụm.
- **Khoá phải phủ đúng phạm vi chạy.** Một tiến trình → `threading.Lock` là đủ. Nhiều
  worker/nhiều máy → phải khoá phân tán (Postgres `pg_advisory_lock`, Redis lock…).
- **Ghi `refresh_token` mới đè cái cũ** trong cùng transaction với `access_token`.

### 5.2. Phân trang — dừng theo cờ `more`, không dừng theo số lượng

```python
cursor, tat_ca = "", []
while True:
    body = client.order.get_order_list(
        time_range_field="create_time", time_from=t_from, time_to=t_to,
        page_size=100, cursor=cursor,
    )["response"]

    tat_ca += [o["order_sn"] for o in body.get("order_list", [])]

    # Shopee trả `more` (bool) + `next_cursor` (str). Hết trang khi more=False.
    if not body.get("more"):
        break
    cursor = body["next_cursor"]
```

Đừng dừng khi `len(order_list) < page_size` — Shopee có thể trả trang non mà vẫn còn dữ
liệu. Chỉ tin cờ `more`.

Sau khi có danh sách mã đơn, lấy chi tiết theo **lô tối đa 50**:

```python
for i in range(0, len(tat_ca), 50):
    lo = tat_ca[i:i + 50]
    detail = client.order.get_order_detail(
        order_sn_list=",".join(lo),
        response_optional_fields="item_list,total_amount,pay_time,recipient_address",
    )
```

> ⚠️ **`response_optional_fields` là opt-in**: field nào không xin thì API **không trả**,
> và nó im lặng — không báo lỗi. Rất nhiều người tưởng "Shopee không có field đó" trong
> khi thật ra là quên xin. Cứ liệt kê đủ thứ bạn cần.

### 5.3. Phân loại lỗi → hành động (bảng này quyết định retry hay không)

`ShopeeRequestError.error` chứa mã lỗi Shopee. Ánh xạ đã dùng production:

| Nhóm | Dấu hiệu | Xử lý |
|---|---|---|
| **Hết hạn / sai token** | `error_auth`, `error_token`, `error_auth_refresh`, `error_invalid_token`, `error_access_token`, `error_permission`, hoặc HTTP 401/403 | Refresh token rồi gọi lại **một lần**. Vẫn lỗi → dừng, báo người. Đừng lặp. |
| **Quá tần suất** | `error_too_many_request`, `error_rate_limit`, hoặc HTTP 429 | Chờ theo `retry_after` nếu có, không thì backoff luỹ thừa. **Được retry.** |
| **Shopee lỗi** | HTTP 5xx | Backoff rồi retry. **Được retry.** |
| **Mạng** | timeout / connection reset | Backoff rồi retry — **nhưng xem cảnh báo bên dưới**. |
| **IP chưa khai báo** | HTTP 403 + `source_ip_undeclared` | **Không retry** — vô nghĩa. Báo người khai IP mới vào whitelist app. Thông điệp có dạng `Request Source IP (x.x.x.x) is undeclared` → parse lấy IP để báo cho nhanh. |
| **Còn lại** | sai tham số, sai trạng thái đơn… | **Không retry.** Retry chỉ tốn quota và che lỗi thật. |

Backoff nên có **jitter** (cộng ngẫu nhiên 0–25%) để nhiều worker không cùng thức dậy một
lúc: `delay = min(cap, base * 2**(lần_thử-1)) + random(0, 0.25*delay)`, ví dụ
`base=0.5s, cap=8s, tối đa 3 lần`.

> 🔴 **Cảnh báo về retry lỗi mạng, phần nguy hiểm nhất:** timeout **không** có nghĩa là
> request chưa tới nơi. Với endpoint **ghi** (`cancel_order`, `update_*`, `unlist_item`,
> tạo voucher…), retry sau timeout có thể **thực hiện hành động hai lần**. Quy tắc: endpoint
> đọc (`get_*`) retry thoải mái; endpoint ghi đặt **tối đa 1 lần thử**, và nếu nghi ngờ thì
> gọi API đọc để kiểm trạng thái trước khi thử lại.

### 5.4. Tự giới hạn tần suất (đừng đợi Shopee đánh 429)

Shopee giới hạn theo **hai tầng: mỗi shop và mỗi partner**. Mức thực tế dùng làm mặc định:
**~40 request/giây mỗi shop** và **~500 request/giây mỗi partner** (partner là tổng của tất
cả shop cộng lại — nhiều shop rất dễ chạm trần này trước).

Cách làm: một *token bucket* cho mỗi shop + một cho partner, mỗi request phải lấy được cả
hai vé mới được đi. Và **đọc header phản hồi để tự chỉnh**: Shopee trả các header dạng
`x-shopee-ratelimit-partner`, `x-shopee-ratelimit-shop`, `x-shopee-ratelimit-remaining`,
`x-shopee-ratelimit-reset`, `retry-after` — nếu có thì lấy số thật đó ghi đè mặc định.

## 6. Bẫy đã trả giá thật

1. **Tiền: dùng `escrow_amount`, không dùng `total_amount`.** `get_escrow_detail(order_sn=...)`
   → `response.order_income.escrow_amount` = tiền **thực về ví** sau mọi phí sàn, phí thanh
   toán, voucher, phí ship. `total_amount` chỉ là số khách trả. `buyer_paid_amount` hay NULL —
   đừng xây công thức trên nó. Có `get_escrow_detail_batch` nếu cần lấy nhiều đơn.
2. **Escrow ÂM là bình thường** — đơn giao thất bại / hoàn hàng, seller chịu phí ship nên
   tiền về âm. Đừng lọc bỏ nhóm này khỏi báo cáo: lọc đi là doanh thu bị thổi lên một chiều.
   (Chúng tôi mất công đối soát mới phát hiện lỗi này.)
3. **Escrow chỉ có sau khi Shopee quyết toán** — đơn mới thường chưa có. Muốn tính tỷ lệ phí
   thì lấy mẫu **đơn đã đủ chín ít nhất 10 ngày**, nếu không đơn chưa quyết toán sẽ bị tính
   như "mất trắng" và kéo tỷ lệ xuống sai.
4. **API không có lịch sử trạng thái đơn** — chỉ có trạng thái *hiện tại*. Một đơn `CANCELLED`
   không cho biết nó từng được xác nhận rồi mới huỷ, hay chết từ lúc chưa thanh toán. Muốn
   phân biệt phải suy từ `pay_time` / cờ `cod` / `cancel_reason`. **Hệ quả thiết kế: lưu
   `order_update_time` của Shopee và tự ghi lịch sử trạng thái ngay từ đầu**, sau này không
   dựng lại được.
5. **Cột enum trong DB đặt VARCHAR ≥ 64.** Shopee có mã dài 35+ ký tự
   (`AMS_COMMISSION_FEE_REFUND_DEDUCT`); đặt 32 là tràn cột giữa production.
6. **Số điện thoại người nhận bị che ở Việt Nam** — `recipient_address.phone` trả dạng
   `******NN` (2 số cuối), dù tài liệu Shopee nói chỉ che ở Đài Loan. Đừng hứa tính năng gọi
   khách dựa trên field này. **Địa chỉ tỉnh/thành trả về không chuẩn hoá** (một tỉnh nhiều
   cách viết, có/không tiền tố "Tỉnh"/"Thành phố") → phải tự chuẩn hoá trước khi gộp nhóm,
   không thì một tỉnh bị tách làm đôi trong báo cáo.
7. **403 `source_ip` xuất hiện đột ngột** thường chỉ là IP động của nhà mạng đổi, không phải
   bị tấn công. Chẩn nhanh: so IP hiện tại (`curl ifconfig.me`) với IP đã khai trong app.
8. **Đồng hồ máy chủ phải chuẩn (NTP).** Chữ ký HMAC gắn timestamp; lệch quá ~5 phút là sai
   chữ ký toàn bộ, mà thông báo lỗi trả về không hề gợi ý nguyên nhân này.
9. **Thời gian đều là unix giây UTC**, và khoảng truy vấn `time_from`/`time_to` của
   `get_order_list` **tối đa 15 ngày** — cần dài hơn thì tự cắt đoạn rồi lặp.
10. **Shopee chỉ giữ dữ liệu một thời gian**: số liệu traffic ~183 ngày, quảng cáo ~90 ngày.
    Cần lịch sử dài hơn thì phải kéo về DB của mình **từ sớm** — sau này không lấy lại được.
11. **Ghi log `request_id`** cho mọi lỗi. Không có nó thì làm việc với Shopee support gần như
    không đi tới đâu.

## 7. Sandbox

`Client(..., test_env=True)` → trỏ về host sandbox. Cần app + shop test riêng tạo trong
console. Dữ liệu sandbox rất nghèo: kiểm luồng authorize / chữ ký / phân trang thì tốt, còn
nghiệp vụ thật gần như phải test trên live với shop thật.

---

*Đóng gói từ kinh nghiệm chạy Shopee Open API v2 trên môi trường production. Chúc bạn build vui.*
