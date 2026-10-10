// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// One UI progress bar: thin rounded track. Determinate (value 0..1) or, when the
// length of the work is unknown, a segment running across the track.

import QtQuick
import "oneui.js" as OneUi

Rectangle {
    id: root

    property real value: 0
    property bool indeterminate: false
    property color accent: OneUi.blue

    implicitWidth: 200
    implicitHeight: 6
    radius: height / 2
    color: OneUi.track
    clip: true

    Rectangle {
        visible: !root.indeterminate
        width: root.width * Math.max(0, Math.min(1, root.value))
        height: root.height
        radius: root.radius
        color: root.accent
        Behavior on width { NumberAnimation { duration: 350; easing.type: Easing.OutCubic } }
    }

    Rectangle {
        id: runner
        visible: root.indeterminate
        width: root.width * 0.3
        height: root.height
        radius: root.radius
        color: root.accent

        NumberAnimation on x {
            running: root.indeterminate && root.visible
            loops: Animation.Infinite
            from: -runner.width
            to: root.width
            duration: 1200
            easing.type: Easing.InOutQuad
        }
    }
}
