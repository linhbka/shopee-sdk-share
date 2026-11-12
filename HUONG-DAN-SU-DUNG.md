# shopee-open-sdk 2.1.1 — Hướng dẫn dùng Shopee Open API v2 bằng Python

> Wheel kèm theo: `shopee_open_sdk-2.1.1-py3-none-any.whl` (license MIT). Python ≥ 3.9,
> phụ thuộc duy nhất: `requests`.
>
> Bên trong có 2 package: **`pyshopee2` (Open API v2 — dùng cái này)** và `pyshopee`
> (v1 cũ, Shopee đã ngưng, chỉ để tham khảo).
>
> Tài liệu này viết cho **dev triển khai thật**, không phải bản demo: ngoài cách gọi API
> còn có 4 mảnh bắt buộc phải có trước khi lên production (mục 5), các bẫy dữ liệu đã trả
> giá thật (mục 6) và các bẫy vận hành app (mục 7). Mọi tham số đều đúng tên trong tài liệu
> chính thức <https://open.shopee.com/documents> — SDK không đổi tên gì.
>
> **Cập nhật 12/11/2026:** thư viện không đổi (vẫn 2.1.1). Bổ sung kiến thức chạy thật từ
> 08/2026 đến 11/2026: tiền về sau điều chỉnh (bẫy 1 viết lại), kéo lại quyết toán, đơn đổi
> trạng thái mà `update_time` đứng yên, đối chiếu ví, cờ trả hàng mới, `main_item`, hạn mức
> GMV Max, toàn bộ mục 7 (hạn khoá partner, IP, push) và mục 8 (tra cứu). Lịch sử thay đổi
> ở cuối tệp.

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

> 💡 Đăng nhập **Open Platform Console** (nơi quản lý app) khác đăng nhập **Seller Centre**
> (tài khoản shop). Muốn cấp quyền lại cho nhiều shop thì mỗi shop cần phiên Seller Centre của
> chính nó; một trình duyệt chỉ giữ một phiên Seller → dùng hồ sơ trình duyệt riêng cho từng shop.

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

Bốn chi tiết không được bỏ:

- **Kiểm lại sau khi giành khoá** (`current.updated_at > before_updated`). Không có bước
  này thì 5 luồng cùng thấy token hết hạn sẽ xếp hàng refresh 5 lần liên tiếp — lần đầu
  thành công, 4 lần sau dùng token đã chết → hỏng cả cụm.
- **Khoá phải phủ đúng phạm vi chạy.** Một tiến trình → `threading.Lock` là đủ. Nhiều
  worker/nhiều máy → phải khoá phân tán (Postgres `pg_advisory_lock`, Redis lock…).
- **Ghi `refresh_token` mới đè cái cũ** trong cùng transaction với `access_token`.
- 🔴 **Script chạy riêng (kiểm tra, dò dữ liệu, chạy tay) KHÔNG được tự refresh.** Khoá trong
  tiến trình của app không chặn được một script chạy ở tiến trình khác. Script mà refresh song
  song với app là app cầm token chết → mất quyền shop, phải authorize lại. Trong script, thay
  hàm refresh bằng một hàm ném lỗi; shop nào token hết hạn thì bỏ qua, để app tự refresh.

> ⚠️ **Chỉ refresh khi mã lỗi đúng là lỗi token**, đừng refresh với mọi HTTP 403. Gọi sai
> đường dẫn hay IP chưa khai cũng ra 403; nếu wrapper "gặp 403 là refresh" thì một script gọi
> thử một endpoint không tồn tại cũng đủ đi vào đường refresh (đã xảy ra thật).

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

> ⚠️ Shopee thông báo (bài Announcement 11/2026) rằng trong đợt sale lớn, khi hệ thống giảm
> tải, `get_order_list` có thể chỉ trả lời nhắn trong trường `warning` thay vì danh sách đơn.
> Hãy log trường `warning` nếu có, và có đường bù (ví dụ `logistics.get_shipment_list` cho đơn
> chờ giao) thay vì coi "không có đơn" là thật. Chúng tôi chưa gặp lần giảm tải thật nào để
> xác nhận hình dạng phản hồi.

