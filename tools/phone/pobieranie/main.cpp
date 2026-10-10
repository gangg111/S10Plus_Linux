// SPDX-FileCopyrightText: 2026 Artur <ganggg111@gmail.com>
// SPDX-License-Identifier: GPL-2.0-or-later
//
// Pobieranie: a phone front end (One UI look) for JDownloader 2, which runs
// without its Swing window as the user service jdownloader.service. The app
// talks to JD2's local API through /run/jdapi/jdapi.sock (jdapi-proxy.py);
// port 3128 itself is closed to everything but that proxy, see the firewall
// unit. Links given on the command line open the "add" page filled in.

#include <QClipboard>
#include <QDesktopServices>
#include <QDir>
#include <QFile>
#include <QFont>
#include <QGuiApplication>
#include <QIcon>
#include <QJSEngine>
#include <QJSValue>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QJsonValue>
#include <QLocalSocket>
#include <QProcess>
#include <QQmlApplicationEngine>
#include <QQmlContext>
#include <QTimer>
#include <QUrl>

static const char *SOCKET = "/run/jdapi/jdapi.sock";
static const char *UNIT = "jdownloader.service";

class JdApi : public QObject
{
    Q_OBJECT
    Q_PROPERTY(QStringList initialLinks READ initialLinks CONSTANT)
    // POBIERANIE_TEST_UPDATE=1: every update check reports an update, to test "Zainstaluj"
    Q_PROPERTY(bool testUpdate READ testUpdate CONSTANT)

public:
    JdApi(QJSEngine *engine, QStringList links)
        : m_engine(engine)
        , m_links(std::move(links))
    {
    }

    QStringList initialLinks() const
    {
        return m_links;
    }

    bool testUpdate() const
    {
        return qEnvironmentVariableIntValue("POBIERANIE_TEST_UPDATE") == 1;
    }

    // call("/downloadsV2/queryPackages", [{...}], function (ok, data) {...});
    // every parameter goes as JSON, url-encoded, in the documented order
    Q_INVOKABLE void call(const QString &path, const QVariantList &params, QJSValue callback)
    {
        QStringList encoded;
        for (const QVariant &p : params) {
            // QJsonDocument cannot hold a bare value, so serialise [value] and peel it
            QByteArray json = QJsonDocument(QJsonArray{QJsonValue::fromVariant(p)}).toJson(QJsonDocument::Compact);
            json = json.mid(1, json.size() - 2);
            encoded << QString::fromLatin1(QUrl::toPercentEncoding(QString::fromUtf8(json)));
        }
        const QByteArray request = "GET " + (path + (encoded.isEmpty() ? QString() : QStringLiteral("?") + encoded.join(QLatin1Char('&')))).toUtf8()
            + " HTTP/1.0\r\n\r\n";

        auto *socket = new QLocalSocket(this);
        socket->setProperty("path", path);
        auto *timer = new QTimer(socket);
        auto buffer = std::make_shared<QByteArray>();
        auto done = std::make_shared<bool>(false);
        auto finish = [this, socket, callback, buffer, done](bool transport) mutable {
            if (*done)
                return;
            *done = true;
            bool ok = false;
            QJSValue data;
            // HTTP status: 0 no answer from the proxy, 503 JD2 not listening (proxy), else JD2's own
            int code = 0;
            const int split = buffer->indexOf("\r\n\r\n");
            if (transport && split > 0) {
                const QList<QByteArray> status = buffer->left(buffer->indexOf("\r\n")).split(' ');
                code = status.size() > 1 ? status.at(1).toInt() : 0;
                const QJsonDocument doc = QJsonDocument::fromJson(buffer->mid(split + 4));
                ok = code == 200;
                if (ok && doc.isObject())
                    data = m_engine->toScriptValue(doc.object().value(QStringLiteral("data")).toVariant());
                else
                    data = m_engine->toScriptValue(doc.toVariant());
            } else {
                data = QJSValue(QStringLiteral("offline"));
            }
            if (qEnvironmentVariableIsSet("JDAPI_TRACE"))
                qWarning("jdapi trace: %s done ok=%d bytes=%lld", socket->property("path").toByteArray().constData(), ok,
                         (long long)buffer->size());
            if (!ok)
                qWarning("jdapi: %s -> %s (%s)", socket->property("path").toByteArray().constData(),
                         transport ? buffer->left(80).constData() : "no answer", qPrintable(socket->errorString()));
            if (callback.isCallable())
                callback.call({QJSValue(ok), data, QJSValue(code)});
            socket->deleteLater();
        };
        connect(socket, &QLocalSocket::connected, socket, [socket, request] {
            socket->write(request);
        });
        connect(socket, &QLocalSocket::readyRead, socket, [socket, buffer] {
            buffer->append(socket->readAll());
        });
        connect(socket, &QLocalSocket::disconnected, socket, [socket, buffer, finish]() mutable {
            buffer->append(socket->readAll());
            finish(true);
        });
        connect(socket, &QLocalSocket::errorOccurred, socket, [finish](QLocalSocket::LocalSocketError e) mutable {
            if (e != QLocalSocket::PeerClosedError)
                finish(false);
        });
        connect(timer, &QTimer::timeout, socket, [finish]() mutable {
            finish(false);
        });
        timer->setSingleShot(true);
        timer->start(60000);
        if (qEnvironmentVariableIsSet("JDAPI_TRACE"))
            qWarning("jdapi trace: %s start", request.left(120).constData());
        socket->connectToServer(QString::fromLatin1(SOCKET));
    }

