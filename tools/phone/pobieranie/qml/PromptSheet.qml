// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// One UI bottom sheet asking for one value: ask(title, value, done) for text,
// choose(title, options, current, done) with options [[value, label], ...].

import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import "oneui.js" as OneUi

QQC2.Drawer {
    id: root

    property string title: ""
    property var options: []      // empty: a text field
    property var current: null
    property bool secret: false
    property var done: null

    function ask(t, value, cb, hidden) {
        title = t
        options = []
        secret = !!hidden
        field.text = value === undefined || value === null ? "" : "" + value
        done = cb
        open()
    }

    // focus only once the sheet is up: the drawer takes it while opening
    onOpened: if (options.length === 0) {
        field.forceActiveFocus()
        field.selectAll()
    }

    function choose(t, opts, cur, cb) {
        title = t
        options = opts
        current = cur
        done = cb
        open()
    }

    // above the settings page and other overlays
    z: 41
    edge: Qt.BottomEdge
    width: parent ? parent.width : 480
    height: Math.min(content.implicitHeight + 24, (parent ? parent.height : 900) * 0.85)
    modal: true
    dim: true

    background: Rectangle {
        color: OneUi.card
        topLeftRadius: OneUi.radius
        topRightRadius: OneUi.radius
    }

    Flickable {
        anchors.fill: parent
        contentHeight: content.implicitHeight + 24
        clip: true
        boundsBehavior: Flickable.StopAtBounds

        Column {
            id: content
            width: parent.width
            topPadding: 12
            spacing: 6

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 36
                height: 4
                radius: 2
                color: OneUi.separator
            }

            QQC2.Label {
                width: parent.width
                topPadding: 10
                leftPadding: 28
                rightPadding: 28
                text: root.title
                color: OneUi.text
                font.pixelSize: OneUi.fontSize + 1
                font.weight: Font.DemiBold
                wrapMode: Text.Wrap
            }

            // text value
            Item {
                visible: root.options.length === 0
                width: parent.width
                height: visible ? 140 : 0

                Rectangle {
                    x: 20
                    y: 10
                    width: parent.width - 40
                    height: 52
                    radius: 26
                    color: OneUi.pill

                    QQC2.TextField {
                        id: field
                        anchors.fill: parent
                        anchors.leftMargin: 20
                        anchors.rightMargin: 20
                        color: OneUi.text
                        background: null
                        echoMode: root.secret ? TextInput.Password : TextInput.Normal
                        inputMethodHints: Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase
                        onAccepted: ok.clicked()
                    }
                }

                Row {
                    x: 20
                    y: 78
                    spacing: 10

                    PillButton {
                        id: ok
                        text: "Zapisz"
                        iconName: "dialog-ok-apply"
                        filled: true
                        onClicked: {
                            var cb = root.done
                            root.close()
                            if (cb)
                                cb(field.text)
                        }
                    }

                    PillButton {
                        text: "Anuluj"
                        accent: OneUi.subtitle
                        onClicked: root.close()
                    }
                }
            }

            // one of a list
            Repeater {
                model: root.options

                delegate: QQC2.ItemDelegate {
                    id: opt
                    required property var modelData
                    width: content.width
                    height: 52
                    onClicked: {
                        var cb = root.done
                        root.close()
                        if (cb)
                            cb(modelData[0])
                    }

                    background: Rectangle {
                        color: opt.down ? OneUi.cardPressed : "transparent"
                    }

                    contentItem: Item {
                        QQC2.Label {
                            x: 28
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width - 90
                            text: opt.modelData[1]
                            color: OneUi.text
                            font.pixelSize: OneUi.fontSize
                            elide: Text.ElideRight
                        }

                        Kirigami.Icon {
                            visible: opt.modelData[0] === root.current
                            anchors.right: parent.right
                            anchors.rightMargin: 28
                            anchors.verticalCenter: parent.verticalCenter
                            width: 22
                            height: 22
                            isMask: true
                            color: OneUi.blue
                            source: "dialog-ok-apply"
                        }
                    }
                }
            }
        }
    }
}
