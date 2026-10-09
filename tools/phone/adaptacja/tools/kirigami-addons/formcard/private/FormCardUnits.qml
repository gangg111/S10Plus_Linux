// Copyright 2024 Carl Schwan <carl@carlschwan.eu>
// SPDX-License-Identifier: LGPL-2.0-or-later

pragma Singleton

import QtQml
import QtQuick
import org.kde.kirigami as Kirigami

QtObject {
    // Galaxy S10+ port, One UI look: rows as tall as One UI ones (65 px with 17 px text),
    // the vertical padding follows the application font, so smaller fonts get lower rows
    readonly property FontMetrics _fontMetrics: FontMetrics {
        font: Qt.application.font
    }
    readonly property int horizontalPadding: 20
    readonly property int verticalPadding: Math.max(Kirigami.Units.largeSpacing + Kirigami.Units.smallSpacing,
                                                    Math.round(_fontMetrics.height * 0.85))

    readonly property int verticalSpacing: Kirigami.Units.smallSpacing
    readonly property int horizontalSpacing: Kirigami.Units.largeSpacing
}