### 5.3. Phân loại lỗi → hành động (bảng này quyết định retry hay không)

`ShopeeRequestError.error` chứa mã lỗi Shopee. Ánh xạ đã dùng production:

| Nhóm | Dấu hiệu | Xử lý |
|---|---|---|
| **Hết hạn / sai token** | `error_auth`, `error_token`, `error_auth_refresh`, `error_invalid_token`, `error_access_token`, `error_permission`, hoặc HTTP 401 | Refresh token rồi gọi lại **một lần**. Vẫn lỗi → dừng, báo người. Đừng lặp. |
| **Quá tần suất** | `error_too_many_request`, `error_rate_limit`, hoặc HTTP 429 | Chờ theo `retry_after` nếu có, không thì backoff luỹ thừa. **Được retry.** |
| **Quá tần suất của quảng cáo** | `ads_rate_limit_shop_api` | **Không retry ngay** — xem bẫy 9 ở mục 6. |
| **Shopee lỗi** | HTTP 5xx | Backoff rồi retry. **Được retry.** |
| **Mạng** | timeout / connection reset | Backoff rồi retry — **nhưng xem cảnh báo bên dưới**. |
| **IP chưa khai báo** | HTTP 403 + `source_ip_undeclared` | **Không retry, không refresh** — vô nghĩa. Báo người khai IP mới (mục 7.2). Thông điệp có dạng `Request Source IP (x.x.x.x) is undeclared` → parse lấy IP để báo cho nhanh. |
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

Một số nhóm endpoint có hạn mức **riêng, thấp hơn nhiều và không công bố** — xem bẫy 9 ở mục 6.

## 6. Bẫy dữ liệu đã trả giá thật

### Tiền và quyết toán

1. **Tiền về = `escrow_amount + total_adjustment_amount`, không phải `escrow_amount` trần,
   càng không phải `total_amount`.** `payment.get_escrow_detail(order_sn=...)` →
   `response.order_income`. `total_amount` chỉ là số khách trả; `buyer_paid_amount` hay NULL —
   đừng xây công thức trên nó.

   Shopee có **hai đường** ghi tiền trả hàng:
   - Trả hàng / hoàn tiền **trước khi giải ngân**: Shopee sửa thẳng `escrow_amount`.
   - Trả hàng, bồi thường khiếu nại kéo dài, đền bù vận chuyển **sau khi đã giải ngân**:
     `escrow_amount` **đứng yên**, Shopee ghi thêm dòng vào `order_adjustment[]`, cộng dồn ở
     `total_adjustment_amount` (số âm khi trừ tiền), số cuối ở `escrow_amount_after_adjustment`.

   Chỉ đọc `escrow_amount` thì đơn đã hoàn đủ tiền vẫn mang trọn doanh thu. Ở hệ thống của
   chúng tôi, lỗi này làm doanh thu cao hơn thật khoảng 1% mỗi tháng, tháng nào cũng có.

   ```python
   income = client.payment.get_escrow_detail(order_sn=sn)["response"].get("order_income") or {}
   if income.get("escrow_amount") is None:
       tien_ve = None          # chưa quyết toán, hoặc Shopee không còn phục vụ đơn này
   else:
       tien_ve = income["escrow_amount"] + (income.get("total_adjustment_amount") or 0)
   ```

   Vì sao **cộng hai trường** chứ không lấy thẳng `escrow_amount_after_adjustment`: nếu một
   phản hồi thiếu khối điều chỉnh, phép cộng vẫn ra đúng tiền gốc, còn lấy thẳng thì ra None
   và xoá mất doanh thu. Đã kiểm trên toàn bộ đơn một năm: phép cộng bằng đúng
   `escrow_amount_after_adjustment` ở mọi đơn có trường đó.

   Có `get_escrow_detail_batch` nếu cần lấy nhiều đơn.
