// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Everything JD2's context menus do to packages and files, for the download
// list (downloadsV2) and the link grabber (linkgrabberv2), whose methods mostly
// share names. open(t, refresh) shows them in the action sheet; t is
// { ns, links: [ids], packages: [ids], name, link (bool), enabled, finished,
//   saveTo, stopMark (bool) }.

import QtQuick
import "oneui.js" as OneUi

QtObject {
    id: root

    property var sheet
    property var prompt
    property var copy           // function (text)

    readonly property var priorities: [["HIGHEST", "Najwyższy"], ["HIGHER", "Wyższy"], ["HIGH", "Wysoki"],
                                       ["DEFAULT", "Normalny"], ["LOW", "Niski"], ["LOWER", "Niższy"],
                                       ["LOWEST", "Najniższy"]]

    function call(path, params, refresh) {
        jd.call(path, params, function () { if (refresh) refresh() })
    }

    function open(t, refresh) {
        var ns = "/" + t.ns + "/"
        var dl = t.ns === "downloadsV2"
        var L = t.links, P = t.packages
        var one = t.link ? L[0] : P[0]
        var a = []

        if (dl) {
            a.push({ text: "Wznów pobieranie", icon: "media-playback-start", enabled: !t.finished, run: function () {
                jd.call(ns + "resumeLinks", [L, P], function () {
                    jd.call(ns + "setEnabled", [true, L, P], function () { root.call("/downloadcontroller/start", [], refresh) })
                })
            } })
            a.push({ text: "Pobierz teraz", icon: "download", enabled: !t.finished,
                     run: function () { root.call(ns + "forceDownload", [L, P], refresh) } })
        } else {
            a.push({ text: "Pobierz", icon: "download", run: function () {
                jd.call(ns + "moveToDownloadlist", [L, P], function () { root.call("/downloadcontroller/start", [], refresh) })
            } })
            a.push({ text: "Przenieś do pobierania bez startu", icon: "go-next",
                     run: function () { root.call(ns + "moveToDownloadlist", [L, P], refresh) } })
        }

        a.push({ text: t.enabled ? "Wyłącz" : "Włącz", icon: t.enabled ? "dialog-cancel" : "dialog-ok-apply",
                 run: function () { root.call(ns + "setEnabled", [!t.enabled, L, P], refresh) } })
        a.push({ text: "Sprawdź dostępność", icon: "view-refresh",
                 run: function () { root.call(ns + "startOnlineStatusCheck", [L, P], refresh) } })

        if (dl) {
            a.push({ text: "Resetuj", icon: "edit-undo",
                     run: function () { root.call(ns + "resetLinks", [L, P], refresh) } })
            a.push({ text: "Odblokuj pominięte", icon: "media-skip-backward",
                     run: function () { root.call(ns + "unskip", [P, L, null], refresh) } })
        }

        a.push({ text: "Zmień nazwę", icon: "edit-rename", run: function () {
            prompt.ask("Nowa nazwa", t.name, function (v) {
                if (v.length > 0)
                    root.call(ns + (t.link ? "renameLink" : "renamePackage"), [one, v], refresh)
            })
        } })
        if (!t.link)
            a.push({ text: "Folder pobierania", icon: "folder", run: function () {
                prompt.ask("Folder", t.saveTo, function (v) {
                    if (v.length > 0)
                        root.call(ns + "setDownloadDirectory", [v, P], refresh)
                })
            } })
        a.push({ text: "Priorytet", icon: "view-sort", run: function () {
            prompt.choose("Priorytet", root.priorities, t.priority || "DEFAULT",
                          function (v) { root.call(ns + "setPriority", [v, L, P], refresh) })
        } })
        a.push({ text: "Hasło do pobrania", icon: "lock", run: function () {
            prompt.ask("Hasło do pobrania", "", function (v) { root.call(ns + "setDownloadPassword", [L, P, v], refresh) }, true)
        } })
        a.push({ text: "Komentarz", icon: "document-edit", run: function () {
            prompt.ask("Komentarz", t.comment || "", function (v) { root.call(ns + "setComment", [L, P, !t.link, v], refresh) })
        } })

        if (t.link && !dl)
            a.push({ text: "Wariant", icon: "view-list-details", run: function () { root.variants(one, refresh) } })

        a.push({ text: "Przenieś na początek", icon: "go-top", run: function () {
            if (t.link)
                root.call(ns + "moveLinks", [L, null, t.packageOf], refresh)
            else
                root.call(ns + "movePackages", [P, null], refresh)
        } })
        if (!t.link && t.lastPackage !== undefined && t.lastPackage !== one)
            a.push({ text: "Przenieś na koniec", icon: "go-bottom",
                     run: function () { root.call(ns + "movePackages", [P, t.lastPackage], refresh) } })
        a.push({ text: "Nowy pakiet", icon: "folder-new", run: function () {
            prompt.ask("Nazwa nowego pakietu", t.name, function (v) {
                if (v.length > 0)
                    root.call(ns + "movetoNewPackage", [L, P, v, t.saveTo || null], refresh)
            })
        } })
        if (!t.link)
            a.push({ text: "Podziel według hostingu", icon: "split",
                     run: function () { root.call(ns + "splitPackageByHoster", [L, P], refresh) } })
        a.push({ text: "Kopiuj linki", icon: "edit-copy", run: function () {
            // { url: [link ids] }; CONTENT is the link itself, ORIGIN only
            // the page a crawler found it on (empty for plain links)
            jd.call(ns + "getDownloadUrls", [L, P, ["CONTENT"]], function (ok, d) {
                if (ok)
                    root.copy(Object.keys(d).join("\n"))
            })
        } })

        if (dl) {
            a.push({ text: t.stopMark ? "Usuń znacznik zatrzymania" : "Zatrzymaj po tym", icon: "media-playback-stop",
                     run: function () {
                         if (t.stopMark)
                             root.call(ns + "removeStopMark", [], refresh)
                         else
                             root.call(ns + "setStopMark", [t.link ? one : null, t.link ? null : one], refresh)
                     } })
        }
        if (t.saveTo)
            a.push({ text: "Otwórz folder", icon: "folder-open", run: function () { jd.openFolder(t.saveTo) } })
        a.push({ text: "Usuń z listy", icon: "list-remove", danger: true,
                 run: function () { root.call(ns + "removeLinks", [L, P], refresh) } })
        if (dl)
            a.push({ text: "Usuń razem z plikami", icon: "edit-delete", danger: true, run: function () {
                root.call(ns + "cleanup", [L, P, "DELETE_ALL", "REMOVE_LINKS_AND_DELETE_FILES", "SELECTED"], refresh)
            } })

        sheet.show(t.name, a)
    }

    // the variants a plugin offers for one file (e.g. quality of a video)
    function variants(linkId, refresh) {
        jd.call("/linkgrabberv2/getVariants", [linkId], function (ok, list) {
            if (!ok || !list || list.length === 0) {
                sheet.show("Ten plik nie ma wariantów", [])
                return
            }
            prompt.choose("Wariant", list.map(function (v) { return [v.id, v.name] }), null, function (id) {
                root.call("/linkgrabberv2/setVariant", [linkId, id], refresh)
            })
        })
    }
}
