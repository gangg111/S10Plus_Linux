### Linux on the Samsung Galaxy S10+ (SM-G975F, Exynos 9820)

**English** | [Polski](README.pl.md)

Mainline-based Linux for the **Exynos** Galaxy S10+ (`beyond2lte`): our own U-Boot
bootloader (upstream U-Boot plus the patches in `patches-uboot/`), a mainline-based
kernel, and a full **Droidian** device adaptation (Plasma Mobile with a One UI look).

> This is **only** for the Exynos **SM-G975F** (`beyond2lte`). It is **not** for the
> Snapdragon S10+ (SM-G975U / SM-G975W), nor for the S10 / S10e. Flashing it on another
> model will not boot and can brick the device.

Ready-to-flash images are on the [Releases page](https://github.com/gangg111/S10Plus_Linux/releases/latest).

### What works

Two images are offered. **pmOS** is a small quick-start to confirm your phone boots this
stack; **Droidian** is the full daily driver.

| | pmOS (quick-start) | Droidian (full) |
|---|---|---|
| Boots via our U-Boot | yes | yes |
| Display | simple framebuffer | 60 fps, hardware DECON pipeline |
| Touch | yes | yes |
| Wi-Fi | no | yes (BCM4375) |
| Mobile data / calls | no | yes (needs a SIM) |
| Audio (speaker + mics) | no | yes |
| Camera | no | yes (Camera2 / libcamera path) |
| Hardware video decode | no | yes (MFC: H.264 / HEVC) |
| GPS, sensors, fingerprint | no | GPS + sensors yes; fingerprint partial |
| Deep sleep (suspend to RAM) | no | yes, hands-free auto-suspend with ~1 s wake |
| Desktop | console / framebuffer | Plasma Mobile, One UI theme |

Status is honest and moving; the Droidian image is the real phone the author uses daily.

### Before you start (read this)

- **Flashing the rootfs wipes userdata** (all your Android data). Back it up first.
- Your **bootloader must be unlocked** (OEM unlocking). On an Exynos Samsung this trips
  **Knox permanently** (warranty bit) and cannot be undone.
- The **first partition layer (efs / IMEI / keys) is never touched** by these images.
- You can always go back to stock Android with Odin (see **Recovery** below).
- Do this with a **charged battery** and a cable you trust.

### You need

- A Samsung Galaxy S10+ **SM-G975F**.
- A Windows PC with **Odin 3.14+** and the **Samsung USB drivers** installed
  (on Linux you can use **Heimdall** instead).
- A USB cable.
- The two files from the [latest release](https://github.com/gangg111/S10Plus_Linux/releases/latest):
  - `uboot-s10plus.tar.md5` — our U-Boot, flashes to the **boot** partition.
  - `pmos-s10plus-userdata.tar.md5` — the pmOS rootfs, flashes to **userdata**.
  - The full **Droidian** image is added to the same release when its clean build is
    published; until then, build it yourself (see **Build from source**).

### Install with Odin (Windows)

1. On stock Android, enable **Settings → Developer options → OEM unlocking**.
2. Power the phone off. Enter **Download mode**: with the phone off, hold **Volume Up +
   Volume Down together**, then plug the USB cable into the PC. A warning screen appears;
   press **Volume Up** to continue. If the bootloader is still locked, **long-press Volume
   Up** to unlock it (this wipes the phone).
3. Open **Odin**. The phone shows up as a blue **Added!!** box in the log.
4. Put `uboot-s10plus.tar.md5` in the **AP** slot and press **Start**. This replaces the
   boot partition with our U-Boot. (The file name inside the archive is `boot.img`, so Odin
   targets the boot partition automatically.)
5. The phone reboots into U-Boot. Put it back into Download mode (step 2), put
   `pmos-s10plus-userdata.tar.md5` in **AP**, press **Start**. This writes the Linux rootfs
   to userdata and **wipes Android**. (Inside it is `userdata.img`.)
6. Reboot. U-Boot comes up, finds the EFI system partition inside userdata, and boots Linux.

Leave **BL**, **CP** and **CSC** empty in Odin, and keep **Re-Partition** off. Odin reads
only `ustar` archives with an appended MD5; the files above are packed exactly that way.

### First boot and login

- The first boot is slower (filesystem resize). Give it a minute.
- **Droidian** logs in as user `droidian`. The default password is `1234`. Change it.
- **pmOS** boots to the generic postmarketOS image; use the credentials baked into that
  image. (If you are unsure, flash Droidian instead; it is the supported daily driver.)

### Recovery (back to stock Android)

1. Download the **stock firmware** for your exact SM-G975F (match your region / CSC) from a
   firmware source you trust. It comes as four files: BL, AP, CP, CSC.
2. In Odin, load BL/AP/CP/CSC into their slots and flash. This restores Android.
3. Knox stays tripped (that is permanent), but the phone is a normal S10+ again.

### Build from source

Everything here is reproducible; nothing is a vendor blob you cannot rebuild.

- **U-Boot**: upstream U-Boot plus `patches-uboot/` (see `patches-uboot/README.md`), packed
  for Odin by `scripts/pack-uboot-odin.sh`.
- **pmOS rootfs**: packed for Odin by `scripts/pack-pmos-odin.sh`.
- **Kernel and the mainline patch series**: `patches/`, `scripts/`, `SOURCES.md`; see
  `docs/mainline-submission.md` for the developer and upstreaming notes.
- **Droidian device adaptation** (the `.deb` with the One UI look, modem, audio, sensors,
  deep-sleep daemon, and the rest): `tools/phone/adaptacja/`.

### Credits and license

Port and adaptation by **Artur Szafraniec**. The kernel and U-Boot changes are submitted as
regular upstream patches (see `docs/mainline-submission.md` and `patches-uboot/`). Each
component keeps the license of its upstream project.
