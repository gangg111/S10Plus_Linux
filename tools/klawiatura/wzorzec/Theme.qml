pragma Singleton
import QtQuick

QtObject {
    id: theme

    // Ustawiane z Main.qml na podstawie Screen.pixelDensity.
    // 20.5 px/mm to ~522 dpi panelu Galaxy S10+ (1440x3040, 6.4").
    property real dpmm: 20.5

    // Wysokosc rzedu w milimetrach. 9 mm to gorna granica komfortu kciuka,
    // ponizej 7 mm rosnie liczba pomylek przy pisaniu w ruchu.
    property real rowHeightMm: 9.0
    property real gapMm: 0.6
    property real radiusMm: 1.2

    // Zakrzywione krawedzie panelu.  Tlo klawiatury ma tam siegac, zeby nie
    // bylo czarnego paska przy krawedzi, ale nic czytelnego ani klikalnego
    // nie moze tam stac: piksele sa zniekszalcone i palec trafia w nie bokiem.
    //
    // 1.6 mm to 32 piksele przy 20.5 px/mm, czyli dokladnie tyle, o ile
    // odsuwa sie tekstowa konsola jadra na tym panelu (wezel simple-framebuffer
    // w drzewie urzadzen zaczyna sie o 32 piksele dalej i jest o 64 wezszy).
    property real safeMarginMm: 1.6

    readonly property real rowHeight: rowHeightMm * dpmm
    readonly property real gap: Math.max(2, gapMm * dpmm)
    readonly property real radius: radiusMm * dpmm
    readonly property real safeMargin: safeMarginMm * dpmm

    function mm(v) { return v * theme.dpmm }

    // Paleta pod AMOLED: czyste zero na tle oszczedza prad i nie swieci w nocy.
    readonly property color bg: "#000000"
    readonly property color keyBg: "#1c1c1e"
    readonly property color keyBgAlt: "#131315"
    readonly property color keyBgDown: "#0a84ff"
    readonly property color keyBgActive: "#2c2c2e"
    readonly property color text: "#f2f2f7"
    readonly property color textDim: "#8e8e93"
    readonly property color accent: "#0a84ff"
    readonly property color danger: "#ff453a"

    readonly property real fontMain: rowHeight * 0.40
    readonly property real fontLabel: rowHeight * 0.26
    readonly property real fontHint: rowHeight * 0.18
}
