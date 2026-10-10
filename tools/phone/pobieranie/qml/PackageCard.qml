// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// One download package as a One UI card: name, status, progress bar, sizes,
// speed and time left. Tap shows the files of the package, press and hold
// opens the actions.

import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import "oneui.js" as OneUi

Item {
    id: root

    property var pkg: ({})
    property var links: []
    property bool expanded: false

    signal toggled()
    signal menuRequested(real x, real y)
    // press and hold on one file of the package
    signal linkMenuRequested(var link, Item item, real x, real y)

    readonly property bool finished: !!pkg.finished
    readonly property bool paused: !pkg.enabled
    readonly property real fraction: OneUi.progress(pkg.bytesLoaded || 0, pkg.bytesTotal || 0)
    readonly property color barColour: finished ? OneUi.green : (paused ? OneUi.subtitle : OneUi.blue)

    width: parent ? parent.width : 300
    implicitHeight: panel.height

    Rectangle {
        id: panel
        width: root.width - 2 * OneUi.cardMargin
        height: body.implicitHeight + 36
        anchors.horizontalCenter: parent.horizontalCenter
        radius: OneUi.radius
        color: area.pressed ? OneUi.cardPressed : OneUi.card

        MouseArea {
            id: area
            anchors.fill: parent
            onClicked: root.toggled()
            onPressAndHold: mouse => root.menuRequested(mouse.x, mouse.y)
        }

        Column {
            id: body
            x: 20
            y: 18
            width: panel.width - 40
            spacing: 8

            Row {
                width: parent.width
                spacing: 12

                Rectangle {
                    width: 32
                    height: 32
                    radius: 16
                    anchors.verticalCenter: parent.verticalCenter
                    color: root.barColour

                    Kirigami.Icon {
                        anchors.centerIn: parent
                        width: 22
                        height: 22
                        isMask: true
                        color: "white"
                        source: root.finished ? "dialog-ok-apply" : (root.paused ? "media-playback-pause" : "download")
                    }
                }

                Column {
                    width: parent.width - 44
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 2

                    QQC2.Label {
                        width: parent.width
                        text: root.pkg.name || ""
                        color: OneUi.text
                        font.pixelSize: OneUi.fontSize
                        font.weight: Font.DemiBold
                        elide: Text.ElideMiddle
                    }

                    QQC2.Label {
                        width: parent.width
                        text: root.paused ? "Wyłączone" : (root.pkg.status || (root.pkg.running ? "Pobieranie" : "W kolejce"))
                        color: OneUi.subtitle
                        font.pixelSize: OneUi.fontSize - 3
                        elide: Text.ElideRight
                    }
                }
            }

            // progress bar
            Rectangle {
                width: parent.width
                height: 6
                radius: 3
                color: OneUi.track

                Rectangle {
                    width: parent.width * root.fraction
                    height: parent.height
                    radius: 3
                    color: root.barColour
                    Behavior on width { NumberAnimation { duration: 400 } }
                }
            }

            Item {
                width: parent.width
                height: sizes.implicitHeight

                QQC2.Label {
                    id: sizes
                    text: root.finished ? OneUi.size(root.pkg.bytesTotal)
                                        : OneUi.size(root.pkg.bytesLoaded || 0) + " z " + OneUi.size(root.pkg.bytesTotal)
                    color: OneUi.subtitle
                    font.pixelSize: OneUi.fontSize - 3
                }

                QQC2.Label {
                    anchors.right: parent.right
                    visible: !root.finished && (root.pkg.speed || 0) > 0
                    text: OneUi.speed(root.pkg.speed || 0) + (root.pkg.eta > 0 ? "  ·  " + OneUi.eta(root.pkg.eta) : "")
                    color: OneUi.text
                    font.pixelSize: OneUi.fontSize - 3
                }
            }

            // files of the package
            Column {
                width: parent.width
                visible: root.expanded
                spacing: 0

                Repeater {
                    model: root.expanded ? root.links : []

                    delegate: Item {
                        id: linkRow
                        required property var modelData
                        width: parent.width
                        height: 58

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: OneUi.separator
                        }

                        MouseArea {
                            anchors.fill: parent
                            onClicked: root.toggled()
                            onPressAndHold: mouse => root.linkMenuRequested(linkRow.modelData, linkRow, mouse.x, mouse.y)
                        }

                        Column {
                            anchors.verticalCenter: parent.verticalCenter
                            width: parent.width
                            spacing: 3
                            // a disabled file is skipped by the queue
                            opacity: !linkRow.modelData.enabled ? 0.45 : 1

                            QQC2.Label {
                                width: parent.width
                                text: modelData.name || ""
                                color: OneUi.text
                                font.pixelSize: OneUi.fontSize - 2
                                elide: Text.ElideMiddle
                            }

                            QQC2.Label {
                                width: parent.width
                                text: (modelData.finished ? OneUi.size(modelData.bytesTotal)
                                                          : OneUi.size(modelData.bytesLoaded || 0) + " z " + OneUi.size(modelData.bytesTotal))
                                      + "  ·  " + (!modelData.enabled ? "wyłączony" : (modelData.status || modelData.host || ""))
                                color: OneUi.subtitle
                                font.pixelSize: OneUi.fontSize - 4
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }
        }
    }
}
