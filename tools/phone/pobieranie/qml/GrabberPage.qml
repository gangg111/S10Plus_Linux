// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// JD2's link grabber: what was added and checked but is not in the download
// list yet. Packages with availability, files on tap, every action on press
// and hold, the whole list from the buttons at the bottom.

import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import "oneui.js" as OneUi

Item {
    id: page

    property var packages: []
    property bool collecting: false
    property var linksByPackage: ({})
    property var expandedUuid: null

    signal changed()

    readonly property var win: QQC2.ApplicationWindow.window

    function reloadLinks() {
        if (expandedUuid === null)
            return
        var uuid = expandedUuid
        jd.call("/linkgrabberv2/queryLinks", [{ packageUUIDs: [uuid], bytesTotal: true, enabled: true, host: true,
                                                availability: true, status: true, variants: true, variantName: true,
                                                priority: true, comment: true, url: true }],
                function (ok, data) {
                    if (!ok)
                        return
                    var m = Object.assign({}, page.linksByPackage)
                    m[uuid] = data
                    page.linksByPackage = m
                })
    }

    function refresh() {
        page.changed()
        reloadLinks()
    }

    function availability(p) {
        var parts = [p.childCount + (p.childCount === 1 ? " plik" : " pliki")]
        if (p.bytesTotal > 0)
            parts.push(OneUi.size(p.bytesTotal))
        if (p.onlineCount > 0)
            parts.push("dostępne " + p.onlineCount)
        if (p.offlineCount > 0)
            parts.push("niedostępne " + p.offlineCount)
        var unknown = (p.unknownCount || 0) + (p.tempUnknownCount || 0)
        if (unknown > 0)
            parts.push("nieznane " + unknown)
        return parts.join("  ·  ")
    }

    function availabilityText(a) {
        return a === "ONLINE" ? "dostępny" : a === "OFFLINE" ? "niedostępny" : a === "TEMP_UNKNOWN" ? "sprawdzanie" : "nieznany"
    }

    function allIds() {
        return packages.map(function (p) { return p.uuid })
    }

    function moreActions() {
        var ns = "/linkgrabberv2/"
        var ids = allIds()
        var done = function () { page.refresh() }
        win.sheet.show("Wszystkie linki", [
            { text: "Pobierz wszystko", icon: "download", enabled: ids.length > 0, run: function () {
                jd.call(ns + "moveToDownloadlist", [[], ids], function () { jd.call("/downloadcontroller/start", [], done) })
            } },
            { text: "Sprawdź dostępność wszystkich", icon: "view-refresh", enabled: ids.length > 0,
              run: function () { jd.call(ns + "startOnlineStatusCheck", [[], ids], done) } },
            { text: "Przerwij wyszukiwanie linków", icon: "process-stop", enabled: page.collecting,
              run: function () { jd.call(ns + "abort", [], done) } },
            { text: "Usuń niedostępne", icon: "list-remove", enabled: ids.length > 0,
              run: function () { jd.call(ns + "cleanup", [[], [], "DELETE_OFFLINE", "REMOVE_LINKS_ONLY", "ALL"], done) } },
            { text: "Usuń wyłączone", icon: "list-remove", enabled: ids.length > 0,
              run: function () { jd.call(ns + "cleanup", [[], [], "DELETE_DISABLED", "REMOVE_LINKS_ONLY", "ALL"], done) } },
            { text: "Usuń duplikaty", icon: "edit-copy", enabled: ids.length > 0,
              run: function () { jd.call(ns + "cleanup", [[], [], "DELETE_DUPE", "REMOVE_LINKS_ONLY", "ALL"], done) } },
            { text: "Wyczyść listę", icon: "edit-delete", danger: true, enabled: ids.length > 0,
              run: function () { jd.call(ns + "clearList", [], done) } }
        ])
    }

    ListView {
        id: list
        anchors.top: parent.top
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: controls.top
        anchors.bottomMargin: 8
        clip: true
        spacing: 12
        model: page.packages
        boundsBehavior: Flickable.StopAtBounds

        header: Item {
            width: list.width
            height: page.collecting ? 56 : 0
            visible: page.collecting

            Row {
                x: 28
                anchors.verticalCenter: parent.verticalCenter
                spacing: 12

                QQC2.BusyIndicator {
                    width: 28
                    height: 28
                    running: page.collecting
                }

                QQC2.Label {
                    anchors.verticalCenter: parent.verticalCenter
                    text: "Wyszukiwanie i sprawdzanie linków"
                    color: OneUi.subtitle
                    font.pixelSize: OneUi.fontSize - 2
                }
            }
        }

        delegate: Item {
            id: card
            required property var modelData
            required property int index
            readonly property bool expanded: page.expandedUuid === modelData.uuid
            readonly property var links: page.linksByPackage[modelData.uuid] || []
            width: list.width
            height: panel.height

            function packageTarget() {
                return { ns: "linkgrabberv2", links: [], packages: [modelData.uuid], name: modelData.name,
                         link: false, enabled: !!modelData.enabled, saveTo: modelData.saveTo || "",
                         priority: modelData.priority, comment: modelData.comment,
                         lastPackage: page.packages.length > 0 ? page.packages[page.packages.length - 1].uuid : undefined }
            }

            Rectangle {
                id: panel
                width: card.width - 2 * OneUi.cardMargin
                height: body.implicitHeight + 36
                anchors.horizontalCenter: parent.horizontalCenter
                radius: OneUi.radius
                color: area.pressed ? OneUi.cardPressed : OneUi.card

                MouseArea {
                    id: area
                    anchors.fill: parent
                    onClicked: {
                        page.expandedUuid = card.expanded ? null : card.modelData.uuid
                        page.reloadLinks()
                    }
                    onPressAndHold: page.win.items.open(card.packageTarget(), page.refresh)
                }

                Column {
                    id: body
                    x: 20
                    y: 18
                    width: panel.width - 40
                    spacing: 6
                    opacity: !card.modelData.enabled ? 0.45 : 1

                    QQC2.Label {
                        width: parent.width
                        text: card.modelData.name
                        color: OneUi.text
                        font.pixelSize: OneUi.fontSize
                        font.weight: Font.DemiBold
                        elide: Text.ElideMiddle
                    }

                    QQC2.Label {
                        width: parent.width
                        text: page.availability(card.modelData)
                        color: card.modelData.offlineCount > 0 ? OneUi.orange : OneUi.subtitle
                        font.pixelSize: OneUi.fontSize - 3
                        wrapMode: Text.Wrap
                    }

                    QQC2.Label {
                        width: parent.width
                        visible: !!card.modelData.saveTo
                        text: card.modelData.saveTo || ""
                        color: OneUi.subtitle
                        font.pixelSize: OneUi.fontSize - 4
                        elide: Text.ElideMiddle
                    }

                    Repeater {
                        model: card.expanded ? card.links : []

                        delegate: Item {
                            id: linkRow
                            required property var modelData
                            width: body.width
                            height: 58

                            Rectangle { width: parent.width; height: 1; color: OneUi.separator }

                            MouseArea {
                                anchors.fill: parent
                                onClicked: {
                                    page.expandedUuid = null
                                }
                                onPressAndHold: page.win.items.open({
                                    ns: "linkgrabberv2", links: [linkRow.modelData.uuid], packages: [],
                                    name: linkRow.modelData.name, link: true, packageOf: card.modelData.uuid,
                                    enabled: !!linkRow.modelData.enabled, saveTo: card.modelData.saveTo || "",
                                    priority: linkRow.modelData.priority, comment: linkRow.modelData.comment
                                }, page.refresh)
                            }

                            Column {
                                anchors.verticalCenter: parent.verticalCenter
                                width: parent.width
                                spacing: 3
                                opacity: !linkRow.modelData.enabled ? 0.45 : 1

                                QQC2.Label {
                                    width: parent.width
                                    text: linkRow.modelData.name || ""
                                    color: OneUi.text
                                    font.pixelSize: OneUi.fontSize - 2
                                    elide: Text.ElideMiddle
                                }

                                QQC2.Label {
                                    width: parent.width
                                    text: [OneUi.size(linkRow.modelData.bytesTotal), linkRow.modelData.host,
                                           page.availabilityText(linkRow.modelData.availability),
                                           linkRow.modelData.variantName || ""].filter(function (x) { return !!x }).join("  ·  ")
                                    color: linkRow.modelData.availability === "OFFLINE" ? OneUi.orange : OneUi.subtitle
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

    // nothing waiting
    Column {
        anchors.centerIn: list
        visible: page.packages.length === 0 && !page.collecting
        spacing: 18

        Kirigami.Icon {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 64
            height: 64
            source: "view-list-details"
            isMask: true
            color: OneUi.subtitle
        }

        QQC2.Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Brak linków do sprawdzenia"
            color: OneUi.text
            font.pixelSize: OneUi.fontSize + 2
        }
    }

    Row {
        id: controls
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 10
        visible: page.packages.length > 0 || page.collecting

        PillButton {
            text: "Pobierz wszystko"
            iconName: "download"
            filled: true
            enabled: page.packages.length > 0
            onClicked: jd.call("/linkgrabberv2/moveToDownloadlist", [[], page.allIds()], function () {
                jd.call("/downloadcontroller/start", [], function () { page.refresh() })
            })
        }

        PillButton {
            text: "Więcej"
            iconName: "overflow-menu"
            onClicked: page.moreActions()
        }
    }
}
