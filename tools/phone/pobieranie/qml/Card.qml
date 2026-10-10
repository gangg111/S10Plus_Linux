// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// One UI card: rounded dark panel, inset from the screen edges, children in a column.

import QtQuick
import "oneui.js" as OneUi

Item {
    id: root

    default property alias content: column.data
    property real padding: 20
    property alias spacing: column.spacing

    width: parent ? parent.width : 300
    implicitHeight: column.implicitHeight + 2 * padding

    Rectangle {
        id: panel
        width: root.width - 2 * OneUi.cardMargin
        height: root.height
        anchors.horizontalCenter: parent.horizontalCenter
        radius: OneUi.radius
        color: OneUi.card

        Column {
            id: column
            x: root.padding
            y: root.padding
            width: panel.width - 2 * root.padding
            spacing: 12
        }
    }
}
