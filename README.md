# Kardeşler VPN

Zar masası Lightsail sunucusu üzerinde çalışan özel WireGuard VPN.

- `server/` : sunucu kurulumu (`wg-kur.sh`), cihaz kayıt API'si (`vpn-api.py`) ve rehber (`REHBER.md`)
- **İndir:** telefon https://github.com/turniphead0/priv-vpn/releases/download/son/KardeslerVPN.apk · bilgisayar https://github.com/turniphead0/priv-vpn/releases/download/son/KardeslerVPN.exe
- `desktop/` : Windows uygulaması (.NET 8, WinForms). Resmi WireGuard bileşenini arka planda kullanır, yoksa ilk bağlantıda kendisi kurar. Actions > Windows uygulamasi > `KardeslerVPN-windows`.
- `app/` : Android uygulaması (Kotlin, resmi WireGuard tünel kütüphanesi). APK, GitHub Actions'ta derlenir: Actions > Android APK > son çalıştırma > `KardeslerVPN-apk`.
