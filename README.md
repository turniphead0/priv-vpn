# Kardeşler VPN

Zar masası Lightsail sunucusu üzerinde çalışan özel WireGuard VPN.

- `server/` : sunucu kurulumu (`wg-kur.sh`), cihaz kayıt API'si (`vpn-api.py`) ve rehber (`REHBER.md`)
- `app/` : Android uygulaması (Kotlin, resmi WireGuard tünel kütüphanesi). APK, GitHub Actions'ta derlenir: Actions > Android APK > son çalıştırma > `KardeslerVPN-apk`.