2. **Escrow ÂM là bình thường** — đơn giao thất bại / hoàn hàng, seller chịu phí ship nên
   tiền về âm. Đừng lọc bỏ nhóm này khỏi báo cáo: lọc đi là doanh thu bị thổi lên một chiều.
   Khi cộng tiền, mọi điều kiện kiểu `escrow > 0` hoặc `COALESCE(escrow, 0) = 0` đều là nghi
   phạm. (Lọc để *chọn mẫu* thì được, lọc khi *cộng tiền* thì không.)
3. **Escrow chỉ có sau khi Shopee quyết toán** — đơn mới thường chưa có. Muốn tính tỷ lệ phí
   thì lấy mẫu **đơn đã đủ chín ít nhất 10 ngày**, nếu không đơn chưa quyết toán sẽ bị tính
   như "mất trắng" và kéo tỷ lệ xuống sai.
4. **Quyết toán kéo một lần là sẽ cũ.** Khách có thể trả hàng sau khi đơn đã `COMPLETED`;
   khi đó `order_status` vẫn `COMPLETED`, chỉ quyết toán và hồ sơ trả hàng đổi. Hệ thống phải
   **kéo lại quyết toán** khi:
   - hồ sơ trả hàng của đơn chuyển sang `ACCEPTED` sau lần kéo trước; hoặc
   - sổ ví (`payment.get_wallet_transaction_list`) có giao dịch mới gắn mã đơn đó sau lần kéo
     trước, **trừ** hai loại `ESCROW_VERIFIED_ADD` / `ESCROW_VERIFIED_MINUS` (đó chính là khoản
     giải ngân bình thường; tính cả vào là kéo lại gần như mọi đơn vô ích).

   🔴 **Kéo lại là GHI ĐÈ, khác kéo lần đầu.** Với đơn quá cũ, Shopee có thể đáp 200 nhưng
   `order_income` rỗng. Ghi đè lúc đó sẽ xoá số đúng đang có. Chốt chặn phải là
   `if escrow_amount is None: bỏ qua`, **không** dùng `if not escrow_amount` — quyết toán bằng 0
   hoặc âm vẫn phải được ghi.
5. **Đối chiếu bằng sổ ví.** Tổng **mọi** giao dịch ví gắn một mã đơn phải bằng tiền về sau
   điều chỉnh của đơn đó. Đây là phép kiểm chéo tốt nhất mà không cần nguồn ngoài. Các loại giao
   dịch đáng biết: `ADJUSTMENT_FOR_RR_AFTER_ESCROW_VERIFIED` (trả hàng sau giải ngân),
   `RETURN_COMPENSATION_SERVICE_ADD`, `SELLER_COMPENSATE_ADD`, `FULFILMENT_COMPENSATE_ADD`.
   Lưu ý: khoản bù loại `ADJUSTMENT_CENTER_ADD` **không** có mã đơn, chỉ đối chiếu được ở cấp shop.

### Đơn hàng

6. **API không có lịch sử trạng thái đơn** — chỉ có trạng thái *hiện tại*. Một đơn `CANCELLED`
   không cho biết nó từng được xác nhận rồi mới huỷ, hay chết từ lúc chưa thanh toán. Muốn
   phân biệt phải suy từ `pay_time` / cờ `cod` / `cancel_reason` (giao không thành có
   `cancel_reason = "Failed Delivery"`). **Hệ quả thiết kế: lưu `order_update_time` của Shopee
   và tự ghi lịch sử trạng thái ngay từ đầu**, sau này không dựng lại được.
7. 🔴 **Đơn đổi trạng thái mà `update_time` KHÔNG đổi.** Khách mở yêu cầu trả hàng (đơn sang
   `TO_RETURN`), sau đó yêu cầu bị huỷ: đơn quay về `COMPLETED` nhưng Shopee **giữ nguyên
   `update_time` cũ**. Quét theo `time_range_field="update_time"` sẽ không bao giờ thấy bước
   chuyển này, và đơn nằm kẹt ở `TO_RETURN` trong DB của bạn mãi mãi (báo cáo chỉ tính
   `COMPLETED` sẽ bỏ sót cả doanh thu lẫn giá vốn). Cách chữa: định kỳ gọi `get_order_detail`
   cho các đơn **chưa chốt** (khác `COMPLETED`/`CANCELLED`) mà đã im lặng vài ngày, mỗi đơn tối
   đa một lần mỗi ngày để không đốt quota.
