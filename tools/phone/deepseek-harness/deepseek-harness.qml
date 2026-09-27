// Okno aplikacji DeepSeek Harness: Web UI serwera dsh bez przegladarki.
// Skrypt uruchamiajacy kopiuje ten plik do XDG_RUNTIME_DIR (0700) i wpisuje
// adres z tokenem w miejsce @DSH_URL@.
import QtQuick
import QtQuick.Window
import QtWebEngine

Window {
    id: okno
    visible: true
    visibility: Window.Maximized
    title: "DeepSeek Harness"
    color: "#101014"

    WebEngineView {
        id: widok
        anchors.fill: parent
        url: "@DSH_URL@"
        onNewWindowRequested: function(req) { Qt.openUrlExternally(req.requestedUrl) }
    }

    Rectangle {
        anchors.fill: parent
        color: "#101014"
        visible: widok.loading && widok.loadProgress < 100
        Rectangle {
            anchors.centerIn: parent
            width: parent.width * 0.5; height: 12; radius: 6
            color: "#26262e"
            Rectangle {
                width: parent.width * widok.loadProgress / 100
                height: parent.height; radius: 6
                color: "#4d6bfe"
            }
        }
    }
}
