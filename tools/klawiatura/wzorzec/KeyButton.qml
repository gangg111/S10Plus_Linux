import QtQuick

Item {
    id: key

    required property var spec          // obiekt z Layouts
    property bool shifted: false
    property bool special: spec.act !== undefined || spec.k !== undefined
    readonly property bool spacer: spec.sp !== undefined

    signal activated(var spec)          // tap
    signal altRequested(var spec, var item)  // dlugie przytrzymanie

    readonly property bool hasAlt: spec.alt !== undefined && spec.alt.length > 0
    readonly property string glyph: {
        if (spec.label !== undefined) return spec.label
        if (spec.t === undefined) return ""
        return shifted ? spec.t.toUpperCase() : spec.t
    }

    Rectangle {
        visible: !key.spacer
        anchors.fill: parent
        anchors.margins: Theme.gap / 2
        radius: Theme.radius
        color: tap.pressed ? Theme.keyBgDown
                           : (key.special ? Theme.keyBgAlt : Theme.keyBg)

        Behavior on color { ColorAnimation { duration: 60 } }

        Text {
            anchors.centerIn: parent
            text: key.glyph
            color: Theme.text
            font.pixelSize: key.special ? Theme.fontLabel : Theme.fontMain
            font.family: "Sans"
            renderType: Text.NativeRendering
        }

        // Kropka sygnalizujaca, ze pod klawiszem sa warianty (ą, ó, ...).
        Rectangle {
            visible: key.hasAlt
            width: Math.max(2, Theme.mm(0.35))
            height: width
            radius: width / 2
            color: Theme.textDim
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.margins: Theme.mm(0.9)
        }
    }

    // TapHandler obsluguje kazdy punkt dotyku osobno, wiec dwa kciuki
    // naraz daja dwa znaki (MouseArea by tu zgubil drugi palec).
    TapHandler {
        id: tap
        enabled: !key.spacer
        gesturePolicy: TapHandler.ReleaseWithinBounds
        longPressThreshold: 0.35

        onTapped: if (!repeatTimer.fired) key.activated(key.spec)
        onLongPressed: {
            if (key.hasAlt) {
                repeatTimer.fired = true
                key.altRequested(key.spec, key)
            }
        }
        onPressedChanged: {
            if (pressed) {
                repeatTimer.fired = false
                if (key.spec.rep === true) repeatDelay.restart()
            } else {
                repeatDelay.stop()
                repeatTimer.stop()
            }
        }
    }

    // Autorepeat: 400 ms zwloki, potem 55 ms na znak — kalka z konsoli.
    Timer {
        id: repeatDelay
        interval: 400
        onTriggered: repeatTimer.start()
    }
    Timer {
        id: repeatTimer
        property bool fired: false
        interval: 55
        repeat: true
        onTriggered: {
            fired = true
            key.activated(key.spec)
        }
    }
}
