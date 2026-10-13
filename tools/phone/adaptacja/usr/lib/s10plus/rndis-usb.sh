#!/bin/bash
# Siec po kablu USB: gadzet g1 z funkcja RNDIS i adresem 169.254.172.1 (link-local, PC sam
# nadaje sobie adres z tej puli, bez DHCP).  Windows bierze sterownik RNDIS sam, przez
# deskryptory Microsoft OS (os_desc), Linux przez rndis_host.  usb-tethering z hybris-usb
# na tym jadrze nie dziala (nie umie zalozyc funkcji sieciowej), dlatego gadzet tworzymy tu.
# Idempotentne: jesli rndis0 juz ma adres, nic nie robi.
G=/sys/kernel/config/usb_gadget/g1
UDC=10c00000.dwc3
IP=169.254.172.1/16
if ip -br addr show rndis0 2>/dev/null | grep -q "169.254.172.1"; then exit 0; fi
[ -d /sys/kernel/config/usb_gadget ] || mount -t configfs none /sys/kernel/config 2>/dev/null
if [ ! -d "$G" ]; then
	mkdir -p $G/strings/0x409 $G/configs/c.1/strings/0x409 || exit 1
	echo 0x0fce > $G/idVendor     # te same identyfikatory co domyslny profil hybris-usb
	echo 0x7169 > $G/idProduct
	echo "Droidian Galaxy S10+" > $G/strings/0x409/manufacturer
	echo "Galaxy S10+" > $G/strings/0x409/product
	cut -c1-16 /etc/machine-id > $G/strings/0x409/serialnumber 2>/dev/null
	echo "RNDIS" > $G/configs/c.1/strings/0x409/configuration
fi
echo "" > $G/UDC 2>/dev/null; sleep 1
rm -f $G/configs/c.1/ncm.usb0 2>/dev/null
rm -f $G/configs/c.1/rndis.usb0 2>/dev/null
mkdir -p $G/functions/rndis.usb0 2>/dev/null
echo 1 > $G/os_desc/use 2>/dev/null
echo 0xcd > $G/os_desc/b_vendor_code 2>/dev/null
echo MSFT100 > $G/os_desc/qw_sign 2>/dev/null
echo RNDIS > $G/functions/rndis.usb0/os_desc/interface.rndis/compatible_id 2>/dev/null
echo 5162001 > $G/functions/rndis.usb0/os_desc/interface.rndis/sub_compatible_id 2>/dev/null
[ -e $G/os_desc/c.1 ] || ln -s $G/configs/c.1 $G/os_desc/c.1 2>/dev/null
ln -sf $G/functions/rndis.usb0 $G/configs/c.1/rndis.usb0 2>/dev/null
echo $UDC > $G/UDC 2>/dev/null; sleep 2
for IFN in usb0 rndis0; do
  if [ -e /sys/class/net/$IFN ]; then
    ip link set $IFN up; ip addr flush dev $IFN; ip addr add $IP dev $IFN 2>/dev/null
  fi
done
exit 0
