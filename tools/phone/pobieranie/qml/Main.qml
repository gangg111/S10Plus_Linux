// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Pobieranie: One UI style front end for JDownloader 2. Big title, five tabs
// at the bottom (downloads, link grabber, add, hosters, settings), one action
// sheet and one prompt for every menu, JD2's captchas and dialogs on top.
// The lists refresh every 1.5 s in front, every 10 s without focus.

import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Layouts
import org.kde.kirigami as Kirigami
import "oneui.js" as OneUi

QQC2.ApplicationWindow {
    id: win

    property bool online: false
    property bool everOnline: false
    property int failures: 0
    // switched off in Settings: do not bring it back on our own
    property bool userStopped: false
    property string queueState: "IDLE"
    property real speed: 0
    property int tab: 0
    property string defaultFolder: ""

    // shared by every page (QQC2.ApplicationWindow.window.sheet ...)
    property alias sheet: sheetItem
    property alias prompt: promptItem
    property alias items: itemActions

    visible: true
    width: 480
    height: 946
    title: "JDownloader 2"
    color: OneUi.bg

    palette.window: OneUi.bg
    palette.base: OneUi.card
    palette.text: OneUi.text
    palette.windowText: OneUi.text
    palette.buttonText: OneUi.text
    palette.button: OneUi.pill
    palette.highlight: OneUi.blue
    palette.highlightedText: "white"
    palette.placeholderText: OneUi.pillText

    readonly property var titles: ["Pobieranie", "Linki", "Dodaj linki", "Hostingi", "Ustawienia"]
    readonly property int addTab: 2

    onTabChanged: if (tab === 3 && online) hosts.reload()

    function openAdvanced(prefix, title) {
        advanced.prefix = prefix
        advanced.title = title
        advanced.query = ""
        advanced.visible = true
    }

    function toast(text) {
        toastLabel.text = text
        toastBox.opacity = 1
        toastTimer.restart()
    }

    function summary() {
        if (!online)
            return settings.installing ? "Aktualizacja JDownloadera"
                 : userStopped ? "JDownloader wyłączony"
                 : (everOnline ? "JDownloader nie odpowiada" : "Uruchamianie JDownloadera")
        if (queueState === "RUNNING")
            return "Pobieranie  ·  " + OneUi.speed(speed)
        if (queueState === "PAUSE")
            return "Wstrzymane"
        var n = downloads.packages.filter(function (p) { return !p.finished }).length
        return n > 0 ? "Zatrzymane  ·  w kolejce: " + n : "Gotowe"
    }

    function refresh() {
        jd.call("/downloadcontroller/getCurrentState", [], function (ok, d) {
            if (!ok) {
                online = false
                // JD2 needs 30-60 s to come up; ask systemd again now and then
                if (++failures % 20 === 1 && !settings.installing && !userStopped)
                    jd.startBackend()
                return
            }
            if (!online && !settings.loaded)
                settings.load()
            online = true
            everOnline = true
            failures = 0
            queueState = d
        })
        if (!online)
            return
        jd.call("/downloadcontroller/getSpeedInBps", [], function (ok, d) { if (ok) speed = d })
        jd.call("/downloadsV2/queryPackages", [{ bytesLoaded: true, bytesTotal: true, speed: true, eta: true,
                                                 finished: true, running: true, status: true, saveTo: true,
                                                 childCount: true, enabled: true, priority: true, comment: true }],
                function (ok, d) { if (ok) downloads.packages = d })
        jd.call("/linkgrabberv2/queryPackages", [{ childCount: true, bytesTotal: true, status: true, saveTo: true,
                                                   enabled: true, priority: true, comment: true,
                                                   availableOnlineCount: true, availableOfflineCount: true,
                                                   availableUnknownCount: true, availableTempUnknownCount: true }],
                function (ok, d) {
                    if (ok) {
                        downloads.grabber = d
                        grabber.packages = d
                    }
                })
        jd.call("/linkgrabberv2/isCollecting", [], function (ok, d) {
            if (ok) {
                downloads.collecting = d
                grabber.collecting = d
            }
        })
        jd.call("/downloadsV2/getStopMark", [], function (ok, d) { if (ok) downloads.stopMark = d })
        jd.call("/toolbar/getStatus", [], function (ok, d) { if (ok) downloads.toolbar = d })
        downloads.reloadLinks()
        grabber.reloadLinks()
        ask.check()
    }

    // 1.5 s in front, 10 s without focus (also with the screen off), never when hidden
    Timer {
        interval: Qt.application.state === Qt.ApplicationActive ? 1500 : 10000
        repeat: true
        running: Qt.application.state !== Qt.ApplicationHidden && Qt.application.state !== Qt.ApplicationSuspended
        triggeredOnStart: true
        onTriggered: win.refresh()
    }

    Component.onCompleted: {
        jd.startBackend()
        refresh()
        if (jd.initialLinks.length > 0) {
            add.links = jd.initialLinks.join("\n")
            tab = addTab
        }
    }

    // big One UI title
    header: Item {
        visible: !advanced.visible
        height: visible ? 132 : 0

        Column {
            anchors.left: parent.left
            anchors.leftMargin: 28
            anchors.right: parent.right
            anchors.rightMargin: 28
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 18
            spacing: 4

            QQC2.Label {
                text: win.titles[win.tab]
                color: OneUi.text
                font.pixelSize: 32
                font.weight: Font.Bold
            }

            QQC2.Label {
                visible: win.tab === 0 || !win.online
                text: win.summary()
                color: OneUi.subtitle
                font.pixelSize: OneUi.fontSize - 2
            }
        }
    }

    StackLayout {
        anchors.fill: parent
        currentIndex: win.tab

        DownloadsPage {
            id: downloads
            queueState: win.queueState
            onAddRequested: win.tab = win.addTab
            onGrabberRequested: win.tab = 1
            onChanged: win.refresh()
        }

        GrabberPage {
            id: grabber
            onChanged: win.refresh()
        }

        AddPage {
            id: add
            defaultFolder: win.defaultFolder
            onAdded: {
                win.tab = 1
                win.refresh()
            }
        }

        HostsPage {
            id: hosts
        }

        SettingsPage {
            id: settings
            onFolderChanged: folder => win.defaultFolder = folder
            // JD2 is back after the update: no "offline" frame in between
            onUpdated: win.refresh()
        }
    }

    // JD2 is not there yet
    Rectangle {
        anchors.fill: parent
        color: OneUi.bg
        visible: !win.online && win.tab !== win.addTab

        Column {
            anchors.centerIn: parent
            spacing: 18

            QQC2.BusyIndicator {
                anchors.horizontalCenter: parent.horizontalCenter
                running: parent.parent.visible && !win.everOnline && !settings.installing
                visible: running
            }

            QQC2.Label {
                anchors.horizontalCenter: parent.horizontalCenter
                text: settings.installing ? "Aktualizacja JDownloadera"
                      : win.userStopped ? "JDownloader jest wyłączony"
                      : (win.everOnline ? "JDownloader nie odpowiada" : "Uruchamianie JDownloadera")
                color: OneUi.text
                font.pixelSize: OneUi.fontSize + 2
            }

            // install steps as JD2 goes through them (SettingsPage.installStage)
            ProgressLine {
                visible: settings.installing
                width: 300
                anchors.horizontalCenter: parent.horizontalCenter
                value: settings.installStage / 4
            }

            QQC2.Label {
                visible: settings.installing
                anchors.horizontalCenter: parent.horizontalCenter
                text: settings.stageText
                color: OneUi.subtitle
                font.pixelSize: OneUi.fontSize - 2
            }

            PillButton {
                anchors.horizontalCenter: parent.horizontalCenter
                visible: !settings.installing && (win.everOnline || win.failures > 60)
                text: "Uruchom"
                iconName: "media-playback-start"
                filled: true
                onClicked: {
                    win.userStopped = false
                    win.failures = 0
                    win.everOnline = false
                    jd.startBackend()
                }
            }
        }
    }

    // every setting (Settings) or one plugin's (Hosters), over the whole window
    AdvancedPage {
        id: advanced
        parent: QQC2.Overlay.overlay
        anchors.fill: parent
        visible: false
        z: 10
        onClosed: {
            visible = false
            // the settings tab shows the same values: read them again
            settings.load()
        }
    }

    // what JD2 asks: captchas and its dialogs
    AskOverlay {
        id: ask
        parent: QQC2.Overlay.overlay
        anchors.fill: parent
        z: 20
    }

    ActionSheet {
        id: sheetItem
    }

    PromptSheet {
        id: promptItem
    }

    ItemActions {
        id: itemActions
        sheet: sheetItem
        prompt: promptItem
        copy: function (text) {
            jd.copyText(text)
            win.toast(text.length > 0 ? "Skopiowano linki: " + text.split("\n").length : "Brak linków do skopiowania")
        }
    }

    // short confirmation at the bottom
    Rectangle {
        id: toastBox
        parent: QQC2.Overlay.overlay
        z: 30
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottom: parent.bottom
        anchors.bottomMargin: 96
        width: toastLabel.implicitWidth + 40
        height: 44
        radius: 22
        color: OneUi.pill
        opacity: 0
        visible: opacity > 0
        Behavior on opacity { NumberAnimation { duration: 200 } }

        QQC2.Label {
            id: toastLabel
            anchors.centerIn: parent
            color: OneUi.text
            font.pixelSize: OneUi.fontSize - 2
        }

        Timer {
            id: toastTimer
            interval: 2200
            onTriggered: toastBox.opacity = 0
        }
    }

    // One UI bottom navigation
    footer: Rectangle {
        visible: !advanced.visible
        height: visible ? 68 : 0
        color: OneUi.bg

        Row {
            anchors.fill: parent

            Repeater {
                model: [["Pobierane", "folder-download"], ["Linki", "view-list-details"], ["Dodaj", "list-add"],
                        ["Hostingi", "network-server"], ["Ustawienia", "configure"]]

                delegate: QQC2.AbstractButton {
                    id: navButton
                    required property var modelData
                    required property int index
                    width: parent.width / 5
                    height: parent.height
                    onClicked: win.tab = index

                    contentItem: Column {
                        spacing: 4
                        topPadding: 10

                        Item {
                            anchors.horizontalCenter: parent.horizontalCenter
                            width: 24
                            height: 24

                            Kirigami.Icon {
                                anchors.fill: parent
                                source: navButton.modelData[1]
                                isMask: true
                                color: win.tab === navButton.index ? OneUi.text : OneUi.subtitle
                            }

                            // links waiting in the grabber
                            Rectangle {
                                visible: navButton.index === 1 && grabber.packages.length > 0
                                x: 16
                                y: -4
                                width: 16
                                height: 16
                                radius: 8
                                color: OneUi.orange

                                QQC2.Label {
                                    anchors.centerIn: parent
                                    text: grabber.packages.length
                                    color: "white"
                                    font.pixelSize: 10
                                }
                            }
                        }

                        QQC2.Label {
                            anchors.horizontalCenter: parent.horizontalCenter
                            text: navButton.modelData[0]
                            color: win.tab === navButton.index ? OneUi.text : OneUi.subtitle
                            font.pixelSize: 12
                            font.weight: win.tab === navButton.index ? Font.DemiBold : Font.Normal
                        }
                    }

                    background: null
                }
            }
        }
    }
}