8. **`item_list[].main_item` KHÔNG phải cờ "sản phẩm chính".** Nó chỉ bật ở đơn có bundle /
   add-on để phân biệt món chính với món kèm; đơn một món thì `main_item = false` dù đó là sản
   phẩm chính. `add_on_deal` cũng không dùng được (dính cả quà lẫn sản phẩm chính). Muốn tách
   quà tặng 0 đồng / giá rẻ khỏi sản phẩm thật thì lọc theo **giá dòng** với ngưỡng hợp với
   ngành hàng của bạn.
9. **Giá trong đơn:** `model_original_price` là giá gạch (thường không ai mua ở giá đó),
   `model_discounted_price` là giá niêm yết sau khuyến mãi của shop, `total_amount` là số khách
   trả sau voucher, xu, phí ship. Chênh lệch `total_amount` giữa các đơn cùng sản phẩm phần lớn
   do voucher và khuyến mãi tự áp, **không phải** do phân loại khác giá.
10. **Tên và số điện thoại người nhận đều bị che ở Việt Nam** — `recipient_address.phone` trả
    dạng `******NN` (2 số cuối), `name` có dấu `*`, ở mọi trạng thái đơn, dù tài liệu Shopee nói
    chỉ che ở Đài Loan. Đừng hứa tính năng gọi khách dựa trên field này. **Địa chỉ tỉnh/thành
    trả về không chuẩn hoá** (một tỉnh nhiều cách viết, có/không tiền tố "Tỉnh"/"Thành phố") →
    phải tự chuẩn hoá trước khi gộp nhóm, không thì một tỉnh bị tách làm đôi trong báo cáo.

### Trả hàng

11. **Hai cờ mới từ 17/08/2026** trong `returns.get_return_list` và `get_return_detail`:
    `is_partial_quantity_return` (khách chỉ trả một phần số lượng) và
    `is_refund_amount_adjusted` (tiền hoàn thấp hơn mức tối đa). Hồ sơ cũ không có hai field
    này. Lưu cột **cho phép NULL** và phân biệt ba trạng thái: vắng field → `None`; có và
    `False` → `False`; có và `True` → `True`.
    - Đừng `bool(detail.get(...))` — nó gộp "Shopee chưa trả lời" với "Shopee trả lời không".
    - Khi cập nhật bản ghi có sẵn, dùng `x if x is not None else cu`, **không** dùng `x or cu`:
      với boolean, `False or True` ra `True` → cờ kẹt ở `True` vĩnh viễn.
12. Bảng hồ sơ trả hàng nên **lưu JSON thô** của phản hồi. Shopee thêm field mới thường xuyên;
    bộ đọc dùng `.get()` không vỡ nhưng field lạ trôi qua và mất, muốn có lại phải kéo lại toàn bộ.

### Quảng cáo, hạn mức, lưu giữ

13. 🔴 **Endpoint hiệu quả GMV Max (`ads.get_gms_campaign_performance`,
    `ads.get_gms_item_performance`) có hạn mức chùm rất thấp: khoảng 3 lệnh gọi sát nhau mỗi
    shop**, lệnh thứ 4 dính `ads_rate_limit_shop_api`. Hạn mức này không có trong tài liệu và
    gọi thử một lần thì luôn qua, nên rất khó thấy. Có dấu hiệu lệnh gọi **lỗi** cũng tính vào
    hạn mức, nên đừng "thử lại cho chắc". Cách làm đã chạy ổn: mỗi lượt chỉ 2 lệnh gọi mỗi shop
    (ví dụ lượt sáng sớm kéo D-1, vài giờ sau lượt khác kéo D-2), giãn ≥ 2 giây giữa các trang.
    Hai lượt gối nhau còn là lưới an toàn: một lượt chết không thành lỗ dữ liệu.
