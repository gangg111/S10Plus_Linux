### Droidian for the Galaxy S10+: build it yourself from the patches

**English** | [Polski](README.pl.md)

There are two ways to put this Droidian on a Galaxy S10+ (**SM-G975F**, Exynos 9820):

1. **Ready images** from the [Releases page](https://github.com/gangg111/S10Plus_Linux/releases/latest),
   flashed with Odin as described in the [main README](../README.md). Nothing to build.
2. **Build it yourself** from this directory: every change the port makes, as patch series
   against pinned upstream commits, and scripts that turn them into packages and a flashable
   image. This is the way to go if you want to change something, or to see exactly what runs
   on the phone.

Plain Droidian does not run on this phone. Without these patches you hit everything the port
had to solve: a kernel that does not boot under Samsung's bootloader, no audio DSP firmware, no
deep sleep (the watchdog resets the phone in suspend), a shell that freezes after the screen
blanks, a modem that never turns its radio on, and so on. With them the phone is a daily
driver; the only thing that does not work is the **fingerprint reader** (enrollment fails in
the vendor HAL).

### What is in here

| Part | Upstream base (pinned) | Changes | Build script |
|---|---|---|---|
| Kernel (LineageOS 4.14) | `LineageOS/android_kernel_samsung_exynos9820` `a412cfaf` | [`kernel/patches`](kernel/patches), 29 patches | [`kernel/build.sh`](kernel/build.sh) |
| Shell, Plasma Mobile on wayfire | `droidian/plasma-mobile-wf` `91ba13c8` | [`plasma-mobile-wf/patches`](plasma-mobile-wf/patches), 29 patches | [`plasma-mobile-wf/build.sh`](plasma-mobile-wf/build.sh) |
| Settings, One UI look | `plasma-mobile/plasma-settings` `v26.04.0` | [`../tools/phone/plasma-settings-oneui`](../tools/phone/plasma-settings-oneui), 4 patches | shipped prebuilt in the adaptation, see there |
| Camera app | `droidian/droidian-camera` `7071899` | [`../tools/phone/aparat/patches`](../tools/phone/aparat/patches), 8 patches | [`camera/build.sh`](camera/build.sh) |
| Device adaptation | none, our package | [`../tools/phone/adaptacja`](../tools/phone/adaptacja) | [`adaptation/build.sh`](adaptation/build.sh) |
| `qt6-text-input-v3`, `maliit-framework` | Droidian's git, the commits the archive binaries were built from | rebuilt unchanged against the current Qt (the archive binaries still want Qt 6.10.2, which is gone) | [`archive-rebuild/build.sh`](archive-rebuild/build.sh) |
| `libbatman-wrappers` | none | an empty placeholder | [`libbatman-wrappers/build.sh`](libbatman-wrappers/build.sh) |
| Image | `droidian-images/droidian` `b1fe26b4`, `rootfs-templates` `d2212f43` | [`image/`](image): the device entry and 1 patch | [`image/build.sh`](image/build.sh), [`image/pack-odin.sh`](image/pack-odin.sh) |

The upstream commits are pinned in [`env.sh`](env.sh). The series are tested against exactly
those trees: applying each one to its base gives the same source tree (same git tree hash) the
working phone was built from. Kernel `70e417bc`, shell `33a021e1`, settings `fce527c1`. The one
difference in the kernel is a bring-up device tree change that the phone never uses (it boots
the stock DTB, its display nodes are enabled), so it is left out of the series.

The device adaptation carries everything the system needs outside the kernel and the shell:
device node permissions, audio routing (the loudspeaker goes past the protection DSP), the
modem radio and an ofono2mm fix, the deep sleep daemon with its fast wake, screen blank and
wake handling, automatic brightness, touch boost, the boot splash, and the One UI parts of the
desktop. Its `-tools` package ships a few prebuilt binaries; the
[adaptation README](../tools/phone/adaptacja/README.md) names the source of each one.

### What you need

- A PC with Linux, or Windows with **WSL2** (Debian or Ubuntu). The WSL2 kernel already has
  the loop and device-mapper drivers the image step needs.
- **Docker**, about **60 GB** free disk and an internet connection.
- RAM: the arm64 builds run about one compile job per 2 GB (a C++ job under emulation
  takes well over a gigabyte; too many at once took a 15 GB WSL VM down). Set `JOBS=n`
  to choose yourself.
- **arm64 emulation** for the containers (step 1).
- The **ABOX audio firmware** from an S10+ (step 2). It is Samsung's, so it is not in this
  repository.

On Windows, clone the repository **inside WSL** (for example `~/S10Plus_Linux`), not under
`/mnt/c`: files on the Windows drive show up with every permission bit set, and the Debian
build tools then run files they should only read.

### Step 1: tools and arm64 emulation

```bash
sudo apt install docker.io git
sudo usermod -aG docker "$USER"     # log out and in again
docker run --privileged --rm tonistiigi/binfmt --install arm64
ls /proc/sys/fs/binfmt_misc/qemu-aarch64     # must exist
git clone https://github.com/gangg111/S10Plus_Linux.git
cd S10Plus_Linux/droidian
```

### Step 2: ABOX firmware

The audio DSP asks for its firmware before `/vendor` is mounted, so the kernel carries it.
You need these four files from `/vendor/firmware` of an SM-G975F:
`calliope_sram.bin`, `calliope_sram_2.bin`, `calliope_dram.bin`, `calliope_dram_2.bin`.

- From a phone that already runs this Droidian: `scp droidian@<phone>:/android/vendor/firmware/calliope_* abox-fw/`
- From rooted stock Android: `adb pull /vendor/firmware/calliope_sram.bin` (and the other three).

Put them in one directory and point `ABOX_FIRMWARE` at it. The files the working phone uses
(vendor of firmware G975FXXSGHWC1, Android 12) have these checksums; others may work, these
are tested:

```
62897bf2ff849e20955b3d47be3c13039a722fb87bcae934b4d09a3bcf64e6e4  calliope_sram.bin
10e19314d1b765ce8b0da1673985196040e2bcf1f98f44ddcb2b5d3e1224224b  calliope_sram_2.bin
b3afb1a41154630f25284e2358af0b28936e6e8cc508d4552cfd56bf99bc57e8  calliope_dram.bin
c0ca54cdef0ab850d7a229ac6f5b2e3e09797ca344227a72d91b3a7d036c0904  calliope_dram_2.bin
```

### Step 3: build

All at once (packages, then the image, then the Odin files):

```bash
ABOX_FIRMWARE=$HOME/abox-fw ./build-all.sh
```

or one part at a time, in this order, each one adding its packages to `~/s10plus-build/localrepo`:

```bash
ABOX_FIRMWARE=$HOME/abox-fw ./kernel/build.sh
./archive-rebuild/build.sh
./plasma-mobile-wf/build.sh
./camera/build.sh
./adaptation/build.sh
docker run --rm -v "$PWD":/d:ro -v ~/s10plus-build/localrepo:/out quay.io/droidian/build-essential:next-amd64 sh /d/libbatman-wrappers/build.sh /out
./image/build.sh
./image/pack-odin.sh
```

The kernel is cross-built (15 to 40 minutes). Everything else is built for arm64 under
emulation, which is slow: count on a few hours for the whole run on a PC. The working
directory can be changed with `WORK=/some/dir`.

The result is in `~/s10plus-build/odin`: `droidian-boot-s10plus.tar.md5` and
`droidian-userdata.tar.md5`, the same two files as on the Releases page (there the userdata
one is xz-compressed). Flash them with Odin exactly as the [main README](../README.md#install-with-odin-windows)
describes.

After the first boot the phone answers SSH as `droidian` (password `1234`) both over Wi-Fi and
over the USB cable (`ssh droidian@169.254.172.1`; a link-local address, so the PC needs no DHCP,
and Windows loads its RNDIS driver by itself). The same cable also gives file access: Windows
shows the phone as a portable device (MTP) with the home folder. The stock plamo-wf image carries neither SSH nor a
working USB network; the adaptation adds both, and the SSH host keys are made anew on the first
boot, so phones flashed from the same image do not share them. The first boot also grows the
root file system to the whole userdata partition, so it takes longer.

This route was tested end to end on 12.10.2026: an image built only from this directory,
flashed with Odin, booted to a working phone.

### How the image keeps the port packages

The image patch adds the local repository (`/opt/localrepo` on the phone) before the first
package is installed and pins it to priority 1100 (Droidian pins its own archive to 1002,
so anything lower loses to the archive copy). Every package the port rebuilds wins over
the archive copy, both while the image is built and later on the phone: a Droidian update does
not replace the patched shell or kernel. To update a port package, rebuild it and install it
(or rebuild the image).

The archive is snapshot 102 plus the rolling production repository (`env.sh`). The production
repository moves; if a later Qt breaks a build, the scripts stop with the apt error, and the
fix is the same as for `qt6-text-input-v3`: rebuild the package that pins the old Qt.

### When something fails

| Symptom | Cause | Fix |
|---|---|---|
| `exec format error` in a container | arm64 emulation not registered (lost after a WSL restart) | step 1, `tonistiigi/binfmt --install arm64` again |
| `the series did not apply` | the checkout is not at the pinned commit, or a patch file was changed (line endings) | rerun the script (it fetches the pinned commit fresh); on Windows keep the repo inside WSL |
| a package build starts running programs (`plasma_session`, ...) | the sources sit on the Windows drive, every file is executable, and debhelper runs an executable `.install` file | clone inside WSL; the adaptation script also resets the modes |
| debos stops on `qt6-base-private-abi (= X) ... none of the choices are installable` | the archive moved to a newer Qt, and some archive package was not rebuilt for it | `archive-rebuild/find-stale.py` lists all such packages; add the one named in the apt error to `COMMIT` in `archive-rebuild/build.sh`, rebuild it, then run `image/build.sh` again (packages the image does not install, like `qt6-qpa-hwcomposer-plugin`, can stay stale) |
| `cannot remove ... belong to root` | a build was interrupted (or the WSL VM went down) before the container handed its files back | run the `sudo rm -rf` the message prints, then the script again |
| Odin rejects the tar | the md5 line does not carry the `.tar.md5` file name | use `pack-odin.sh`, do not rename the files afterwards |

### Where the rest of the work is

- [`../tools/phone`](../tools/phone): every piece of the port with its notes, measurements and
  test scripts. Some folders belong to the mainline (postmarketOS) path, not to Droidian:
  `decon9820`, `hub-modul`, `abox9820`, `tzdev`, `bez-usypiania`, `ucm`, `ochrona-glosnikow`.
- [`../tools/phone/obraz-boot`](../tools/phone/obraz-boot): the history of the Droidian boot
  images, release by release; the current state of those kernel changes is `kernel/patches`.
- [`../patches`](../patches) and [`../patches-uboot`](../patches-uboot): the mainline kernel
  and U-Boot series of the pmOS path.
