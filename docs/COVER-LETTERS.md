### Listy przewodnie: cztery czesci, cztery drzewa

Seria nie idzie jako jedna calosc, bo `MAINTAINERS` kieruje jej czesci do roznych
opiekunow. Podzial i kolejnosc sa uzasadnione w README (sekcja o kolejnosci wysylki);
tutaj sa gotowe teksty do wyslania, po angielsku, zeby dalo sie je wkleic bez przerabiania.

Kazdy z nich mowi wprost trzy rzeczy, ktore recenzent i tak zapyta: co ta czesc wnosi,
od czego zalezy i **czego nie sprawdzono**. Ostatnie jest tu najwazniejsze: zaden patch
z tej serii nie byl uruchomiony na telefonie i list przewodni musi to powiedziec
pierwszy, zanim ktos zapyta.

Podzial patchy:

| czesc | drzewo | patche | ile |
| --- | --- | --- | --- |
| A | drm-misc | 0001, 0016-0019, 0026-0034 | 14 |
| B | phy + mfd | 0023-0025 | 3 |
| C | drm-exynos | 0035-0037 | 3 |
| D | soc/samsung | 0002-0015, 0020-0022, 0038-0040 | 20 |

Zaleznosci miedzy czesciami:

* C potrzebuje A: bierze `DSIM_TYPE_EXYNOS9820` z naglowka mostka i wywoluje
  `samsung_dsim_get_dsc()`.
* **B i C potrzebuja D do przejscia `dt_binding_check`**: przyklady w bindingu
  D-PHY i w bindingu DECON-a wlaczaja `dt-bindings/clock/samsung,exynos9820.h`,
  a ten naglowek powstaje dopiero w patchu 0011, czyli w czesci D. Bez niego
  `cpp` nie przepusci przykladu, wiec to blad kompilacji, nie ostrzezenie.
  Kod obu czesci kompiluje sie bez D, zaleznosc dotyczy wylacznie bramki
  schematow.
* D nie potrzebuje niczego z pozostalych czesci. Bez nich `dtbs_check` zglasza
  trzy wezly bez schematu (DECON, D-PHY, panel) i tyle.

Uwaga o `MAINTAINERS`: seria dodaje dwa wpisy. „SAMSUNG EXYNOS9820 SoC SUPPORT" wchodzi
z patchem 0014, czyli w czesci D, i obejmuje zegary, ich binding i drzewa urzadzen.
„DRM DRIVERS FOR EXYNOS9820" wchodzi z patchem 0037, czyli w czesci C, a wymienia takze
pliki panelu (czesc A) i D-PHY (czesc B). Jesli A albo B wyladuje pierwsze, przez chwile
beda w drzewie pliki bez wpisu. Trzeba to napisac w liscie czesci C albo przeniesc wpis
do tej czesci, ktora pojdzie pierwsza.

---

#### Czesc A: drm-misc (mostek samsung-dsim i panel S6E3HA9)