14. **Đừng gộp nhiều lệnh gọi vào một transaction rồi rollback cả shop khi một lệnh lỗi.**
    Chúng tôi từng mất 5 tuần dữ liệu quảng cáo vì vậy: lệnh 1–3 qua, lệnh 4 dính hạn mức,
    rollback xoá cả 3 lệnh đã qua, log chỉ ghi "shop lỗi" không ghi lệnh thứ mấy. Commit theo
    từng đơn vị dữ liệu (ví dụ theo ngày), và log endpoint + ngày + `request_id` cho từng lệnh hỏng.
15. **Job xử lý nhiều shop phải có ngưỡng "tất cả shop hỏng = job hỏng".** Nếu job chỉ nuốt lỗi
    từng shop rồi báo "ok", heartbeat sẽ nói dối hàng tuần liền.
16. **Số liệu quảng cáo: phân biệt `direct_*` và `broad_*`.** `broad_order` / `broad_gmv` là
    quy công rộng (gồm cả đơn đến từ affiliate, livestream, tự nhiên; đếm cả dòng quà 0 đồng);
    muốn đánh giá hiệu quả **chính chiến dịch** thì dùng `direct_order`. Với GMV Max,
    `direct_gmv` luôn bằng 0 (Shopee không trả), chỉ `direct_order` dùng được. GMV quảng cáo
    tính cả đơn sau này bị huỷ.
17. **Shopee chỉ giữ dữ liệu một thời gian**: số liệu traffic ~183 ngày, quảng cáo ~90 ngày.
    Cần lịch sử dài hơn thì phải kéo về DB của mình **từ sớm** — sau này không lấy lại được.
    Nhóm `account_health`: `get_penalty_point_history` chỉ trả **quý hiện tại**, muốn có lịch
    sử điểm phạt phải tự lưu; `get_punishment_history` bắt buộc truyền `punishment_status`.

### Chung

18. **Cột enum trong DB đặt VARCHAR ≥ 64.** Shopee có mã dài 35+ ký tự
    (`ADJUSTMENT_FOR_RR_AFTER_ESCROW_VERIFIED`, `AMS_COMMISSION_FEE_REFUND_DEDUCT`); đặt 32 là
    tràn cột giữa production. `promotion_id` / `activity_id` là uint64 → dùng `BIGINT`.
19. **Đồng hồ máy chủ phải chuẩn (NTP).** Chữ ký HMAC gắn timestamp; lệch quá ~5 phút là sai
    chữ ký toàn bộ, mà thông báo lỗi trả về không hề gợi ý nguyên nhân này.
20. **Thời gian đều là unix giây UTC**, và khoảng truy vấn `time_from`/`time_to` của
    `get_order_list` **tối đa 15 ngày** — cần dài hơn thì tự cắt đoạn rồi lặp.
21. **Ghi log `request_id`** cho mọi lỗi. Không có nó thì làm việc với Shopee support gần như
    không đi tới đâu.

## 7. Bẫy vận hành app (khoá partner, IP, push)

### 7.1. Live Partner Key có hạn dùng khoảng 6 tháng

Shopee đặt **hạn ~6 tháng** cho Live API Partner Key (xem ở Console → App). Hết hạn = **mọi**
lệnh gọi API dừng. Shopee chỉ nhắc qua email và một dấu chấm than trên Console, không có trong API.

Đã xoay khoá thật và kiểm được:

- **Xoay khoá (nút Reset) đặt lại đồng hồ** — hạn mới ≈ 6 tháng kể từ lúc xoay.
- **Có cửa sổ chuyển tiếp ~24 giờ**: khoá cũ còn chạy thêm 24 giờ sau khi bấm Reset, nên không
  phải "bấm là chết ngay". Vẫn nên thay khoá trong hệ thống liền tay.
- **Ô hạn dùng trên Console chỉ cập nhật SAU khi cửa sổ 24 giờ đóng.** Đọc ngay sau khi xoay sẽ
  thấy hạn cũ và tưởng xoay không ăn — đọc lại sau 24 giờ.
