# Internet orqali ko‘rish havolasi

2026-09-14: foydalanuvchi VPNsiz internet havolasini so‘radi. Cloudflare Quick Tunnel mahalliy `127.0.0.1:8082` gateway'ga ulandi; gateway asosiy `127.0.0.1:8080` panelga uzatadi. Router porti va Windows firewall qoidalari o‘zgartirilmagan. Tailscale Funnel yoqilmagani sabab ishlatilmadi; tailnet siyosati o‘zgartirilmagan.

To‘liq havola `admin-panel/data/share-preview.json` ichidagi `public_origin + '/open/' + token` dan tuziladi. Tokenni ommaviy hujjat yoki Git'ga qo‘shmang. Domenning o‘zi, haqiqiy maxsus havola ochilmaguncha, panelni ko‘rsatmaydi.

Gateway 256 bitli tasodifiy havola tokenini tekshiradi va 12 soatga Secure/HttpOnly kirish cookie'sini beradi. Bundan keyin odatdagi panel login/MFA va foydalanuvchi vakolatlari ishlaydi. Har bir brauzerning ilova sessiyasi alohida. Javoblar cache va indekslashdan chiqarilgan; token ilova serveriga uzatilmaydi va gateway access log'iga yozilmaydi.

Havola ushbu kompyuter, ilova, gateway va tunnel ishlayotgan paytda mavjud. Cloudflare Quick Tunnel qayta ishga tushirilsa domen yangilanadi. Doimiy hosting yoki domen sozlanmagan.

Jarayonlar:

```powershell
# admin-panel papkasidan, alohida terminallarda:
python -B -X utf8 run.py
python -B -X utf8 share_preview.py
.\.tools\cloudflared.exe tunnel --no-autoupdate --url http://127.0.0.1:8082 --protocol http2
```

Gateway bog‘liqliklari `requirements-preview.txt` da. Cloudflared rasmiy Cloudflare GitHub relizidan olindi. Tunnelni to‘xtatish tashqi kirishni yopadi; mahalliy panel ishlashda davom etadi. Tokenni almashtirib gateway'ni qayta ishga tushirish eski havola va kirish cookie'larini bekor qiladi.

Tekshirildi: tokensiz kirish rad etilishi, secure cookie, sessiyalar ajratilishi, cookie muddati, ommaviy HTTPS orqali CSRF/login/MFA, bosh sahifa, hududlar, HTMX, CSS va autentifikatsiyalangan WebSocket.


## Tuzatish (2026-09-14, kechqurun)

Brauzer orqali kirishda `POST /kirish` 403 (CSRF) qaytargan: gateway barcha javoblarga `Referrer-Policy: no-referrer` qo'ygan edi, shu siyosat bilan brauzer forma yuborishda `Origin: null` yuboradi, ilova esa uni bir xil manba deb hisoblamaydi (`curl`/`httpx` sinovlarida Origin qo'lda berilgani uchun sezilmagan). Endi proksi javoblarida `Referrer-Policy: same-origin`, maxsus havola (`/open/...`) javobida avvalgidek `no-referrer`. CSRF middleware rad etish sababini (`cookie_yoq`, `origin_mos_emas`, `token_yoq`, `token_mos_emas`) token qiymatlarisiz server logiga yozadi. Brauzerda tunnel orqali kirish → MFA → bosh sahifa (3D xarita) tekshirildi.
