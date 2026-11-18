# Lightsail sunucusuna WireGuard VPN kurulumu

Oyun sunucusuna dokunmaz. VPN yalnızca **UDP 51820** portunu ve `10.8.0.0/24` iç ağını kullanır. Kaynak kullanımı çok düşüktür (kernel modülü, ayrı bir servis/Docker gerekmez).

## 1. Lightsail firewall
Lightsail konsolu > sunucu > **Networking** > IPv4 Firewall > **Add rule**
- Application: Custom, Protocol: **UDP**, Port: **51820** > Save

## 2. Sunucuda kurulum (SSH ile, bir kez)
```bash
# betiği sunucuya kopyalayın (ör. scp wg-kur.sh ubuntu@SUNUCU_IP:~)
sudo bash wg-kur.sh
```

## 3. Cihaz ekleme
```bash
sudo bash wg-kur.sh ekle telefon
sudo bash wg-kur.sh ekle pc
```
Her komut ekrana bir QR kod basar ve `/etc/wireguard/clients/<isim>.conf` dosyasını oluşturur.

## 4. İstemciler (resmi WireGuard uygulamaları, ücretsiz)
- **Android / iOS:** WireGuard uygulaması > **+** > *QR koddan oluştur* > terminaldeki kodu tara.
- **Windows / macOS:** wireguard.com/install > uygulamayı kur > *Import tunnel from file* > `pc.conf` dosyasını seç.
  Dosyayı almak için: `scp ubuntu@SUNUCU_IP:/etc/wireguard/clients/pc.conf .` (önce sunucuda `sudo cp` ile ev dizinine kopyalayın)

## Diğer komutlar
- `sudo bash wg-kur.sh liste` : cihazlar ve son bağlantı zamanları
- `sudo bash wg-kur.sh sil telefon` : cihazı iptal et

## Notlar
- Her cihaza ayrı config verin; kaybolan cihazı `sil` ile kapatırsınız.
- Lightsail aylık veri kotası (plana göre 1–3 TB) VPN trafiğini de kapsar; kotayı aşan trafik ücretlendirilir.
- Tüm internet trafiği sunucudan çıkar; sitelere sunucunun IP'si görünür.
