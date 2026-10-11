#!/bin/bash
# Idempotentne: jesli rndis0 juz ma IP -> nic. Inaczej przelacz gadzet g1 na RNDIS i nadaj IP.
G=/sys/kernel/config/usb_gadget/g1
UDC=10c00000.dwc3
IP=169.254.172.1/16
if ip -br addr show rndis0 2>/dev/null | grep -q "169.254.172.1"; then exit 0; fi
[ -d "$G" ] || exit 0
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