```
Subject: [PATCH 00/14] drm: Exynos9820 DSI host and the S6E3HA9 panel

This is the display half of Exynos9820 support, the SoC in the Samsung
Galaxy S10 family. It splits into two independent halves that both live
under drm-misc, so they are sent together: eight changes to the shared
samsung-dsim bridge plus one fix, and a driver for the S6E3HA9 DDIC that
drives the phone's 1440x3040 command mode AMOLED panel.

The bridge work is the interesting part for reviewers who do not care
about this SoC. The driver already serves eight variants; supporting a
ninth needed eight things it cannot express today, plus one bound fix:

  - the register offset tables are indexed with enum reg_idx but declared
    without a size, so each ends at its highest initialised entry and an
    index past that end reads whatever follows it in .rodata,
  - the pixel format value is neither the same width nor at the same bit
    on every version of the block, so it moves out of the switch and into
    a per variant table,
  - which clock the escape prescaler counts down from is a property of
    the block, not of the board,
  - whether the software reset also drops the lanes is decided today by
    comparing a register value against a constant, which answers by
    accident on a variant where that constant means another bit,
  - the peripheral's DSC configuration has to reach the display
    controller, which is what the new samsung_dsim_get_dsc() is for,
  - the PLL can live outside the host, in a separate D-PHY device, which
    runtime resume cannot simply power on because the rate is not known
    until the mode is,
  - whether the host comes up in pre_enable or during the first transfer
    is decided today by a range over the variant enum, which answers by
    position rather than by property: every variant added after
    DSIM_TYPE_EXYNOS5433 falls outside it whether or not that is what its
    hardware wants,
  - the resolution register counts compressed pixels when the peripheral
    compresses, and the driver wrote the width the peripheral shows,
    which is three times too many at 8.0 bpp.

Patch 1 is a fix that stands on its own and applies to every variant:
samsung_dsim_init() marks the host initialised even when the hardware
never came up, so a failure is reported as success and the next command
times out instead. It carries a Fixes: tag back to the 2014 commit that
introduced the behaviour.

The panel driver implements Samsung's AID dimming. The AOR, ELVSS and
VINT values of the 74 brightness steps are the vendor's own tables, but
the gamma payload that goes with each step is computed from the panel's
own MTP data rather than hardcoded. The MTP is read once the DDIC is
awake, in the panel enable path, because it cannot answer before it has
power; that is why the driver is split into a main file and a dimming
engine.

Dependencies: none. The DECON driver that consumes samsung_dsim_get_dsc()
goes to drm-exynos separately and is not part of this series.

Not tested on hardware. Nothing here has run on a phone: the code is
built, checked against the vendor sources register by register, and
bisectable, but the display has never been lit with it. Everything that
needs a measurement is listed in the series repository rather than
guessed at in the code, and the three places where a value is still
unverified carry a comment naming what has to be measured.
```

---

#### Czesc B: phy i mfd (D-PHY MIPI DSI)

```
Subject: [PATCH 00/3] phy: samsung: Exynos9820 MIPI DSI D-PHY

Exynos9820 moves the DSI PLL out of the DSI host and into a D-PHY block
of its own, so the host cannot program it the way earlier Exynos parts
do. This adds the driver for that block, its binding, and one compatible
in the syscon binding for the shared bias generator it sits behind.

The bias generator is described as a syscon rather than as part of the
PHY because the vendor sources treat it as a block of its own, shared
between the DSI and CSI links; the PHY node points at it instead of
mapping it.

The reset of the block is not in the block either. It is one bit of a
display unit system register, so the PHY takes a second syscon phandle
and follows the vendor order: hold the block in reset, program it,
release it, and put it back in reset on the way down.

Dependencies: the code builds on its own, but the example in the PHY
binding includes dt-bindings/clock/samsung,exynos9820.h, which the SoC
part of the same effort adds. Until that lands, dt_binding_check on this
part fails on the missing header. The DSI host change that makes use of
this PHY is in the drm-misc part.

The constant register blocks the vendor writes are copied verbatim,
including the two fields it overwrites right after them: the word clock
buffer shift count and the PLL lock counter. Both are left at a
different value by the constant block itself, so writing the block alone
is not the same as following the vendor, and the driver does both in the
vendor's order.

Not tested on hardware. The timing table the driver programs is
transcribed from the vendor sources; the resulting link rate has been
checked against that table arithmetically, not with a scope.
```

---

#### Czesc C: drm-exynos (DECON)