- **Xoay khoá KHÔNG huỷ token của các shop** (không phải authorize lại) và **KHÔNG đổi khoá
  push** (khoá ký webhook là khoá riêng ở mục Push Mechanism).
- Khoá mới chỉ hiện **một lần**: dán vào chỗ an toàn và kiểm độ dài (64 ký tự) **trước** khi
  đóng hộp thoại. Khoá app có dạng `shpk` + 60 ký tự hex; khoá push là 64 hex trần, không có tiền
  tố — đừng kiểm định dạng cứng theo `shpk`.
- Nên có job tự nhắc trước hạn (30 / 14 / 7 ngày rồi mỗi ngày). Chụp màn hình Console thì che ô khoá.

### 7.2. IP whitelist — nay nằm ở "PII Necessity Declaration"

Từ 16/10/2026, ô "IP Address Whitelist" được thay bằng **PII Necessity Declaration**
(Console → App list → Go Live). Bật = chỉ IP đã khai mới gọi được Open API (mọi API, không chỉ
API có dữ liệu cá nhân). Khai IP: Console → App list → Go Live → PII Necessity Declaration →
APP IP Address Management → thêm IP → Submit.

- **403 `source_ip_undeclared` xuất hiện đột ngột** thường chỉ là IP động của nhà mạng đổi
  (hay xảy ra rạng sáng), không phải bị tấn công. Chẩn nhanh: so IP hiện tại
  (`curl ifconfig.me`) với IP đã khai.
- **Khai IP xong, 403 chưa hết ngay.** Gateway Shopee lan whitelist không đều trong khoảng
  4 phút: cùng IP, cùng endpoint trả xen kẽ 200 và 403. Cảnh báo kiểu "lệnh gọi gần nhất quyết
  định trạng thái" sẽ bắn hàng chục tin trong vài phút. Chỉ báo "đã thông lại" khi đã yên
  khoảng 10 phút không có 403.
- Trong lúc bị chặn, đừng để worker liên tục retry hay refresh token — vô ích và làm đầy log.
  Nếu job kéo đơn luôn quét lùi một cửa sổ đủ rộng (ví dụ 24 giờ) thì khi thông lại sẽ tự lấy
  đủ đơn, không mất dữ liệu.

### 7.3. Webhook (push) — đo dữ liệu thật, đừng tin tài liệu

- **Push mã 5 (`shopee_updates`, tin hộp thư Seller Centre)**: tài liệu mô tả `data.actions[]`,
  nhưng dữ liệu thật Shopee gửi là **`data` dạng danh sách** `[{...}]`. Bộ xử lý đọc theo tài
  liệu sẽ không thấy gì, mà vẫn đánh dấu "đã xử lý" → rơi tin im lặng (chúng tôi mất 4 tuần tin
  hộp thư như vậy). Mã 5 phải bật tay trong Console → Push Mechanism.
- Quy tắc chung: **lưu payload thô của mọi webhook** vào một bảng log, viết bộ xử lý dựa trên
  payload thật đã lưu, và khi kiểm một đường push thì nhìn cả hai đầu (bảng log và bảng đích).
- **Xác thực chữ ký tự viết** — SDK không có hàm cho việc này (module `push` chỉ có
  `get_app_push_config`, `set_app_push_config`, `get_lost_push_message`,
  `confirm_consumed_lost_push_message`). Dùng **khoá push** (Console → Push Mechanism), không
  phải partner key:

  ```python
  import hashlib, hmac

  def chu_ky_hop_le(url: str, raw_body: bytes, header_authorization: str, push_key: str) -> bool:
      base = url.encode("utf-8") + b"|" + raw_body
      mong_doi = hmac.new(push_key.encode("utf-8"), base, hashlib.sha256).hexdigest()
      return hmac.compare_digest(mong_doi, (header_authorization or "").strip().lower())
  ```

  `url` phải đúng **URL công khai đã khai trên Console** (có `https://`). Chạy sau proxy /
  tunnel thì ứng dụng thấy `http://` và host nội bộ → dựng lại từ `X-Forwarded-Proto` và
  `X-Forwarded-Host`, nếu không mọi chữ ký đều sai. `raw_body` là byte gốc, không parse rồi
  dump lại.
