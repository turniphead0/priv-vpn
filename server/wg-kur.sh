#!/usr/bin/env bash
# Lightsail (Ubuntu/Debian) icin WireGuard VPN kurulumu.
# Mevcut oyun sunucusuna dokunmaz: sadece UDP 51820 ve 10.8.0.0/24 agini kullanir.
#
# Kullanim:
#   sudo bash wg-kur.sh                 # sunucuyu kurar (bir kez)
#   sudo bash wg-kur.sh ekle telefon    # yeni istemci ekler, QR kodu basar
#   sudo bash wg-kur.sh ekle laptop
#   sudo bash wg-kur.sh sil telefon     # istemciyi kaldirir
#   sudo bash wg-kur.sh liste           # istemcileri ve son baglantilari gosterir
set -euo pipefail

WG_PORT="${WG_PORT:-51820}"
WG_NET="10.8.0"
WG_DIR="/etc/wireguard"
CLIENT_DIR="$WG_DIR/clients"
DNS="${WG_DNS:-1.1.1.1, 1.0.0.1}"

[ "$(id -u)" -eq 0 ] || { echo "sudo ile calistirin."; exit 1; }

public_ip() {
  curl -fsS --max-time 5 https://checkip.amazonaws.com 2>/dev/null || hostname -I | awk '{print $1}'
}

kur() {
  if [ -f "$WG_DIR/wg0.conf" ]; then
    echo "WireGuard zaten kurulu ($WG_DIR/wg0.conf). Istemci eklemek icin: sudo bash $0 ekle <isim>"
    exit 0
  fi
  if ss -lun | grep -q ":$WG_PORT "; then
    echo "UDP $WG_PORT baska bir servis tarafindan kullaniliyor. WG_PORT=51821 gibi baska bir port verin."; exit 1
  fi

  apt-get update -y
  DEBIAN_FRONTEND=noninteractive apt-get install -y wireguard qrencode iptables curl

  IFACE="$(ip -4 route show default | awk '{print $5; exit}')"
  umask 077
  mkdir -p "$CLIENT_DIR"
  wg genkey | tee "$WG_DIR/server.key" | wg pubkey > "$WG_DIR/server.pub"

  cat > "$WG_DIR/wg0.conf" <<CONF
[Interface]
Address = $WG_NET.1/24
ListenPort = $WG_PORT
PrivateKey = $(cat "$WG_DIR/server.key")
PostUp = iptables -t nat -A POSTROUTING -s $WG_NET.0/24 -o $IFACE -j MASQUERADE; iptables -A FORWARD -i wg0 -j ACCEPT; iptables -A FORWARD -o wg0 -m state --state RELATED,ESTABLISHED -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -s $WG_NET.0/24 -o $IFACE -j MASQUERADE; iptables -D FORWARD -i wg0 -j ACCEPT; iptables -D FORWARD -o wg0 -m state --state RELATED,ESTABLISHED -j ACCEPT
CONF

  echo "net.ipv4.ip_forward=1" > /etc/sysctl.d/99-wireguard.conf
  sysctl -p /etc/sysctl.d/99-wireguard.conf

  # ufw aciksa portu ac (Lightsail firewall'i ayrica panelden acilmali)
  if command -v ufw >/dev/null && ufw status | grep -q "Status: active"; then
    ufw allow "$WG_PORT/udp"
    sed -i 's/^DEFAULT_FORWARD_POLICY=.*/DEFAULT_FORWARD_POLICY="ACCEPT"/' /etc/default/ufw
    ufw reload
  fi

  systemctl enable --now wg-quick@wg0
  echo
  echo "Sunucu hazir. Simdi Lightsail panelinde Networking > IPv4 Firewall > Add rule: Custom, UDP, $WG_PORT"
  echo "Sonra istemci ekleyin: sudo bash $0 ekle telefon"
}

ekle() {
  local name="${1:?istemci adi gerekli}"
  [ -f "$WG_DIR/wg0.conf" ] || { echo "Once kurulum yapin: sudo bash $0"; exit 1; }
  [ -f "$CLIENT_DIR/$name.conf" ] && { echo "$name zaten var."; qrencode -t ansiutf8 < "$CLIENT_DIR/$name.conf"; exit 0; }

  local n=2
  while grep -q "AllowedIPs = $WG_NET.$n/32" "$WG_DIR/wg0.conf"; do n=$((n+1)); done
  [ "$n" -lt 255 ] || { echo "Adres kalmadi."; exit 1; }

  umask 077
  local priv pub psk
  priv="$(wg genkey)"; pub="$(echo "$priv" | wg pubkey)"; psk="$(wg genpsk)"

  cat >> "$WG_DIR/wg0.conf" <<CONF

# client: $name
[Peer]
PublicKey = $pub
PresharedKey = $psk
AllowedIPs = $WG_NET.$n/32
CONF

  cat > "$CLIENT_DIR/$name.conf" <<CONF
[Interface]
PrivateKey = $priv
Address = $WG_NET.$n/32
DNS = $DNS

[Peer]
PublicKey = $(cat "$WG_DIR/server.pub")
PresharedKey = $psk
Endpoint = $(public_ip):$WG_PORT
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
CONF

  wg syncconf wg0 <(wg-quick strip wg0)
  echo "Istemci '$name' eklendi. Config dosyasi: $CLIENT_DIR/$name.conf"
  echo "Telefonda WireGuard uygulamasi > + > QR kod tara:"
  qrencode -t ansiutf8 < "$CLIENT_DIR/$name.conf"
}

sil() {
  local name="${1:?istemci adi gerekli}"
  [ -f "$CLIENT_DIR/$name.conf" ] || { echo "$name yok."; exit 1; }
  # "# client: name" satirindan itibaren o peer blogunu sil
  awk -v n="# client: $name" '
    $0==n {skip=1; next}
    skip && /^# client: / {skip=0}
    !skip' "$WG_DIR/wg0.conf" > "$WG_DIR/wg0.conf.new"
  mv "$WG_DIR/wg0.conf.new" "$WG_DIR/wg0.conf"; chmod 600 "$WG_DIR/wg0.conf"
  rm -f "$CLIENT_DIR/$name.conf"
  wg syncconf wg0 <(wg-quick strip wg0)
  echo "$name silindi."
}

liste() {
  ls "$CLIENT_DIR" 2>/dev/null | sed 's/\.conf$//' || true
  echo; wg show wg0
}

case "${1:-kur}" in
  kur) kur ;;
  ekle) ekle "${2:-}" ;;
  sil) sil "${2:-}" ;;
  liste) liste ;;
  *) echo "Kullanim: $0 [kur|ekle <isim>|sil <isim>|liste]"; exit 1 ;;
esac
