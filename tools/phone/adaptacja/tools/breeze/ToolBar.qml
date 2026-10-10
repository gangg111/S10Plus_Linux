/* SPDX-FileCopyrightText: 2020 Noah Davis <noahadvs@gmail.com>
 * SPDX-License-Identifier: LGPL-2.1-only OR LGPL-3.0-only OR LicenseRef-KDE-Accepted-LGPL
 */

pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Window
import QtQuick.Templates as T
import org.kde.kirigami as Kirigami

import org.kde.breeze.impl as Impl

T.ToolBar {
    id: control

    readonly property bool __isHeader: control.position === T.ToolBar.Header
    readonly property bool __isFooter: control.position === T.ToolBar.Footer

    implicitWidth: Math.max(implicitBackgroundWidth + leftInset + rightInset,
                            contentWidth + leftPadding + rightPadding)
    implicitHeight: Math.max(implicitBackgroundHeight + topInset + bottomInset,
                             contentHeight + topPadding + bottomPadding)

    spacing: Kirigami.Units.smallSpacing

    padding: Kirigami.Units.smallSpacing
    rightPadding: horizontalPadding + cameraInset

    // Galaxy S10+: with the shell panels auto-hidden the window covers the whole
    // portrait screen and the front camera hole sits over the top right corner
    // (from x = 367 pt, down to y = 52 pt). A toolbar on that corner ends before
    // it; with the status bar shown (window shorter than the screen) or in
    // landscape nothing changes.
    readonly property real cameraInset: {
        const w = control.Window.width;
        const h = control.Window.height;
        if (w <= 0 || Screen.width >= Screen.height || h < Screen.height - 1 || control.width <= 0) {
            return 0;
        }
        const p = control.mapToItem(null, control.width, 0);
        if (p.x < w - 1 || p.y > 52) {
            return 0;
        }
        return Math.max(0, w - 367);
    }

    // Add space for the separator above the footer
    topPadding: __isFooter && background && background.hasOwnProperty("separator") ?
        background.separator.height + verticalPadding : verticalPadding
    // Add space for the separator below the header
    bottomPadding: __isHeader && background && background.hasOwnProperty("separator") ?
        background.separator.height + verticalPadding : verticalPadding

    Kirigami.Theme.colorSet: __isHeader ? Kirigami.Theme.Header : Kirigami.Theme.Window
    Kirigami.Theme.inherit: false

    background: Impl.StandardRectangle {
        // Enough height for Buttons/ComboBoxes/TextFields with smallSpacing padding on top and bottom
        implicitHeight: Impl.Units.mediumControlHeight + (Kirigami.Units.smallSpacing * 2) + (separator.visible ? separator.height : 0)
        color: Kirigami.Theme.backgroundColor
        property Item separator: Kirigami.Separator {
            parent: control.background
            visible: control.__isHeader || control.__isFooter
            width: parent.width
            y: control.__isFooter ? 0 : parent.height - height
        }
    }
}