- **Luôn trả 2xx với body RỖNG, trong 3 giây.** Body không rỗng hoặc mã khác 2xx bị tính là
  thất bại; Shopee gửi lại sau 5 phút, 30 phút, 3 giờ. Tỷ lệ thành công dưới 70% thì bị email
  cảnh báo, dưới 30% thì Shopee **tắt đăng ký push**. Vì vậy chữ ký sai hay mã lạ cũng trả 200
  (rồi log lại); ghi payload vào DB trước, xử lý nặng để worker làm sau.
- Push bị lỡ (máy chủ sập, IP bị chặn) lấy lại được bằng `push.get_lost_push_message` rồi
  `push.confirm_consumed_lost_push_message`.

## 8. Tra cứu nhanh

- **Tài liệu một API ở dạng JSON** (kèm bảng mã enum), không cần đăng nhập:
  `https://open.shopee.com/opservice/api/v1/doc/api/?version=2&api_name=v2.<module>.<hàm>`
  (ví dụ `api_name=v2.order.get_order_list`).
- **Danh sách tên hàm và tham số của SDK**: tệp `pyshopee2/endpoint_registry.json` trong
  site-packages sau khi cài wheel.
- **Theo dõi thay đổi API (Announcement) mà không cần đăng nhập**:
  - Danh sách: `GET https://open.shopee.com/opservice/api/v1/content/list?category_id=3&page_size=40&page_index=1`
    → `{total, data: [{id, release_time, title, content, is_top}]}`
  - Chi tiết: `GET https://open.shopee.com/opservice/api/v1/content/detail?id=<id>`
    → có thêm `related_api_categories`.
  - Bài có tiêu đề bắt đầu "Significant OpenAPI Updates" là thay đổi API thật; bài gắn thẻ
    `[BR]`, `[TW]`, `[PH]`… chỉ áp cho thị trường đó. Shopee đăng khoảng 1–2 bài API mỗi tuần;
    một job đọc hai lần mỗi ngày, so với danh sách API bạn đang gọi rồi báo khi dính là đủ.
- Một số chương trình trên Seller Centre **không có Open API** (ví dụ "Sản phẩm hot"); trước khi
  hứa tự động hoá, tra danh sách Announcement và registry ở trên.

## 9. Sandbox

`Client(..., test_env=True)` → trỏ về host sandbox. Cần app + shop test riêng tạo trong
console. Dữ liệu sandbox rất nghèo: kiểm luồng authorize / chữ ký / phân trang thì tốt, còn
nghiệp vụ thật gần như phải test trên live với shop thật (nên dùng một shop phụ, và chỉ gọi
endpoint đọc cho tới khi chắc chắn).

---

## Lịch sử thay đổi

- **12/11/2026** — Bổ sung kiến thức chạy thật 08–11/2026: tiền về sau điều chỉnh (bẫy 1),
  kéo lại quyết toán và đối chiếu ví (bẫy 4–5), đơn đổi trạng thái mà `update_time` đứng yên
  (bẫy 7), `main_item` và giá trong đơn (bẫy 8–9), che tên người nhận (bẫy 10), hai cờ trả hàng
  mới (bẫy 11–12), hạn mức GMV Max và thiết kế job nhiều shop (bẫy 13–16), `account_health`
  (bẫy 17); mục 7 mới (hạn khoá partner, IP whitelist kiểu mới, webhook mã 5); mục 8 mới (tra
  cứu); script chạy riêng không được refresh token (mục 5.1); `warning` của `get_order_list`
  (mục 5.2). Thư viện không đổi.
- **10/08/2026** — Bản đầu: shopee-open-sdk 2.1.1 + hướng dẫn triển khai, 11 bẫy.

*Đóng gói từ kinh nghiệm chạy Shopee Open API v2 trên môi trường production. Chúc bạn build vui.*