    Q_INVOKABLE void startBackend()
    {
        QProcess::startDetached(QStringLiteral("systemctl"), {QStringLiteral("--user"), QStringLiteral("start"), QString::fromLatin1(UNIT)});
    }

    Q_INVOKABLE void stopBackend()
    {
        QProcess::startDetached(QStringLiteral("systemctl"), {QStringLiteral("--user"), QStringLiteral("stop"), QString::fromLatin1(UNIT)});
    }

    // main PID of jdownloader.service (0 when stopped): a new one means JD2 was restarted
    Q_INVOKABLE int backendPid() const
    {
        QProcess p;
        p.start(QStringLiteral("systemctl"), {QStringLiteral("--user"), QStringLiteral("show"), QStringLiteral("-p"),
                                              QStringLiteral("MainPID"), QStringLiteral("--value"), QString::fromLatin1(UNIT)});
        if (!p.waitForFinished(2000))
            return -1;
        return p.readAllStandardOutput().trimmed().toInt();
    }

    // JD2 with the user session (systemctl --user enable), otherwise only while the app asks
    Q_INVOKABLE bool autostart() const
    {
        return QFile::exists(QDir::homePath() + QStringLiteral("/.config/systemd/user/default.target.wants/") + QString::fromLatin1(UNIT));
    }

    Q_INVOKABLE void setAutostart(bool on)
    {
        QProcess::execute(QStringLiteral("systemctl"),
                          {QStringLiteral("--user"), on ? QStringLiteral("enable") : QStringLiteral("disable"), QString::fromLatin1(UNIT)});
    }

    Q_INVOKABLE void openFolder(const QString &path)
    {
        QDesktopServices::openUrl(QUrl::fromLocalFile(path));
    }

    Q_INVOKABLE void restartBackend()
    {
        QProcess::startDetached(QStringLiteral("systemctl"), {QStringLiteral("--user"), QStringLiteral("restart"), QString::fromLatin1(UNIT)});
    }

    Q_INVOKABLE void copyText(const QString &text)
    {
        QGuiApplication::clipboard()->setText(text);
    }

    // a container file (DLC, CCF, RSDF) as JD2's addContainer wants it: base64 of the file
    Q_INVOKABLE QString readFileBase64(const QString &pathOrUrl) const
    {
        const QString path = pathOrUrl.startsWith(QLatin1String("file:")) ? QUrl(pathOrUrl).toLocalFile() : pathOrUrl;
        QFile f(path);
        if (!f.open(QIODevice::ReadOnly) || f.size() > 16 * 1024 * 1024)
            return QString();
        return QString::fromLatin1(f.readAll().toBase64());
    }

private:
    QJSEngine *m_engine;
    QStringList m_links;
};

int main(int argc, char *argv[])
{
    QGuiApplication app(argc, argv);
    app.setApplicationName(QStringLiteral("pobieranie"));
    app.setOrganizationDomain(QStringLiteral("s10plus.pl"));
    app.setDesktopFileName(QStringLiteral("pl.s10plus.pobieranie"));
    app.setApplicationDisplayName(QStringLiteral("JDownloader 2"));
    // JD2's own logo, installed into the icon theme by zainstaluj.sh
    app.setWindowIcon(QIcon::fromTheme(QStringLiteral("jdownloader"), QIcon::fromTheme(QStringLiteral("folder-download"))));
    // the One UI text size of the rest of the phone (plasma-settings)
    QFont font = app.font();
    font.setPixelSize(17);
    app.setFont(font);

    QStringList links;
    for (const QString &a : app.arguments().mid(1)) {
        if (a.contains(QLatin1String("://")))
            links << a;
    }

    QQmlApplicationEngine engine;
    JdApi jd(&engine, links);
    engine.rootContext()->setContextProperty(QStringLiteral("jd"), &jd);
    engine.load(QUrl(QStringLiteral("qrc:/qml/Main.qml")));
    if (engine.rootObjects().isEmpty())
        return 1;
    return app.exec();
}

#include "main.moc"
