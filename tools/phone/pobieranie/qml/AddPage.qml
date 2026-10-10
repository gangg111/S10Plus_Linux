// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Adding links: paste them, optionally name the package and pick a folder,
// download at once or only check them first.

import QtQuick
import QtQuick.Controls as QQC2
import QtQuick.Dialogs
import "oneui.js" as OneUi

Flickable {
    id: page

    property alias links: area.text
    property string defaultFolder: ""

    property string priority: "DEFAULT"
    property bool more: false
    property string containerResult: ""
    property bool containerOk: false

    FileDialog {
        id: containerDialog
        title: "Plik kontenera"
        nameFilters: ["Kontenery (*.dlc *.ccf *.rsdf)", "Wszystkie pliki (*)"]
        onAccepted: {
            var url = "" + selectedFile
            var data = jd.readFileBase64(url)
            var ext = url.split(".").pop().toUpperCase()
            if (data.length === 0) {
                page.containerOk = false
                page.containerResult = "Nie udało się odczytać pliku"
                return
            }
            jd.call("/linkgrabberv2/addContainer", [ext, data], function (ok, d) {
                page.containerOk = ok
                page.containerResult = ok ? "Dodano kontener " + url.split("/").pop() : "JDownloader nie przyjął kontenera"
                if (ok)
                    page.added()
            })
        }
    }

    signal added()

    readonly property var win: QQC2.ApplicationWindow.window

    contentHeight: column.implicitHeight + 24
    clip: true
    boundsBehavior: Flickable.StopAtBounds

    function add() {
        var q = { links: area.text.trim(), autostart: autostart.checked }
        if (name.text.trim().length > 0)
            q.packageName = name.text.trim()
        if (folder.text.trim().length > 0)
            q.destinationFolder = folder.text.trim()
        if (password.text.length > 0)
            q.downloadPassword = password.text
        if (comment.text.trim().length > 0)
            q.comment = comment.text.trim()
        q.priority = page.priority
        q.deepDecrypt = deep.checked
        q.overwritePackagizerRules = overwrite.checked
        jd.call("/linkgrabberv2/addLinks", [q], function (ok, data) {
            if (!ok)
                return
            area.text = ""
            name.text = ""
            password.text = ""
            comment.text = ""
            page.added()
        })
    }

    // the keyboard shrinks the window: keep the field being typed into in view
    function showFocused() {
        var f = Window.activeFocusItem
        for (var p = f; p && p !== column; p = p.parent) {}
        if (!f || !p)
            return
        var y = f.mapToItem(column, 0, 0).y
        if (y + f.height + 16 > contentY + height)
            contentY = Math.min(y + f.height + 16 - height, Math.max(0, contentHeight - height))
        else if (y < contentY)
            contentY = Math.max(0, y - 16)
    }

    onHeightChanged: Qt.callLater(showFocused)

    // a tap beside the fields puts the keyboard away (it covers the options)
    MouseArea {
        width: page.width
        height: Math.max(page.contentHeight, page.height)
        onClicked: {
            page.forceActiveFocus()
            Qt.inputMethod.hide()
        }
    }

    Column {
        id: column
        width: page.width
        spacing: 16

        Card {
            QQC2.TextArea {
                id: area
                width: parent.width
                height: 220
                wrapMode: TextEdit.WrapAnywhere
                placeholderText: "Linki, po jednym w wierszu"
                placeholderTextColor: OneUi.pillText
                color: OneUi.text
                font.pixelSize: OneUi.fontSize - 1
                background: null
                inputMethodHints: Qt.ImhUrlCharactersOnly | Qt.ImhNoPredictiveText
            }

            Row {
                spacing: 10

                PillButton {
                    text: "Wklej"
                    iconName: "edit-paste"
                    onClicked: {
                        area.forceActiveFocus()
                        area.cursorPosition = area.length
                        if (area.length > 0 && area.text[area.length - 1] !== "\n")
                            area.insert(area.length, "\n")
                        area.paste()
                    }
                }

                PillButton {
                    text: "Wyczyść"
                    iconName: "edit-clear"
                    accent: OneUi.subtitle
                    enabled: area.length > 0
                    onClicked: area.text = ""
                }
            }
        }

        Card {
            OptionRow {
                text: "Nazwa pakietu"

                QQC2.TextField {
                    id: name
                    width: 220
                    placeholderText: "z linków"
                    placeholderTextColor: OneUi.pillText
                    font.italic: text.length === 0
                    color: OneUi.text
                    horizontalAlignment: Text.AlignRight
                    background: null
                }
            }

            Rectangle { width: parent.width; height: 1; color: OneUi.separator }

            OptionRow {
                text: "Folder"

                QQC2.TextField {
                    id: folder
                    width: 220
                    placeholderText: page.defaultFolder
                    placeholderTextColor: OneUi.pillText
                    font.italic: text.length === 0
                    color: OneUi.text
                    horizontalAlignment: Text.AlignRight
                    background: null
                }
            }

            Rectangle { width: parent.width; height: 1; color: OneUi.separator }

            OptionRow {
                text: "Pobierz od razu"

                QQC2.Switch {
                    id: autostart
                    checked: true
                }
            }
        }

        Card {
            OptionRow {
                text: "Więcej opcji"

                QQC2.Switch {
                    checked: page.more
                    onToggled: page.more = checked
                }
            }

            Column {
                width: parent.width
                visible: page.more
                spacing: 12

                Rectangle { width: parent.width; height: 1; color: OneUi.separator }

                OptionRow {
                    text: "Hasło do pobrania"

                    QQC2.TextField {
                        id: password
                        width: 200
                        echoMode: TextInput.Password
                        color: OneUi.text
                        horizontalAlignment: Text.AlignRight
                        background: null
                        inputMethodHints: Qt.ImhSensitiveData | Qt.ImhNoPredictiveText
                    }
                }

                Rectangle { width: parent.width; height: 1; color: OneUi.separator }

                OptionRow {
                    text: "Komentarz"

                    QQC2.TextField {
                        id: comment
                        width: 200
                        color: OneUi.text
                        horizontalAlignment: Text.AlignRight
                        background: null
                    }
                }

                Rectangle { width: parent.width; height: 1; color: OneUi.separator }

                OptionRow {
                    text: "Priorytet"

                    PillButton {
                        text: page.win ? page.win.items.priorities.filter(function (p) { return p[0] === page.priority })[0][1] : ""
                        accent: OneUi.blue
                        onClicked: page.win.prompt.choose("Priorytet", page.win.items.priorities, page.priority,
                                                          function (v) { page.priority = v })
                    }
                }

                Rectangle { width: parent.width; height: 1; color: OneUi.separator }

                OptionRow {
                    text: "Szukaj głębiej (linki w linkach)"

                    QQC2.Switch { id: deep }
                }

                Rectangle { width: parent.width; height: 1; color: OneUi.separator }

                OptionRow {
                    text: "Pomiń reguły Packagizera"

                    QQC2.Switch { id: overwrite }
                }
            }
        }

        Card {
            OptionRow {
                text: "Plik kontenera (DLC, CCF, RSDF)"

                PillButton {
                    text: "Wybierz"
                    iconName: "document-open"
                    onClicked: containerDialog.open()
                }
            }

            QQC2.Label {
                width: parent.width
                visible: page.containerResult.length > 0
                text: page.containerResult
                color: page.containerOk ? OneUi.green : OneUi.red
                font.pixelSize: OneUi.fontSize - 3
                wrapMode: Text.Wrap
            }
        }

        PillButton {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.min(page.width - 2 * OneUi.cardMargin, 320)
            text: autostart.checked ? "Dodaj i pobierz" : "Dodaj do sprawdzenia"
            iconName: "list-add"
            filled: true
            enabled: area.text.trim().length > 0
            onClicked: page.add()
        }
    }
}
