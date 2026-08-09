"""Ví dụ chạy được ngay với shopee-open-sdk (pyshopee2).

Luồng: (đã authorize shop, có sẵn access_token) → kéo TOÀN BỘ đơn 24h gần nhất
(có phân trang) → lấy chi tiết theo lô 50 → đọc tiền thực về ví của đơn đầu tiên.

LƯU Ý 2 điểm khác trực giác, đã kiểm bằng mã nguồn SDK:
  1) get_token()/get_access_token() trả về TUPLE (access_token, expire_in, refresh_token)
  2) SDK NÉM ShopeeRequestError cho cả lỗi nghiệp vụ — không trả dict lỗi.
     Nên KHÔNG có chuyện `if resp.get("error")`; phải bọc try/except.
"""
from __future__ import annotations

import time

from pyshopee2 import Client, ShopeeRequestError

# ==== ĐIỀN CỦA BẠN (app riêng — không dùng chung partner_id với hệ thống khác) ====
PARTNER_ID = 0
PARTNER_KEY = "your_partner_key"
REDIRECT_URL = "https://your-domain.com/shopee/callback"
SHOP_ID = 0
ACCESS_TOKEN = "your_access_token"

LO_CHI_TIET = 50   # get_order_detail: tối đa 50 đơn/lần
TRANG = 100        # get_order_list: tối đa 100 đơn/trang


def lay_tat_ca_ma_don(client: Client, t_from: int, t_to: int) -> list[str]:
    """Phân trang tới khi hết — dừng theo cờ `more`, KHÔNG dừng theo số lượng trả về."""
    cursor, ra = "", []
    while True:
        body = client.order.get_order_list(
            time_range_field="create_time",
            time_from=t_from,
            time_to=t_to,
            page_size=TRANG,
            cursor=cursor,
        )["response"]

        ra += [o["order_sn"] for o in body.get("order_list", [])]

        if not body.get("more"):
            break
        cursor = body["next_cursor"]
    return ra


def main() -> None:
    client = Client(
        shop_id=SHOP_ID,
        partner_id=PARTNER_ID,
        partner_key=PARTNER_KEY,
        redirect_url=REDIRECT_URL,
        access_token=ACCESS_TOKEN,
    )

    now = int(time.time())
    try:
        ma_don = lay_tat_ca_ma_don(client, now - 86400, now)
        print(f"{len(ma_don)} đơn trong 24h gần nhất")
        if not ma_don:
            return

        # Chi tiết theo lô 50. response_optional_fields là OPT-IN:
        # không xin thì API im lặng không trả field đó.
        for i in range(0, len(ma_don), LO_CHI_TIET):
            lo = ma_don[i:i + LO_CHI_TIET]
            detail = client.order.get_order_detail(
                order_sn_list=",".join(lo),
                response_optional_fields=(
                    "item_list,total_amount,pay_time,order_status,recipient_address"
                ),
            )["response"]["order_list"]

            for don in detail[:3]:   # in thử 3 đơn đầu mỗi lô
                print(f"  {don['order_sn']} · {don.get('order_status')} · "
                      f"{don.get('total_amount', 0):,}đ · "
                      f"{len(don.get('item_list', []))} sản phẩm")

        # Tiền THỰC về ví — nguồn số đúng cho doanh thu (escrow âm là bình thường)
        sn = ma_don[0]
        income = client.payment.get_escrow_detail(order_sn=sn)["response"].get("order_income", {})
        tien = income.get("escrow_amount")
        if tien is None:
            print(f"{sn}: Shopee chưa quyết toán (chưa có escrow)")
        else:
            print(f"{sn}: tiền thực về ví = {tien:,}đ")

    except ShopeeRequestError as e:
        # payload đã tự che access_token/refresh_token/partner_key/sign → log an toàn.
        # LUÔN log request_id: Shopee support hỏi cái này đầu tiên.
        print(f"Shopee lỗi: code={e.error} http={e.status_code} request_id={e.request_id}")


if __name__ == "__main__":
    main()
