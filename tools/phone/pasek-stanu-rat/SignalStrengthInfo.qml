/*
 *  SPDX-FileCopyrightText: 2021 Devin Lin <devin@kde.org>
 *  SPDX-FileCopyrightText: 2015 Marco Martin <mart@kde.org>
 *  SPDX-FileCopyrightText: 2021 Tobias Fella <fella@posteo.de>
 *
 *  SPDX-License-Identifier: GPL-2.0-or-later
 */

pragma Singleton

import QtQuick 2.1
import org.kde.plasma.mm
import org.kde.plasma.plasma5support 2.0 as P5Support

QtObject {
    id: root

    readonly property string icon: "network-mobile-" + Math.floor(SignalIndicator.strength / 20) * 20

    readonly property string label: SignalIndicator.simLocked ? i18n("SIM Locked") : SignalIndicator.name

    readonly property bool showIndicator: SignalIndicator.modemAvailable

    // S10+: oznaczenie technologii sieci (5G / LTE / H+ / 3G / E / 2G) dla paska
    // stanu, jak w One UI. SignalIndicator (ModemManager) nie wystawia RAT, wiec
    // czytamy je skryptem przez DataSource (silnik executable), co kilka sekund.
    property string technology: ""

    property P5Support.DataSource _ratSource: P5Support.DataSource {
        id: ratSource
        engine: "executable"
        connectedSources: []
        onNewData: function(source, data) {
            root.technology = ("" + (data["stdout"] || "")).trim();
            disconnectSource(source);
        }
    }

    property Timer _ratTimer: Timer {
        interval: 5000
        running: true
        repeat: true
        triggeredOnStart: true
        onTriggered: ratSource.connectSource("/usr/lib/s10plus/modem-rat.sh")
    }
}
