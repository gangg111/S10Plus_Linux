// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// A settings row inside a Card: label on the left, any control on the right.

import QtQuick
import QtQuick.Controls as QQC2
import "oneui.js" as OneUi

Item {
    id: root

    property alias text: label.text
    property color textColor: OneUi.text
    default property alias control: slot.data

    width: parent ? parent.width : 300
    implicitHeight: Math.max(48, slot.childrenRect.height)

    QQC2.Label {
        id: label
        anchors.left: parent.left
        anchors.right: slot.left
        anchors.rightMargin: 12
        anchors.verticalCenter: parent.verticalCenter
        color: root.textColor
        font.pixelSize: OneUi.fontSize
        wrapMode: Text.WordWrap
    }

    Item {
        id: slot
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        width: childrenRect.width
        height: childrenRect.height
    }
}
