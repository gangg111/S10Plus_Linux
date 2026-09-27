import QtQuick
import Kbd.Backend

Item {
    id: kb

    property string layerName: "letters"
    property bool shift: false
    property bool shiftLock: false
    property bool ctrl: false
    property bool alt: false

    readonly property var rows: Layouts.layer(layerName)
    readonly property int rowCount: rows.length

    // Rzedy moga miec rozna wysokosc (pole rh), wiec sumujemy zamiast mnozyc.
    implicitHeight: {
        let h = Theme.gap
        for (let i = 0; i < rows.length; ++i)
            h += Theme.rowHeight * rowScale(rows[i])
        return h
    }

    function rowScale(row) {
        return (row.length > 0 && row[0].rh !== undefined) ? row[0].rh : 1
    }

    signal keySent(string what)

    function reset() {
        shift = false; shiftLock = false; ctrl = false; alt = false
    }

    function handle(spec) {
        if (spec.act === "shift") {
            if (shift && !shiftLock) { shiftLock = true }
            else if (shiftLock)      { shiftLock = false; shift = false }
            else                     { shift = true }
            return
        }
        if (spec.act === "layer") {
            layerName = spec.to
            shift = false; shiftLock = false
            return
        }
        if (spec.act === "mod") {
            if (spec.mod === "ctrl") ctrl = !ctrl
            else if (spec.mod === "alt") alt = !alt
            return
        }
        if (spec.k !== undefined) {
            Uinput.tapNamed(spec.k, ctrl, alt, shift, false)
            kb.keySent(spec.k)
        } else if (spec.t !== undefined) {
            const ch = (shift || shiftLock) ? spec.t.toUpperCase() : spec.t
            if (ctrl || alt)
                Uinput.tapChar(ch, ctrl, alt, false, false)
            else
                Uinput.typeText(ch)
            kb.keySent(ch)
        }
        // shift jednorazowy gasnie po znaku, lock zostaje
        if (shift && !shiftLock) shift = false
        if (ctrl || alt) { ctrl = false; alt = false }
    }

    // Tlo celowo BEZ marginesu: ma wypelnic takze zakrzywione krawedzie.
    Rectangle {
        anchors.fill: parent
        color: Theme.bg
    }

    Column {
        id: grid
        anchors.fill: parent
        anchors.topMargin: Theme.gap / 2
        anchors.leftMargin: Theme.gap / 2 + Theme.safeMargin
        anchors.rightMargin: Theme.gap / 2 + Theme.safeMargin
        spacing: 0

        Repeater {
            model: kb.rows
            delegate: Item {
                id: rowItem
                required property var modelData
                width: grid.width
                height: Theme.rowHeight * kb.rowScale(modelData)

                // Suma wag w rzedzie; klawisze skaluja sie do szerokosci ekranu,
                // wiec uklad nie rozjezdza sie przy obrocie ani przy 1440 px.
                readonly property real weightSum: {
                    let s = 0
                    for (let i = 0; i < modelData.length; ++i) {
                        const e = modelData[i]
                        s += e.sp !== undefined ? e.sp
                           : (e.w !== undefined ? e.w : 1)
                    }
                    return s
                }

                Row {
                    anchors.fill: parent
                    Repeater {
                        model: rowItem.modelData
                        delegate: KeyButton {
                            required property var modelData
                            spec: modelData
                            width: rowItem.width *
                                   ((modelData.sp !== undefined ? modelData.sp
                                     : (modelData.w !== undefined ? modelData.w : 1))
                                    / rowItem.weightSum)
                            height: rowItem.height
                            shifted: kb.shift || kb.shiftLock
                            onActivated: (s) => kb.handle(s)
                            onAltRequested: (s, item) => altPopup.openAt(item, s.alt)
                        }
                    }
                }
            }
        }
    }

    // Podswietlenie aktywnych modyfikatorow — bez tego nie widac,
    // czy Ctrl jest jeszcze wcisniety.
    Row {
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: Theme.gap
        anchors.rightMargin: Theme.gap + Theme.safeMargin
        spacing: Theme.gap
        Text {
            visible: kb.shiftLock
            text: "CAPS"; color: Theme.accent; font.pixelSize: Theme.fontHint
        }
        Text {
            visible: kb.ctrl
            text: "CTRL"; color: Theme.accent; font.pixelSize: Theme.fontHint
        }
        Text {
            visible: kb.alt
            text: "ALT"; color: Theme.accent; font.pixelSize: Theme.fontHint
        }
    }

    AltPopup {
        id: altPopup
        anchors.fill: parent
        onPicked: (ch) => {
            Uinput.typeText(ch)
            kb.keySent(ch)
        }
    }
}
