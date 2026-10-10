// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// What JD2 asks the user: captchas of free hosters (captcha/list, get, solve,
// skip) and its own dialogs (dialogs/list, get, getTypeInfo, answer). check()
// runs with every refresh of the app; the first pending question shows up here.

import QtQuick
import QtQuick.Controls as QQC2
import "oneui.js" as OneUi

Rectangle {
    id: root

    property var captcha: null      // CaptchaJob
    property string image: ""
    property var dialog: null       // { id, type, properties, out }

    visible: captcha !== null || dialog !== null
    color: "#cc000000"

    MouseArea { anchors.fill: parent }

    function check() {
        jd.call("/captcha/list", [], function (ok, jobs) {
            if (!ok)
                return
            if (!jobs || jobs.length === 0) {
                root.captcha = null
                return
            }
            if (root.captcha && jobs.some(function (j) { return j.id === root.captcha.id }))
                return
            var job = jobs[0]
            jd.call("/captcha/get", [job.id], function (ok2, img) {
                root.image = ok2 ? "" + img : ""
                answer.text = ""
                root.captcha = job
            })
        })
        if (captcha)
            return
        jd.call("/dialogs/list", [], function (ok, ids) {
            if (!ok || !ids || ids.length === 0) {
                root.dialog = null
                return
            }
            if (root.dialog && ids.indexOf(root.dialog.id) >= 0)
                return
            var id = ids[0]
            jd.call("/dialogs/get", [id, false, true], function (ok2, info) {
                if (!ok2)
                    return
                jd.call("/dialogs/getTypeInfo", [info.type], function (ok3, ti) {
                    root.dialog = { id: id, type: info.type, properties: info.properties || {},
                                    out: ok3 && ti ? ti.out || {} : {} }
                })
            })
        })
    }

    function solve() {
        jd.call("/captcha/solve", [captcha.id, answer.text], function () { root.captcha = null })
    }

    function skip() {
        jd.call("/captcha/skip", [captcha.id, "SINGLE"], function () { root.captcha = null })
    }

    function reply(reason) {
        var data = { closereason: reason }
        for (var k in dialog.out) {
            if (k !== "closereason" && dialogField.text.length > 0)
                data[k] = dialogField.text
        }
        jd.call("/dialogs/answer", [dialog.id, data], function () { root.dialog = null })
    }

    Rectangle {
        anchors.centerIn: parent
        width: parent.width - 2 * OneUi.cardMargin
        height: box.implicitHeight + 40
        radius: OneUi.radius
        color: OneUi.card

        Column {
            id: box
            x: 20
            y: 20
            width: parent.width - 40
            spacing: 14

            QQC2.Label {
                width: parent.width
                text: root.captcha ? "Captcha  ·  " + (root.captcha.hoster || "") : (root.dialog ? (root.dialog.properties.title || "JDownloader") : "")
                color: OneUi.text
                font.pixelSize: OneUi.fontSize + 2
                font.weight: Font.DemiBold
                wrapMode: Text.Wrap
            }

            QQC2.Label {
                width: parent.width
                visible: text.length > 0
                text: root.captcha ? (root.captcha.explain || "") : (root.dialog ? (root.dialog.properties.message || "") : "")
                color: OneUi.text
                font.pixelSize: OneUi.fontSize - 1
                wrapMode: Text.Wrap
            }

            // captcha
            Image {
                visible: root.captcha !== null && root.image.length > 0
                width: parent.width
                height: visible ? Math.min(200, width * sourceSize.height / Math.max(1, sourceSize.width)) : 0
                fillMode: Image.PreserveAspectFit
                source: root.image
                smooth: false
            }

            QQC2.Label {
                width: parent.width
                visible: root.captcha !== null && root.image.length === 0
                text: "Ten rodzaj captchy JDownloader rozwiązuje tylko w przeglądarce"
                color: OneUi.orange
                font.pixelSize: OneUi.fontSize - 2
                wrapMode: Text.Wrap
            }

            Rectangle {
                visible: root.captcha !== null && root.image.length > 0
                width: parent.width
                height: 52
                radius: 26
                color: OneUi.pill

                QQC2.TextField {
                    id: answer
                    anchors.fill: parent
                    anchors.leftMargin: 20
                    anchors.rightMargin: 20
                    color: OneUi.text
                    background: null
                    placeholderText: "Tekst z obrazka"
                    placeholderTextColor: OneUi.pillText
                    inputMethodHints: Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase
                    onAccepted: root.solve()
                }
            }

            Row {
                visible: root.captcha !== null
                spacing: 10

                PillButton {
                    text: "Wyślij"
                    iconName: "dialog-ok-apply"
                    filled: true
                    enabled: answer.text.length > 0
                    onClicked: root.solve()
                }

                PillButton {
                    text: "Pomiń"
                    accent: OneUi.subtitle
                    onClicked: root.skip()
                }
            }

            // JD2 dialog: a text answer when it wants one, then OK / Cancel
            Rectangle {
                visible: root.dialog !== null && Object.keys(root.dialog.out).some(function (k) { return k !== "closereason" })
                width: parent.width
                height: visible ? 52 : 0
                radius: 26
                color: OneUi.pill

                QQC2.TextField {
                    id: dialogField
                    anchors.fill: parent
                    anchors.leftMargin: 20
                    anchors.rightMargin: 20
                    color: OneUi.text
                    background: null
                    text: root.dialog ? (root.dialog.properties.defaultvalue || "") : ""
                }
            }

            Row {
                visible: root.dialog !== null
                spacing: 10

                PillButton {
                    text: root.dialog && root.dialog.properties.ok_button_text ? root.dialog.properties.ok_button_text : "OK"
                    filled: true
                    onClicked: root.reply("OK")
                }

                PillButton {
                    text: root.dialog && root.dialog.properties.cancel_button_text ? root.dialog.properties.cancel_button_text : "Anuluj"
                    accent: OneUi.subtitle
                    onClicked: root.reply("CANCEL")
                }
            }
        }
    }
}
