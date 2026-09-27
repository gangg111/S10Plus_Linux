import QtQuick

Item {
    id: popup
    visible: false
    z: 100

    property var chars: []
    signal picked(string ch)

    function openAt(item, list) {
        chars = list
        const p = item.mapToItem(popup.parent, 0, 0)
        const w = list.length * Theme.rowHeight
        // trzymamy popup w granicach ekranu, inaczej skrajne kolumny uciekaja
        frame.x = Math.max(Theme.gap,
                   Math.min(popup.width - w - Theme.gap,
                            p.x + item.width / 2 - w / 2))
        frame.y = Math.max(Theme.gap, p.y - Theme.rowHeight - Theme.gap)
        frame.width = w
        visible = true
    }

    function close() { visible = false }

    // Tapniecie poza popupem zamyka go bez wstawiania znaku.
    TapHandler {
        onTapped: popup.close()
    }

    Rectangle {
        id: frame
        height: Theme.rowHeight
        radius: Theme.radius
        color: Theme.keyBgActive
        border.color: Theme.accent
        border.width: 1

        Row {
            anchors.fill: parent
            Repeater {
                model: popup.chars
                delegate: Item {
                    required property string modelData
                    width: Theme.rowHeight
                    height: frame.height
                    Text {
                        anchors.centerIn: parent
                        text: parent.modelData
                        color: Theme.text
                        font.pixelSize: Theme.fontMain
                        renderType: Text.NativeRendering
                    }
                    TapHandler {
                        onTapped: {
                            popup.picked(parent.modelData)
                            popup.close()
                        }
                    }
                }
            }
        }
    }
}
