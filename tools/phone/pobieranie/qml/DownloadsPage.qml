// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// The download list: links still being checked (JD2's link grabber) on top,
// then one card per package; start, pause and stop for the whole queue at
// the bottom. Press and hold a package or one of its files for its actions.

import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import "oneui.js" as OneUi

Item {
    id: page

    property var packages: []
    property var grabber: []
    property bool collecting: false
    property string queueState: "IDLE"
    property var linksByPackage: ({})
    property var expandedUuid: null

    // package or file JD2 stops after (downloadsV2/getStopMark), -1 none
    property var stopMark: -1
    // toolbar/getStatus: premium, reconnect, stopafter, ...
    property var toolbar: ({})

    signal addRequested()
    signal grabberRequested()
    signal changed()

    readonly property var win: QQC2.ApplicationWindow.window

    function refresh() {
        page.changed()
        reloadLinks()
    }

    // the whole queue: cleanup and JD2's toolbar switches
    function moreActions() {
        var ns = "/downloadsV2/"
        var done = function () { page.refresh() }
        var tb = page.toolbar
        var clean = function (action, label) {
            return { text: label, icon: "edit-clear-list",
                     run: function () { jd.call(ns + "cleanup", [[], [], action, "REMOVE_LINKS_ONLY", "ALL"], done) } }
        }
        win.sheet.show("Cała lista", [
            { text: "Sprawdź dostępność wszystkich", icon: "view-refresh", enabled: page.packages.length > 0, run: function () {
                jd.call(ns + "startOnlineStatusCheck", [[], page.packages.map(function (p) { return p.uuid })], done)
            } },
            { text: tb.stopafter ? "Zatrzymaj po bieżącym: tak" : "Zatrzymaj po bieżącym: nie", icon: "media-playback-stop",
              run: function () { jd.call("/toolbar/toggleStopAfterCurrentDownload", [], done) } },
            { text: tb.premium ? "Konta premium: używane" : "Konta premium: wyłączone", icon: "user-identity",
              run: function () { jd.call("/toolbar/togglePremium", [], done) } },
            { text: tb.reconnect ? "Automatyczne ponowne połączenie: tak" : "Automatyczne ponowne połączenie: nie",
              icon: "network-connect", run: function () { jd.call("/toolbar/toggleAutomaticReconnect", [], done) } },
            { text: "Połącz ponownie teraz", icon: "view-refresh", run: function () { jd.call("/reconnect/doReconnect", [], done) } },
            { text: "Usuń znacznik zatrzymania", icon: "media-playback-stop", enabled: page.stopMark !== -1,
              run: function () { jd.call(ns + "removeStopMark", [], done) } },
            clean("DELETE_FINISHED", "Usuń zakończone z listy"),
            clean("DELETE_FAILED", "Usuń nieudane z listy"),
            clean("DELETE_OFFLINE", "Usuń niedostępne z listy"),
            clean("DELETE_DISABLED", "Usuń wyłączone z listy"),
            clean("DELETE_DUPE", "Usuń duplikaty z listy")
        ])
    }

    function reloadLinks() {
        if (expandedUuid === null)
            return
        var uuid = expandedUuid
        jd.call("/downloadsV2/queryLinks", [{ packageUUIDs: [uuid], bytesLoaded: true, bytesTotal: true, enabled: true,
                                              status: true, finished: true, host: true, speed: true, priority: true,
                                              comment: true, skipped: true }],
                function (ok, data) {
                    if (!ok)
                        return
                    var m = Object.assign({}, page.linksByPackage)
                    m[uuid] = data
                    page.linksByPackage = m
                })
    }

    function act(path, params) {
        jd.call(path, params, function (ok, data) { page.changed() })
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

        header: Column {
            width: list.width
            spacing: 12
            bottomPadding: page.packages.length > 0 ? 12 : 0

            QQC2.ItemDelegate {
                visible: page.grabber.length > 0 || page.collecting
                width: list.width
                height: visible ? 64 : 0
                leftInset: OneUi.cardMargin
                rightInset: OneUi.cardMargin
                onClicked: page.grabberRequested()

                background: Rectangle {
                    radius: OneUi.radius
                    color: parent.down ? OneUi.cardPressed : OneUi.card
                }

                contentItem: Row {
                    leftPadding: OneUi.cardMargin + 20
                    spacing: 12

                    QQC2.BusyIndicator {
                        width: 28
                        height: 28
                        anchors.verticalCenter: parent.verticalCenter
                        running: page.collecting
                        visible: page.collecting
                    }

                    QQC2.Label {
                        anchors.verticalCenter: parent.verticalCenter
                        text: page.collecting && page.grabber.length === 0 ? "Sprawdzanie linków"
                              : "Linki do pobrania: " + page.grabber.reduce(function (n, p) { return n + p.childCount }, 0)
                        color: OneUi.text
                        font.pixelSize: OneUi.fontSize
                    }
                }
            }
        }

        delegate: PackageCard {
            id: card
            required property var modelData
            width: list.width
            pkg: modelData
            expanded: page.expandedUuid === modelData.uuid
            links: page.linksByPackage[modelData.uuid] || []
            onToggled: {
                page.expandedUuid = expanded ? null : modelData.uuid
                page.reloadLinks()
            }
            onMenuRequested: (x, y) => page.win.items.open({
                ns: "downloadsV2", links: [], packages: [modelData.uuid], name: modelData.name, link: false,
                enabled: !!modelData.enabled, finished: !!modelData.finished, saveTo: modelData.saveTo || "",
                priority: modelData.priority, comment: modelData.comment, stopMark: page.stopMark === modelData.uuid,
                lastPackage: page.packages.length > 0 ? page.packages[page.packages.length - 1].uuid : undefined
            }, page.refresh)
            onLinkMenuRequested: (link, item, x, y) => page.win.items.open({
                ns: "downloadsV2", links: [link.uuid], packages: [], name: link.name, link: true,
                packageOf: modelData.uuid, enabled: !!link.enabled, finished: !!link.finished,
                saveTo: modelData.saveTo || "", priority: link.priority, comment: link.comment,
                stopMark: page.stopMark === link.uuid
            }, page.refresh)
        }
    }

    // nothing to show
    Column {
        anchors.centerIn: list
        visible: page.packages.length === 0 && page.grabber.length === 0 && !page.collecting
        spacing: 18

        Kirigami.Icon {
            anchors.horizontalCenter: parent.horizontalCenter
            width: 64
            height: 64
            source: "folder-download"
            isMask: true
            color: OneUi.subtitle
        }

        QQC2.Label {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Brak pobrań"
            color: OneUi.text
            font.pixelSize: OneUi.fontSize + 3
        }

        PillButton {
            anchors.horizontalCenter: parent.horizontalCenter
            text: "Dodaj linki"
            iconName: "list-add"
            filled: true
            onClicked: page.addRequested()
        }
    }

    // the whole queue
    Row {
        id: controls
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 8
        anchors.horizontalCenter: parent.horizontalCenter
        spacing: 10
        visible: page.packages.length > 0

        PillButton {
            text: "Start"
            iconName: "media-playback-start"
            filled: page.queueState !== "RUNNING"
            enabled: page.queueState !== "RUNNING"
            onClicked: page.act("/downloadcontroller/start", [])
        }

        PillButton {
            text: page.queueState === "PAUSE" ? "Wznów" : "Pauza"
            iconName: page.queueState === "PAUSE" ? "media-playback-start" : "media-playback-pause"
            enabled: page.queueState === "RUNNING" || page.queueState === "PAUSE"
            onClicked: page.act("/downloadcontroller/pause", [page.queueState !== "PAUSE"])
        }

        PillButton {
            text: "Stop"
            iconName: "media-playback-stop"
            accent: OneUi.red
            enabled: page.queueState === "RUNNING" || page.queueState === "PAUSE"
            onClicked: page.act("/downloadcontroller/stop", [])
        }

        PillButton {
            implicitWidth: 52
            iconName: "overflow-menu"
            accent: OneUi.text
            onClicked: page.moreActions()
        }
    }
}
