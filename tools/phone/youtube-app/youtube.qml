// YouTube jako aplikacja Qt WebEngine. Gorny pasek = strefa bezpieczna pod
// otwor aparatu (prawy gorny rog, 142 px fiz); tresc zaczyna sie ponizej.
import QtQuick
import QtQuick.Window
import QtWebEngine

Window {
    id: okno
    visible: true
    visibility: Window.Maximized
    title: "YouTube"
    color: "#0f0f0f"

    // wysokosc otworu aparatu w px logicznych (142 px fiz / skala) + zapas
    readonly property int camInset: Math.round(142 / Screen.devicePixelRatio) + 4

    WebEngineProfile {
        id: profil
        storageName: "youtube"
        offTheRecord: false
        persistentCookiesPolicy: WebEngineProfile.ForcePersistentCookies
        httpUserAgent: "Mozilla/5.0 (Linux; Android 13; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
    }

    Rectangle {
        id: pasekAparatu
        anchors { left: parent.left; right: parent.right; top: parent.top }
        height: okno.camInset
        color: "#0f0f0f"
        z: 2
    }

    WebEngineView {
        id: widok
        anchors.fill: parent
        anchors.topMargin: okno.camInset
        profile: profil
        url: "https://m.youtube.com"
        settings.fullScreenSupportEnabled: true
        onFullScreenRequested: function(req) { req.accept() }
        onNewWindowRequested: function(req) { widok.url = req.requestedUrl }
    }
}
