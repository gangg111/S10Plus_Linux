// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Hosting services: premium accounts (JD2 accountsV2: list, add, refresh,
// enable, remove) and every hoster JD2 has a plugin for, searchable.
// Plugins themselves come from JD2's update server, see SettingsPage.

import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import "oneui.js" as OneUi

Item {
    id: page

    property var accounts: []
    property var premiumHosters: []     // hosters that take an account
    property var allHosters: []         // every hoster with a plugin
    property string query: ""
    property bool adding: false
    property string chosenHoster: ""
    property string error: ""
    property var basicAuths: []
    property var pluginClass: ({})      // host -> plugin class (its settings live under that name)

    readonly property var win: QQC2.ApplicationWindow.window

    function reload() {
        jd.call("/accountsV2/listAccounts", [{ enabled: true, error: true, trafficLeft: true, trafficMax: true,
                                               userName: true, valid: true, validUntil: true }],
                function (ok, d) { if (ok) page.accounts = d })
        jd.call("/accountsV2/listBasicAuth", [], function (ok, d) { if (ok) page.basicAuths = d })
        if (Object.keys(pluginClass).length === 0)
            jd.call("/plugins/list", [{ pattern: false, version: true }], function (ok, d) {
                if (!ok)
                    return
                var m = {}
                d.forEach(function (p) { m[p.displayName] = p.className })
                page.pluginClass = m
            })
        if (premiumHosters.length === 0)
            jd.call("/accountsV2/listPremiumHoster", [], function (ok, d) { if (ok) page.premiumHosters = d.sort() })
        if (allHosters.length === 0)
            jd.call("/plugins/getAllPluginRegex", [], function (ok, d) { if (ok) page.allHosters = Object.keys(d).sort() })
    }

    function dateOf(ms) {
        if (!ms || ms <= 0)
            return ""
        var d = new Date(ms)
        return ("0" + d.getDate()).slice(-2) + "." + ("0" + (d.getMonth() + 1)).slice(-2) + "." + d.getFullYear()
    }

    // second line: state of the account, as JD2 reports it after checking
    function accountLine(a) {
        var parts = []
        if (!a.enabled)
            parts.push("wyłączone")
        else if (a.errorType)
            parts.push(a.errorString || a.errorType)
        else if (a.validUntil > 0)
            parts.push("ważne do " + dateOf(a.validUntil))
        else if (a.valid === undefined && a.trafficLeft === undefined)
            parts.push("sprawdzanie konta")
        if (a.enabled && a.trafficLeft >= 0 && a.trafficLeft !== null && a.trafficLeft !== undefined)
            parts.push("zostało " + OneUi.size(a.trafficLeft)
                       + (a.trafficMax > 0 ? " z " + OneUi.size(a.trafficMax) : ""))
        return parts.join("  ·  ")
    }

    // JD2 checks a new or refreshed account in the background: ask again for a while
    Timer {
        id: accountPoll
        property int left: 0
        interval: 2000
        repeat: true
        onTriggered: {
            page.reload()
            if (--left <= 0)
                stop()
        }
    }

    function pollAccounts() {
        accountPoll.left = 10
        accountPoll.restart()
    }

    function accountActions(a) {
        var done = function () { page.reload() }
        win.sheet.show(a.hostname + "  ·  " + (a.username || ""), [
            { text: "Odśwież", icon: "view-refresh",
              run: function () { jd.call("/accountsV2/refreshAccounts", [[a.uuid], true], function () { page.pollAccounts() }) } },
            { text: a.enabled ? "Wyłącz" : "Włącz", icon: a.enabled ? "dialog-cancel" : "dialog-ok-apply",
              run: function () { jd.call(a.enabled ? "/accountsV2/disableAccounts" : "/accountsV2/enableAccounts", [[a.uuid]], done) } },
            { text: "Zmień login i hasło", icon: "document-edit", run: function () {
                win.prompt.ask("Login", a.username || "", function (user) {
                    win.prompt.ask("Hasło", "", function (pass) {
                        jd.call("/accountsV2/setUserNameAndPassword", [a.uuid, user, pass], done)
                    }, true)
                })
            } },
            { text: "Ustawienia wtyczki", icon: "configure", run: function () { page.pluginSettings(a.hostname) } },
            { text: "Usuń", icon: "edit-delete", danger: true,
              run: function () { jd.call("/accountsV2/removeAccounts", [[a.uuid]], done) } }
        ])
    }

    function pluginSettings(host) {
        var cls = pluginClass[host]
        win.openAdvanced(cls ? cls : "jd.plugins.hoster." + host, "Wtyczka " + host)
    }

    function hostActions(host) {
        var premium = premiumHosters.indexOf(host) >= 0
        win.sheet.show(host, [
            { text: "Ustawienia wtyczki", icon: "configure", run: function () { page.pluginSettings(host) } },
            { text: "Dodaj konto", icon: "list-add", enabled: premium, run: function () {
                page.adding = true
                page.chosenHoster = host
                page.error = ""
            } },
            { text: "Kup konto", icon: "globe", enabled: premium, run: function () {
                jd.call("/accountsV2/getPremiumHosterUrl", [host], function (ok, url) { if (ok && url) Qt.openUrlExternally(url) })
            } }
        ])
    }

    // HTTP/FTP logins JD2 sends to sites that ask for one
    function addBasicAuth() {
        win.prompt.choose("Rodzaj", [["HTTP", "HTTP"], ["FTP", "FTP"]], "HTTP", function (type) {
            win.prompt.ask("Adres (np. *.example.com)", "", function (mask) {
                win.prompt.ask("Login", "", function (user) {
                    win.prompt.ask("Hasło", "", function (pass) {
                        jd.call("/accountsV2/addBasicAuth", [type, mask, user, pass], function () { page.reload() })
                    }, true)
                })
            })
        })
    }

    function basicAuthActions(b) {
        var done = function () { page.reload() }
        win.sheet.show(b.hostmask + "  ·  " + b.username, [
            { text: b.enabled ? "Wyłącz" : "Włącz", icon: "dialog-ok-apply", run: function () {
                jd.call("/accountsV2/updateBasicAuth", [Object.assign({}, b, { enabled: !b.enabled })], done)
            } },
            { text: "Zmień hasło", icon: "lock", run: function () {
                win.prompt.ask("Hasło", "", function (pass) {
                    jd.call("/accountsV2/updateBasicAuth", [Object.assign({}, b, { password: pass })], done)
                }, true)
            } },
            { text: "Usuń", icon: "edit-delete", danger: true,
              run: function () { jd.call("/accountsV2/removeBasicAuths", [[b.id]], done) } }
        ])
    }

    readonly property var shown: {
        var list = adding ? premiumHosters : allHosters
        var q = query.trim().toLowerCase()
        var out = []
        for (var i = 0; i < list.length && out.length < 200; i++) {
            if (q.length === 0 || list[i].indexOf(q) >= 0)
                out.push(list[i])
        }
        return out
    }

    // search over the hosters, above the list: a list rebuilt on every keystroke
    // would take the focus away from a field in its header
    Rectangle {
        id: searchBar
        visible: page.chosenHoster.length === 0
        anchors.top: parent.top
        x: OneUi.cardMargin
        width: parent.width - 2 * OneUi.cardMargin
        height: visible ? 48 : 0
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
            id: search
            anchors.left: parent.left
            anchors.leftMargin: 46
            anchors.right: parent.right
            anchors.rightMargin: 16
            anchors.verticalCenter: parent.verticalCenter
            placeholderText: page.adding ? "Wybierz hosting z " + page.premiumHosters.length
                                         : "Szukaj w " + page.allHosters.length + " hostingach"
            placeholderTextColor: OneUi.pillText
            color: OneUi.text
            background: null
            inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText
            onTextChanged: page.query = text
        }
    }

    ListView {
        id: list
        anchors.top: searchBar.bottom
        anchors.topMargin: searchBar.visible ? 14 : 0
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        model: page.chosenHoster.length > 0 ? [] : page.shown
        // the search field sits in the header: a new model must not take its focus
        keyNavigationEnabled: false
        currentIndex: -1
        highlightFollowsCurrentItem: false

        header: Column {
            width: list.width
            spacing: 16
            bottomPadding: 12

            // accounts
            Card {
                visible: !page.adding

                QQC2.Label {
                    text: "Konta premium"
                    color: OneUi.text
                    font.pixelSize: OneUi.fontSize
                    font.weight: Font.DemiBold
                }

                Repeater {
                    model: page.accounts

                    delegate: QQC2.ItemDelegate {
                        id: accountRow
                        required property var modelData
                        width: parent.width
                        height: Math.max(60, accountCol.implicitHeight + 16)
                        padding: 0
                        background: null
                        onClicked: page.accountActions(modelData)

                        contentItem: Row {
                            spacing: 12

                            Rectangle {
                                width: 32
                                height: 32
                                radius: 16
                                anchors.verticalCenter: parent.verticalCenter
                                color: !accountRow.modelData.enabled ? OneUi.subtitle
                                       : (accountRow.modelData.errorType ? OneUi.red : OneUi.green)

                                Kirigami.Icon {
                                    anchors.centerIn: parent
                                    width: 22
                                    height: 22
                                    isMask: true
                                    color: "white"
                                    source: "user-identity"
                                }
                            }

                            Column {
                                id: accountCol
                                width: accountRow.width - 44
                                anchors.verticalCenter: parent.verticalCenter
                                spacing: 2

                                QQC2.Label {
                                    width: parent.width
                                    text: accountRow.modelData.hostname
                                    color: OneUi.text
                                    font.pixelSize: OneUi.fontSize
                                    elide: Text.ElideRight
                                }

                                QQC2.Label {
                                    width: parent.width
                                    visible: text.length > 0
                                    text: accountRow.modelData.username || ""
                                    color: OneUi.subtitle
                                    font.pixelSize: OneUi.fontSize - 3
                                    elide: Text.ElideRight
                                }

                                QQC2.Label {
                                    width: parent.width
                                    visible: text.length > 0
                                    text: page.accountLine(accountRow.modelData)
                                    color: OneUi.subtitle
                                    font.pixelSize: OneUi.fontSize - 3
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }

                PillButton {
                    text: "Dodaj konto"
                    iconName: "list-add"
                    filled: true
                    onClicked: {
                        page.adding = true
                        page.query = ""
                        search.text = ""
                    }
                }
            }

            // HTTP / FTP logins for sites
            Card {
                visible: !page.adding

                QQC2.Label {
                    text: "Logowanie do stron (HTTP, FTP)"
                    color: OneUi.text
                    font.pixelSize: OneUi.fontSize
                    font.weight: Font.DemiBold
                }

                Repeater {
                    model: page.basicAuths

                    delegate: QQC2.ItemDelegate {
                        id: authRow
                        required property var modelData
                        width: parent.width
                        height: 52
                        padding: 0
                        background: null
                        onClicked: page.basicAuthActions(modelData)

                        contentItem: Column {
                            spacing: 2
                            opacity: authRow.modelData.enabled ? 1 : 0.45

                            QQC2.Label {
                                text: authRow.modelData.hostmask
                                color: OneUi.text
                                font.pixelSize: OneUi.fontSize
                            }

                            QQC2.Label {
                                text: authRow.modelData.type + "  ·  " + authRow.modelData.username
                                color: OneUi.subtitle
                                font.pixelSize: OneUi.fontSize - 3
                            }
                        }
                    }
                }

                PillButton {
                    text: "Dodaj logowanie"
                    iconName: "list-add"
                    onClicked: page.addBasicAuth()
                }
            }

            // adding: hoster chosen, now the login
            Card {
                visible: page.adding && page.chosenHoster.length > 0

                QQC2.Label {
                    width: parent.width
                    text: page.chosenHoster
                    color: OneUi.text
                    font.pixelSize: OneUi.fontSize + 2
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                QQC2.TextField {
                    id: login
                    width: parent.width
                    placeholderText: "Login lub e-mail"
                    placeholderTextColor: OneUi.pillText
                    color: OneUi.text
                    inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText
                }

                QQC2.TextField {
                    id: password
                    width: parent.width
                    placeholderText: "Hasło"
                    placeholderTextColor: OneUi.pillText
                    color: OneUi.text
                    echoMode: TextInput.Password
                    inputMethodHints: Qt.ImhNoAutoUppercase | Qt.ImhNoPredictiveText | Qt.ImhSensitiveData
                }

                QQC2.Label {
                    width: parent.width
                    visible: page.error.length > 0
                    text: page.error
                    color: OneUi.red
                    font.pixelSize: OneUi.fontSize - 3
                    wrapMode: Text.WordWrap
                }

                Row {
                    spacing: 10

                    PillButton {
                        text: "Dodaj"
                        iconName: "dialog-ok-apply"
                        filled: true
                        enabled: login.text.length > 0 && password.text.length > 0
                        onClicked: {
                            page.error = ""
                            jd.call("/accountsV2/addAccount", [page.chosenHoster, login.text, password.text],
                                    function (ok, d) {
                                        password.text = ""
                                        if (!ok) {
                                            page.error = "JDownloader nie przyjął konta"
                                            return
                                        }
                                        login.text = ""
                                        page.chosenHoster = ""
                                        page.adding = false
                                        page.pollAccounts()
                                    })
                        }
                    }

                    PillButton {
                        text: "Kup konto"
                        iconName: "globe"
                        onClicked: jd.call("/accountsV2/getPremiumHosterUrl", [page.chosenHoster], function (ok, url) {
                            if (ok && url)
                                Qt.openUrlExternally(url)
                        })
                    }

                    PillButton {
                        text: "Anuluj"
                        accent: OneUi.subtitle
                        onClicked: {
                            password.text = ""
                            page.chosenHoster = ""
                            page.adding = false
                        }
                    }
                }
            }

            // adding: back to the accounts
            PillButton {
                visible: page.adding && page.chosenHoster.length === 0
                x: OneUi.cardMargin
                text: "Anuluj dodawanie"
                accent: OneUi.subtitle
                onClicked: page.adding = false
            }
        }

        delegate: QQC2.ItemDelegate {
            id: hostRow
            required property string modelData
            readonly property bool premium: page.premiumHosters.indexOf(modelData) >= 0
            width: list.width
            height: 54
            padding: 0
            leftInset: OneUi.cardMargin
            rightInset: OneUi.cardMargin
            onClicked: {
                if (page.adding) {
                    page.chosenHoster = modelData
                    page.error = ""
                } else {
                    page.hostActions(modelData)
                }
            }

            background: Rectangle {
                color: hostRow.down ? OneUi.cardPressed : OneUi.card
                Rectangle {
                    anchors.bottom: parent.bottom
                    x: 20
                    width: parent.width - 40
                    height: 1
                    color: OneUi.separator
                }
            }

            contentItem: Item {
                QQC2.Label {
                    x: OneUi.cardMargin + 20
                    anchors.verticalCenter: parent.verticalCenter
                    width: parent.width - 2 * OneUi.cardMargin - 120
                    text: hostRow.modelData
                    color: OneUi.text
                    font.pixelSize: OneUi.fontSize - 1
                    elide: Text.ElideRight
                }

                Rectangle {
                    visible: hostRow.premium && !page.adding
                    anchors.right: parent.right
                    anchors.rightMargin: OneUi.cardMargin + 20
                    anchors.verticalCenter: parent.verticalCenter
                    width: badge.implicitWidth + 20
                    height: 26
                    radius: 13
                    color: OneUi.pill

                    QQC2.Label {
                        id: badge
                        anchors.centerIn: parent
                        text: "konto"
                        color: OneUi.blue
                        font.pixelSize: OneUi.fontSize - 4
                    }
                }
            }
        }
    }
}
