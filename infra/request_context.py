"""
infra/request_context.py
--------------------------
Denetim (audit) kayıtları için istek bilgisi (IP adresi) yardımcısı.

Streamlit bir web sunucusu olduğu için "hangi IP'den" bilgisi
uygulama koduna doğrudan verilmez. Bu modül elde edilebilecek en
güvenilir kaynağı dener; hiçbiri çalışmazsa sessizce boş string
döner (audit kaydı IP olmadan da eksiksiz kalır - kim/ne
zaman/hangi siparişte bilgisi her zaman vardır).

Öncelik sırası:
  1) Ters proxy (nginx / load balancer) arkasında çalışılıyorsa
     X-Forwarded-For header'ı (proxy IP'yi buraya ekler).
  2) X-Real-Ip header'ı (bazı proxy kurulumlarında kullanılır).
  3) Hiçbiri yoksa (eski Streamlit sürümü, doğrudan bağlantı,
     test ortamı vb.) "".

Not: st.context, Streamlit 1.37+ ile eklendi. Daha eski bir
sürümde çalışıyorsa (veya st.context henüz mevcut değilse) bu
fonksiyon hata fırlatmak yerine sadece "" döner.
"""

import streamlit as st


def get_client_ip() -> str:

    try:

        headers = getattr(st.context, "headers", None)

        if not headers:
            return ""

        forwarded = headers.get("X-Forwarded-For")

        if forwarded:
            # "X-Forwarded-For: client, proxy1, proxy2" -> ilk adres
            return forwarded.split(",")[0].strip()

        real_ip = headers.get("X-Real-Ip")

        if real_ip:
            return real_ip.strip()

    except Exception:
        # st.context yoksa / farklı bir ortamda çalışıyorsa
        # (örn. script olarak import edilmiş) audit kaydı IP
        # olmadan devam eder.
        pass

    return ""
