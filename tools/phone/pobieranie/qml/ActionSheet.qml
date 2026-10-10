// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// One UI bottom sheet with a list of actions; the one menu of the whole app
// (press and hold, "more" buttons). show(title, actions), every action
// { text, icon, enabled (default true), danger, run }.

import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import "oneui.js" as OneUi

QQC2.Drawer {
    id: root

    property string title: ""
    property var actions: []

    function show(t, a) {
        title = t
        actions = a.filter(function (x) { return !!x })
        open()
    }

    // above the settings page and other overlays
    z: 40
    edge: Qt.BottomEdge
    width: parent ? parent.width : 480
    height: Math.min(content.implicitHeight + 24, (parent ? parent.height : 900) * 0.85)
    modal: true
    dim: true
    interactive: true

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

            Rectangle {
                anchors.horizontalCenter: parent.horizontalCenter
                width: 36
                height: 4
                radius: 2
                color: OneUi.separator
            }

            QQC2.Label {
                width: parent.width
                visible: root.title.length > 0
                topPadding: 14
                bottomPadding: 6
                leftPadding: 28
                rightPadding: 28
                text: root.title
                color: OneUi.subtitle
                font.pixelSize: OneUi.fontSize - 2
                wrapMode: Text.Wrap
                maximumLineCount: 6
                elide: Text.ElideRight
            }

            Repeater {
                model: root.actions

                delegate: QQC2.ItemDelegate {
                    id: row
                    required property var modelData
                    width: content.width
                    height: 54
                    enabled: modelData.enabled !== false
                    opacity: enabled ? 1 : 0.4
                    onClicked: {
                        root.close()
                        modelData.run()
                    }

                    background: Rectangle {
                        color: row.down ? OneUi.cardPressed : "transparent"
                    }

                    contentItem: Row {
                        leftPadding: 28
                        spacing: 18

                        Kirigami.Icon {
                            anchors.verticalCenter: parent.verticalCenter
                            width: 22
                            height: 22
                            isMask: true
                            color: row.modelData.danger ? OneUi.red : OneUi.text
                            source: row.modelData.icon || ""
                        }

                        QQC2.Label {
                            anchors.verticalCenter: parent.verticalCenter
                            text: row.modelData.text
                            color: row.modelData.danger ? OneUi.red : OneUi.text
                            font.pixelSize: OneUi.fontSize
                        }
                    }
                }
            }
        }
    }
}
