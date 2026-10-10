// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Every setting JD2 has (its "Advanced Settings": /config/list, about 2000
// entries in 200 groups, plugin settings included), searchable and editable:
// switches flip at once, numbers and text through the prompt, enums from
// their options, lists and objects as JSON. With prefix set it shows only one
// plugin's settings (interface names start with the plugin class).

import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import "oneui.js" as OneUi

Rectangle {
    id: page

    property string title: "Wszystkie ustawienia"
    property string prefix: ""
    property var entries: []
    property string query: ""
    property bool loading: false

    signal closed()

    readonly property var win: QQC2.ApplicationWindow.window

    color: OneUi.bg

    function load() {
        loading = true
        jd.call("/config/list", [".*", true, true, true, true], function (ok, d) {
            loading = false
            if (ok)
                page.entries = d
        })
    }

    function groupName(iface) {
        var s = iface.split(".").pop()
        return s.replace(/\$/g, " / ")
    }

    function label(e) {
        // CamelCase key into words: MaxSimultaneDownloads -> Max simultane downloads
        var k = e.key.replace(/([a-z0-9])([A-Z])/g, "$1 $2")
        return k.charAt(0).toUpperCase() + k.slice(1).toLowerCase()
    }

    function valueText(e) {
        var v = e.value
        if (e.abstractType === "BOOLEAN")
            return v ? "tak" : "nie"
        if (v === null || v === undefined)
            return "brak"
        if (typeof v === "object")
            return JSON.stringify(v).slice(0, 60)
        return "" + v
    }

    // A plugin's settings group is not always named after its class:
    // jd.plugins.hoster.OneFichierCom keeps them in ...config.OneFichierConfigInterface,
    // RealDebridCom in RealDebridComConfig, AllDebridCom in AllDebridCom$AlldebridComConfig.
    // Both reduce to the same stem.
    function stem(name) {
        var s = name.split(/[.$]/).pop().toLowerCase()
        s = s.replace(/configinterface$|config$/, "")
        return s.replace(/(com|net|org|to|cc|io)$/, "")
    }

    function belongs(iface) {
        return iface.indexOf(prefix) === 0 || stem(iface) === stem(prefix)
    }

    readonly property var shown: {
        var q = query.trim().toLowerCase()
        var out = []
        for (var i = 0; i < entries.length && out.length < 300; i++) {
            var e = entries[i]
            if (prefix.length > 0 && !belongs(e.interfaceName))
                continue
            if (q.length > 0 && (e.key + " " + e.interfaceName + " " + (e.docs || "")).toLowerCase().indexOf(q) < 0)
                continue
            out.push(e)
        }
        return out
    }

    function save(e, v) {
        jd.call("/config/set", [e.interfaceName, e.storage || null, e.key, v], function (ok) {
            if (!ok)
                return
            // the delegate holds a copy of the entry, so find it by its name
            var copy = page.entries.slice()
            var i = -1
            for (var j = 0; j < copy.length; j++) {
                if (copy[j].interfaceName === e.interfaceName && copy[j].key === e.key && copy[j].storage === e.storage) {
                    i = j
                    break
                }
            }
            if (i >= 0) {
                copy[i] = Object.assign({}, e, { value: v })
                page.entries = copy
            }
        })
    }

    function edit(e) {
        var t = e.abstractType
        if (t === "BOOLEAN") {
            save(e, !e.value)
        } else if (t === "ENUM") {
            win.prompt.choose(label(e), e.enumOptions.map(function (o) { return [o[0], o[1] || o[0]] }), e.value,
                              function (v) { page.save(e, v) })
        } else if (t === "INT" || t === "LONG" || t === "DOUBLE") {
            win.prompt.ask(label(e), e.value, function (v) {
                var n = Number(v.replace(",", "."))
                if (!isNaN(n))
                    page.save(e, t === "DOUBLE" ? n : Math.round(n))
            })
        } else if (t === "STRING") {
            win.prompt.ask(label(e), e.value, function (v) { page.save(e, v) })
        } else {
            win.prompt.ask(label(e) + " (JSON)", JSON.stringify(e.value), function (v) {
                try {
                    page.save(e, JSON.parse(v))
                } catch (err) {
                }
            })
        }
    }

    function actions(e) {
        // JD2's own description of the setting, when it has one
        win.sheet.show(label(e) + (e.docs ? ": " + e.docs : ""), [
            { text: "Zmień", icon: "document-edit", run: function () { page.edit(e) } },
            { text: "Przywróć domyślne (" + page.valueText({ abstractType: e.abstractType, value: e.defaultValue }) + ")",
              icon: "edit-undo", run: function () { page.save(e, e.defaultValue) } }
        ])
    }

    onVisibleChanged: if (visible && entries.length === 0) load()

    // header with back and search
    Column {
        id: head
        width: parent.width
        spacing: 10
        topPadding: 16

        Row {
            x: 12
            spacing: 6

            QQC2.ToolButton {
                implicitWidth: 48
                implicitHeight: 48
                onClicked: page.closed()
                contentItem: Kirigami.Icon {
                    source: "go-previous"
                    isMask: true
                    color: OneUi.text
                }
                background: null
            }

            QQC2.Label {
                anchors.verticalCenter: parent.verticalCenter
                width: page.width - 90
                text: page.title
                color: OneUi.text
                font.pixelSize: 24
                font.weight: Font.Bold
                elide: Text.ElideRight
            }
        }

        Rectangle {
            x: OneUi.cardMargin
            width: parent.width - 2 * OneUi.cardMargin
            height: 48
            radius: 24
            color: OneUi.pill

            Kirigami.Icon {
                x: 16
                anchors.verticalCenter: parent.verticalCenter
                width: 22
                height: 22
                isMask: true
                color: OneUi.pillText
                source: "search"
            }

            QQC2.TextField {
                anchors.left: parent.left
                anchors.leftMargin: 46
                anchors.right: parent.right
                anchors.rightMargin: 16
                anchors.verticalCenter: parent.verticalCenter
                placeholderText: page.loading ? "Wczytywanie" : "Szukaj w " + page.shown.length + (page.shown.length >= 300 ? "+" : "")
                placeholderTextColor: OneUi.pillText
                color: OneUi.text
                background: null
                inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText
                onTextChanged: page.query = text
            }
        }
    }

    ListView {
        anchors.top: head.bottom
        anchors.topMargin: 12
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        clip: true
        model: page.shown
        boundsBehavior: Flickable.StopAtBounds

        delegate: QQC2.ItemDelegate {
            id: row
            required property var modelData
            width: ListView.view.width
            height: col.implicitHeight + 24
            leftInset: OneUi.cardMargin
            rightInset: OneUi.cardMargin
            onClicked: page.edit(modelData)
            onPressAndHold: page.actions(modelData)

            background: Rectangle {
                color: row.down ? OneUi.cardPressed : OneUi.card
                Rectangle {
                    anchors.bottom: parent.bottom
                    x: 20
                    width: parent.width - 40
                    height: 1
                    color: OneUi.separator
                }
            }

            contentItem: Item {
                Column {
                    id: col
                    x: OneUi.cardMargin + 20
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 2 * OneUi.cardMargin - 40 - (sw.visible ? 60 : 0)
                    spacing: 2

                    QQC2.Label {
                        width: parent.width
                        text: page.label(row.modelData)
                        color: OneUi.text
                        font.pixelSize: OneUi.fontSize - 1
                        wrapMode: Text.Wrap
                    }

                    QQC2.Label {
                        width: parent.width
                        visible: row.modelData.abstractType !== "BOOLEAN"
                        text: page.valueText(row.modelData)
                        color: OneUi.blue
                        font.pixelSize: OneUi.fontSize - 3
                        elide: Text.ElideRight
                    }

                    QQC2.Label {
                        width: parent.width
                        text: page.groupName(row.modelData.interfaceName)
                        color: OneUi.subtitle
                        font.pixelSize: OneUi.fontSize - 4
                        elide: Text.ElideRight
                    }
                }

                QQC2.Switch {
                    id: sw
                    visible: row.modelData.abstractType === "BOOLEAN"
                    anchors.right: parent.right
                    anchors.rightMargin: OneUi.cardMargin + 12
                    anchors.verticalCenter: parent.verticalCenter
                    checked: !!row.modelData.value
                    onToggled: page.save(row.modelData, checked)
                }
            }
        }
    }

    QQC2.BusyIndicator {
        anchors.centerIn: parent
        running: page.loading
        visible: running
    }

    QQC2.Label {
        anchors.centerIn: parent
        visible: !page.loading && page.entries.length > 0 && page.shown.length === 0
        text: page.prefix.length > 0 && page.query.length === 0 ? "Ta wtyczka nie ma ustawień" : "Nic nie znaleziono"
        color: OneUi.subtitle
        font.pixelSize: OneUi.fontSize
    }
}
