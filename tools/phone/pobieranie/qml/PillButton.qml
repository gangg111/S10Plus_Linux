// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// One UI pill button: rendered Breeze glyph and label, filled (accent) or flat.

import QtQuick
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami
import "oneui.js" as OneUi

QQC2.AbstractButton {
    id: root

    property string iconName
    property color accent: OneUi.blue
    property bool filled: false

    implicitHeight: 52
    implicitWidth: row.implicitWidth + 40
    opacity: enabled ? 1 : 0.4

    background: Rectangle {
        radius: height / 2
        color: root.filled ? (root.down ? Qt.darker(root.accent, 1.2) : root.accent)
                           : (root.down ? OneUi.cardPressed : OneUi.pill)
    }

    contentItem: Item {
        Row {
            id: row
            anchors.centerIn: parent
            spacing: 8

            Kirigami.Icon {
                visible: root.iconName.length > 0
                width: 22
                height: 22
                anchors.verticalCenter: parent.verticalCenter
                source: root.iconName
                isMask: true
                color: root.filled ? "white" : root.accent
            }

            QQC2.Label {
                anchors.verticalCenter: parent.verticalCenter
                visible: root.text.length > 0
                text: root.text
                font.pixelSize: OneUi.fontSize
                font.weight: Font.DemiBold
                color: root.filled ? "white" : root.accent
            }
        }
    }
}
