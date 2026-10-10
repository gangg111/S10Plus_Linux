// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// JD2 settings that matter on a phone, read from and written to JD2 itself
// (GeneralSettings through /config), plus starting JD2 with the session.

import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import "oneui.js" as OneUi

Flickable {
    id: page

    readonly property string iface: "org.jdownloader.settings.GeneralSettings"
    property string version: ""
    property bool loaded: false

    signal folderChanged(string folder)

    contentHeight: column.implicitHeight + 24
    clip: true
    boundsBehavior: Flickable.StopAtBounds

    function get(key, apply) {
        jd.call("/config/get", [iface, null, key], function (ok, v) {
            if (ok)
                apply(v)
        })
    }

    function set(key, value) {
        jd.call("/config/set", [iface, null, key, value], function () {})
    }

    function load() {
        get("DefaultDownloadFolder", function (v) { folder.text = v; page.folderChanged(v) })
        get("MaxSimultaneDownloads", function (v) { simultaneous.value = v })
        get("MaxChunksPerFile", function (v) { chunks.value = v })
        get("DownloadSpeedLimitEnabled", function (v) { limitOn.checked = v })
        get("DownloadSpeedLimit", function (v) { limit.value = Math.round(v / 1000) })
        jd.call("/jd/getCoreRevision", [], function (ok, v) { if (ok) page.version = "" + v })
        jd.call("/system/getSystemInfos", [], function (ok, v) { if (ok) page.system = v })
        autostart.checked = jd.autostart()
        loaded = true
    }

    property var system: ({})
    property string freeSpace: ""

    // free space in the download folder, also when the folder changes
    function updateFree() {
        if (folder.text.length === 0)
            return
        jd.call("/system/getStorageInfos", [folder.text], function (ok, v) {
            if (ok && v && v.length > 0 && !v[0].error)
                page.freeSpace = "wolne " + OneUi.size(v[0].free) + " z " + OneUi.size(v[0].size)
        })
    }

    readonly property var win: QQC2.ApplicationWindow.window

    Column {
        id: column
        width: page.width
        spacing: 16

        Card {
            OptionRow {
                text: "Folder pobierania"

                QQC2.TextField {
                    id: folder
                    width: 230
                    color: OneUi.text
                    font.pixelSize: OneUi.fontSize - 2
                    // the start of the path stays in view
                    onTextChanged: {
                        if (!activeFocus)
                            cursorPosition = 0
                        page.updateFree()
                    }
                    background: null
                    onEditingFinished: if (page.loaded && text.length > 0) {
                        page.set("DefaultDownloadFolder", text)
                        page.folderChanged(text)
                    }
                }
            }

            Rectangle { width: parent.width; height: 1; color: OneUi.separator }

            OptionRow {
                text: "Miejsce na dysku"

                QQC2.Label {
                    text: page.freeSpace
                    color: OneUi.subtitle
                    font.pixelSize: OneUi.fontSize - 2
                }
            }

            Rectangle { width: parent.width; height: 1; color: OneUi.separator }

            OptionRow {
                text: "Jednoczesne pobrania"

                QQC2.SpinBox {
                    id: simultaneous
                    from: 1
                    to: 10
                    onValueModified: page.set("MaxSimultaneDownloads", value)
                }
            }

            Rectangle { width: parent.width; height: 1; color: OneUi.separator }

            // JD2 splits one file into this many parallel connections (1..20)
            OptionRow {
                text: "Części na plik"

                QQC2.SpinBox {
                    id: chunks
                    from: 1
                    to: 20
                    onValueModified: page.set("MaxChunksPerFile", value)
                }
            }
        }

        Card {
            OptionRow {
                text: "Limit prędkości"

                QQC2.Switch {
                    id: limitOn
                    onToggled: page.set("DownloadSpeedLimitEnabled", checked)
                }
            }

            Rectangle { width: parent.width; height: 1; color: OneUi.separator; visible: limitOn.checked }

            OptionRow {
                visible: limitOn.checked
                text: "kB/s"

                QQC2.SpinBox {
                    id: limit
                    from: 10
                    to: 100000
                    stepSize: 100
                    editable: true
                    onValueModified: page.set("DownloadSpeedLimit", value * 1000)
                }
            }
        }

        Card {
            OptionRow {
                text: "Uruchamiaj przy starcie telefonu"

                QQC2.Switch {
                    id: autostart
                    onToggled: jd.setAutostart(checked)
                }
            }

            Rectangle { width: parent.width; height: 1; color: OneUi.separator }

            OptionRow {
                text: "JDownloader"

                Row {
                    spacing: 8

                    PillButton {
                        text: "Restart"
                        iconName: "view-refresh"
                        onClicked: {
                            // "starting" rather than "switched off" until it answers again
                            win.userStopped = false
                            win.everOnline = false
                            win.failures = 0
                            jd.restartBackend()
                        }
                    }

                    PillButton {
                        text: "Wyłącz"
                        iconName: "system-shutdown"
                        accent: OneUi.red
                        onClicked: {
                            win.userStopped = true
                            jd.stopBackend()
                        }
                    }
                }
            }
        }

        // every JD2 setting, plugins included
        Card {
            QQC2.ItemDelegate {
                width: parent.width
                height: 52
                padding: 0
                background: null
                onClicked: page.win.openAdvanced("", "Wszystkie ustawienia")

                contentItem: Item {
                    QQC2.Label {
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Wszystkie ustawienia"
                        color: OneUi.text
                        font.pixelSize: OneUi.fontSize
                    }

                    Kirigami.Icon {
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        width: 22
                        height: 22
                        isMask: true
                        color: OneUi.subtitle
                        source: "go-next"
                    }
                }
            }

            Rectangle { width: parent.width; height: 1; color: OneUi.separator }

            OptionRow {
                text: "Java"

                QQC2.Label {
                    text: page.system.javaVersionString ? page.system.javaVersionString.split("+")[0]
                          + "  ·  " + OneUi.size(page.system.heapUsed) + " z " + OneUi.size(page.system.heapMax) : ""
                    color: OneUi.subtitle
                    font.pixelSize: OneUi.fontSize - 2
                }
            }
        }


        // plugins and JD2 itself come from the JDownloader update server
        Card {
            OptionRow {
                text: "Wtyczki i program"

                QQC2.Label {
                    text: page.updateState === "checking" ? "sprawdzanie"
                          : page.updateState === "available" ? "jest aktualizacja"
                          : page.updateState === "installing" ? page.stageText
                          : page.updateState === "none" ? "aktualne"
                          : page.updateState === "done" ? page.doneText
                          : (page.version.length > 0 ? "rewizja " + page.version : "")
                    color: page.updateState === "available" || page.updateState === "done" ? OneUi.blue : OneUi.subtitle
                    font.pixelSize: OneUi.fontSize - 2
                }
            }

            // the check has no known length; the install moves on observed steps
            ProgressLine {
                width: parent.width
                visible: page.updateState === "checking" || page.updateState === "installing"
                indeterminate: page.updateState === "checking"
                value: page.installStage / 4
            }

            Row {
                spacing: 10

                PillButton {
                    text: "Sprawdź aktualizacje"
                    iconName: "view-refresh"
                    enabled: page.updateState !== "checking" && page.updateState !== "installing"
                    onClicked: page.checkUpdates()
                }

                PillButton {
                    visible: page.updateState === "available"
                    text: "Zainstaluj"
                    iconName: "system-software-update"
                    filled: true
                    onClicked: page.install()
                }
            }
        }
    }

    // "", checking, available, none, installing, done
    property string updateState: ""
    readonly property bool installing: updateState === "installing"

    // install steps, each one moved to only when it is seen happening:
    // 1 JD2 closing (old process still there), 2 installing (new process, API not
    // listening yet), 3 starting (API up, JD2 not ready), 4 done (API answers)
    property int installStage: 0
    property int installPid: 0
    property string revisionBefore: ""
    property string doneText: ""
    readonly property var stageNames: ["", "Zamykanie JDownloadera", "Instalowanie aktualizacji",
                                       "Uruchamianie JDownloadera", "Gotowe"]
    readonly property string stageText: stageNames[installStage] + "  ·  " + installStage + " z 4"

    function checkUpdates() {
        updateState = "checking"
        jd.call("/update/runUpdateCheck", [], function () { updatePoll.restart() })
    }

    function install() {
        revisionBefore = version
        installPid = jd.backendPid()
        installStage = 1
        updateState = "installing"
        // JD2 exits to install; systemd starts it again (Restart=always)
        jd.call("/update/restartAndUpdate", [], function () {})
        installWatch.start()
    }

    // called by Main when JD2 answers again; the install watch finishes on its own
    function backOnline() {}

    Timer {
        id: installWatch
        interval: 500
        repeat: true
        onTriggered: jd.call("/jd/getCoreRevision", [], function (ok, rev, code) {
            var restarted = jd.backendPid() !== page.installPid
            if (ok && restarted) {
                // step 4 stays on screen for a moment, then the card says what was installed
                page.installStage = 4
                page.version = "" + rev
                page.doneText = "zaktualizowano  ·  rewizja " + (page.revisionBefore === page.version
                                ? page.version : page.revisionBefore + " → " + page.version)
                installWatch.stop()
                page.updated()
                installDone.start()
            } else if (!ok && restarted) {
                // 503 from the proxy: nothing listens on 3128 yet; any other answer comes from JD2 itself
                page.installStage = Math.max(page.installStage, code === 503 || code === 0 ? 2 : 3)
            }
        })
    }

    signal updated()

    Timer {
        id: installDone
        interval: 1500
        onTriggered: page.updateState = "done"
    }

    // the update check runs in JD2's background
    Timer {
        id: updatePoll
        property int tries: 0
        interval: 1500
        repeat: true
        triggeredOnStart: true
        onRunningChanged: if (running) tries = 0
        onTriggered: jd.call("/update/isUpdateAvailable", [], function (ok, yes) {
            if (ok && (yes || jd.testUpdate)) {
                page.updateState = "available"
                updatePoll.stop()
            } else if (++updatePoll.tries >= 4) {
                page.updateState = ok ? "none" : ""
                updatePoll.stop()
            }
        })
    }
}