```
Subject: [PATCH 00/3] drm/exynos: Exynos9820 DECON

This adds the display controller of Exynos9820 to exynos-drm, together
with its binding and the DSI host variant entry.

The controller differs enough from the DECONs already supported that it
gets a driver of its own rather than a variant of exynos5433_drm_decon:
the register layout moved, the window pipeline is a separate DPP block,
and the panel is command mode only, so the frame is triggered by the
panel's tearing effect line rather than by a scanout timer.

Dependencies: this needs the drm-misc part of the same effort, which
adds DSIM_TYPE_EXYNOS9820 and exports samsung_dsim_get_dsc(). It should
go in after that lands, or on an immutable branch from drm-misc. The
example in the DECON binding also includes
dt-bindings/clock/samsung,exynos9820.h from the SoC part, so
dt_binding_check on this part alone fails on the missing header until
that part lands.

The MAINTAINERS entry this part adds also lists the D-PHY driver, which
goes to the phy tree in a part of its own. It is listed here because
drivers/phy/samsung/ has no directory glob in MAINTAINERS, only named
files, so nothing else would cover it; if the phy part lands first, that
driver is for a while in the tree without an entry. The panel driver
does not need this entry: it falls under DRM PANEL DRIVERS, which globs
both drivers/gpu/drm/panel/ and its bindings directory.

The register writes follow the vendor's own order, including the ones it
makes unconditionally and which are easy to miss because leaving them
out produces no error anywhere: the clock gating of the blocks inside
the controller, the size of the picture leaving the blender, the output
FIFO threshold, the channel order, and which interface drives which DSI
link. The input channel is brought up once per power on rather than per
frame, because its reset clears itself only when the block is done and
writes issued inside that window are not guaranteed to land.

Not tested on hardware. In particular the DPU power domain has never
been switched on with this code: whether it comes up at all is one of
the open questions listed in the series repository.
```

---

#### Czesc D: soc/samsung (zegary, piny, domena zasilania, drzewa urzadzen)

```
Subject: [PATCH 00/20] arm64: exynos: Add Exynos9820 and the Galaxy S10+

This brings up the Exynos9820 SoC far enough for a console and a
display: the clock controllers, the pin controller, the DPU power
domain, and the device trees for the SoC and for the Galaxy S10+
(SM-G975F, beyond2lte).

The clock driver covers eight CMU blocks and 533 clocks. It is generated
from the clock tables that ship with the vendor kernel rather than typed
out, so every offset, field position, gate bit and parent can be traced
to a line of vendor source, and a second run of the generator reproduces
the file byte for byte. What the tables do not describe is called out in
the commit message: which clocks are critical, which must not be gated
at boot, and which paths propagate a rate request.

The pin controller support is 64 banks across eight controllers. Without
it the device tree in this series has nothing to bind its pinctrl nodes
to, so no pin and no GPIO on the SoC would work.

The device trees describe only what this series can drive. Storage, USB,
audio, the modem and the cameras are left out rather than described and
disabled.

The board has no memory node. The DRAM map of this phone has not been
read from the hardware, and the vendor tree carries a placeholder its
boot loader overwrites, so there is nothing to transcribe. Rather than
invent one, the board file says so where the node would be. This is the
one thing that has to be filled in before the board can boot.

What the board file does carry is the memory the kernel must not hand
out: eleven reserved regions, for the secure log, the debug pages, the
secure camera, the three the modem owns, the frame buffer the boot
loader is still showing, and two regions belonging to the hypervisor.
Every one of them is transcribed from a tree that describes this board,
either the vendor's own or an independent port that boots the same
phone; none is calculated. The three that only the independent port
lists say so in a comment, because reserving a region that does not
exist costs memory, while missing one that does costs a kernel that
writes into the hypervisor and dies without a console line.

Dependencies: none at build time, but this part is best applied after
the other three. The display nodes reference a DECON, a DSI host, a
D-PHY and a panel whose bindings go to drm-exynos, drm-misc and the phy
tree. The device tree is descriptive, so it applies and builds on its
own and the display stays disabled, but until those bindings are in the
tree dtbs_check reports three nodes that match no schema, the display
controller, the D-PHY and the panel. The DSI host and the D-PHY top
block are not among them, because a generic schema claims each of those
two.

Not tested on hardware. No part of this has been run on a phone. The
clock driver in particular changes which clocks are held on compared to
the out of tree ports of this SoC, and that choice is reasoned from what
the in tree Exynos drivers do rather than from a measurement.
```

