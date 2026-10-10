// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// One UI dark palette and sizes, the same values as the phone's settings app
// (tools/phone/plasma-settings-oneui), plus Polish number formatting.
.pragma library

var bg = "#010101"
var card = "#171719"
var cardPressed = "#2a2a2e"
var separator = "#3a3a3c"
var text = "#fafafa"
var subtitle = "#a3a2a7"
var pill = "#232325"
var pillText = "#a1a0a5"
var track = "#2c2c2f"

var blue = "#377aff"
var green = "#65c33b"
var red = "#d83e36"
var orange = "#e65b18"

var cardMargin = 13
var radius = 28
var fontSize = 17

function num(x, digits) {
    return x.toFixed(digits).replace(".", ",")
}

function size(bytes) {
    if (bytes === undefined || bytes === null || bytes < 0)
        return "?"
    var u = ["B", "kB", "MB", "GB", "TB"]
    var i = 0
    var v = bytes
    while (v >= 1000 && i < u.length - 1) {
        v /= 1000
        i++
    }
    return (i === 0 ? v : num(v, v < 10 ? 2 : (v < 100 ? 1 : 0))) + " " + u[i]
}

function speed(bps) {
    return size(bps) + "/s"
}

function eta(s) {
    if (s === undefined || s === null || s < 0)
        return ""
    s = Math.round(s)
    var h = Math.floor(s / 3600)
    var m = Math.floor((s % 3600) / 60)
    var sec = s % 60
    if (h > 0)
        return h + " h " + m + " min"
    if (m > 0)
        return m + " min " + sec + " s"
    return sec + " s"
}

function progress(done, total) {
    return total > 0 ? Math.min(1, done / total) : 0
}