---

### List przewodni serii bootloadera (inne repozytorium)

Ta seria nie idzie do jadra, tylko do **U-Boota**, wiec jest osobna od czterech
czesci wyzej i nie ma z nimi zadnej zaleznosci w obie strony. Baza to przypiety
commit z `SOURCES.md`. Osiem patchy, jeden watek.

Subject: [PATCH 0/8] Add Exynos9820 support and the Samsung Galaxy S10+

Nothing here has been run on hardware. The phone this is for is in hand and
the series builds an image for it, but no image has been flashed yet, so
every claim below is about what the code does and where its numbers come
from, not about a device that booted. Reviewers should weigh it on that
basis, and I would rather say so first than have it asked.

This adds Exynos9820, the SoC in the Samsung Galaxy S10 family, to the
existing exynos-mobile board. The point of it is storage: these phones keep
theirs on UFS, and the primary boot loader will not load a mainline kernel
directly, so U-Boot has to bring the link up itself and hand over over EFI.

Two pieces of it are new to U-Boot rather than new to this SoC:

  - the Samsung UFS PHY, which no board here had. The Linux driver splits
    into a part the whole family shares and a per SoC calibration table, and
    that split is right, so this follows it. Two things had to change. The
    PHY uclass has no .calibrate operation, so the calibration point travels
    from the host controller into .configure instead of living in a state
    machine inside the PHY. And a wait for the hardware is an entry of the
    calibration table rather than a callback run after it, because the
    vendor's own tables put those waits in the middle of a sequence.

  - the Exynos UFS host controller, likewise. Its four calibration tables
    carry entries that hand over to the PHY, standing where the vendor's
    tables have their own block of PHY writes, which keeps the order the
    hardware sees. One place makes that necessary rather than tidy: the post
    link block is bracketed by a pair of writes to a UniPro attribute.

One patch is a fix to the board rather than SoC support. exynos-mobile looked
its block device up as "mmc" and nothing else, and turned its absence into a
failed initcall, which the core turns into hang(). A phone with UFS therefore
stopped before it reached its storage. The lookup now tries the interfaces the
board can boot from in turn. Nothing changes for a board that has an eMMC.

Every constant in the two UFS drivers comes from the vendor's calibration layer
for this SoC and names the line it came from. The tables were cross checked
against it in both directions, so that a value that is present is right and a
line of the vendor's that applies to this board is not missing; the second half
is what matters, because the third party port this was compared against had
every transcribed value correct and still dropped whole tables.

Three things are marked UNVERIFIED in the code and cannot be settled without
the hardware: the order in which the storage device is reset relative to
programming the host, which the core and the vendor do the other way round
from each other; the model_info properties the neighbouring board of this
family says its primary boot loader requires; and the rate of the clock the
early console counts baud from, which is why that console is a fragment to
merge by hand rather than part of the defconfig.

The device trees are copies of what the kernel side of this port carries,
because that is what dts/upstream holds for every other board here, and they
will be replaced by the real thing when that lands. The clock binding header
travels with them for the same reason. The UFS nodes are not in those copies:
they live in the board's own u-boot.dtsi, because the kernel has no driver for
them yet and the shared copy should stay exactly what the kernel has.

  Artur Szafraniec (8):
    pinctrl: exynos: add the Exynos9820 pin controller driver
    clk: exynos: add the PLL_0817X, PLL_0818X and PLL_1018X types
    clk: exynos: add the Exynos9820 clock driver
    phy: samsung: add the UFS PHY driver for Exynos9820
    ufs: exynos: add the host controller driver for Exynos9820
    board: samsung: exynos-mobile: stop requiring an eMMC
    dts: exynos: add the Exynos9820 and Galaxy S10+ device trees
    board: samsung: exynos-mobile: add the Samsung Galaxy S10+

