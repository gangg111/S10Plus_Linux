// S10Breeze: Breeze widget style for the Galaxy S10+ front camera hole.
//
// With the shell panels auto-hidden a maximized window covers the whole portrait
// screen and the camera hole sits over its top right corner (from x = 367 pt,
// down to y = 52 pt).  A menu bar or a horizontal tool bar that ends on that
// corner gets a right margin, so its last items and the overflow arrow end
// before the hole; the window itself is not moved.  The same rule lives in the
// Kirigami header and the Breeze QML tool bar (qml-oneui.diff).
//
// Selected for every Qt 6 widget application with QT_STYLE_OVERRIDE=S10Breeze
// (/etc/xdg/plasma-workspace/env/s10-style.sh).

#include <QEvent>
#include <QMenuBar>
#include <QPointer>
#include <QProxyStyle>
#include <QScreen>
#include <QStyleFactory>
#include <QStylePlugin>
#include <QTimer>
#include <QToolBar>
#include <QWindow>

namespace
{
const int HOLE_LEFT = 367;
const int HOLE_BOTTOM = 52;
const char *ORIGINAL_MARGINS = "_s10_margins";
const char *SPACER = "_s10_camera_spacer";

// Width to keep free at the right end of w, 0 when w does not reach the hole.
int cameraInset(QWidget *w)
{
    QWidget *win = w->window();
    QScreen *screen = win->screen();
    if (!screen || !w->isVisible()) {
        return 0;
    }
    const QSize s = screen->size();
    // a window shortened from the bottom (on-screen keyboard) still starts under
    // the hole; only a small difference means the status bar is shown above it
    const int d = s.height() - win->height();
    if (s.width() >= s.height() || win->width() != s.width()
        || (d > 1 && d < 60) || win->height() < s.height() / 3) {
        return 0;
    }
    const QPoint p = w->mapTo(win, QPoint(w->width(), 0));
    if (p.x() < win->width() - 1 || p.y() > HOLE_BOTTOM) {
        return 0;
    }
    return qMax(0, win->width() - HOLE_LEFT);
}

void applyToolBar(QToolBar *bar)
{
    if (bar->orientation() != Qt::Horizontal) {
        return;
    }
    QVariant v = bar->property(ORIGINAL_MARGINS);
    if (!v.isValid()) {
        v = QVariant::fromValue(bar->contentsMargins());
        bar->setProperty(ORIGINAL_MARGINS, v);
    }
    QMargins m = v.value<QMargins>();
    m.setRight(m.right() + cameraInset(bar));
    if (bar->contentsMargins() != m) {
        bar->setContentsMargins(m);
    }
}

void applyMenuBar(QMenuBar *bar)
{
    QWidget *corner = bar->cornerWidget(Qt::TopRightCorner);
    if (corner && !corner->property(SPACER).toBool()) {
        return; // the application has its own corner widget
    }
    const int inset = cameraInset(bar);
    if (inset == 0) {
        if (corner) {
            bar->setCornerWidget(nullptr, Qt::TopRightCorner);
            corner->deleteLater();
        }
        return;
    }
    if (!corner) {
        corner = new QWidget(bar);
        corner->setProperty(SPACER, true);
        corner->setAttribute(Qt::WA_TransparentForMouseEvents);
        bar->setCornerWidget(corner, Qt::TopRightCorner);
        corner->show();
    }
    if (corner->width() != inset) {
        corner->setFixedSize(inset, 1);
        bar->adjustSize();
        bar->updateGeometry();
    }
}

class Watcher : public QObject
{
public:
    using QObject::QObject;

    void watch(QWidget *w)
    {
        w->installEventFilter(this);
        schedule(w);
    }

    bool eventFilter(QObject *o, QEvent *e) override
    {
        switch (e->type()) {
        case QEvent::Show:
        case QEvent::Resize:
        case QEvent::Move:
        case QEvent::ParentChange:
            schedule(static_cast<QWidget *>(o));
            break;
        default:
            break;
        }
        return false;
    }

private:
    // after the event: the bar's position in the window is final only then,
    // and changing its margins from inside its own resize would recurse
    void schedule(QWidget *w)
    {
        QPointer<QWidget> guard(w);
        QTimer::singleShot(0, this, [guard] {
            if (!guard) {
                return;
            }
            if (auto *bar = qobject_cast<QToolBar *>(guard.data())) {
                applyToolBar(bar);
            } else if (auto *bar = qobject_cast<QMenuBar *>(guard.data())) {
                applyMenuBar(bar);
            }
        });
    }
};

class S10Style : public QProxyStyle
{
public:
    S10Style()
        : QProxyStyle(QStyleFactory::create(QStringLiteral("Breeze")))
        , m_watcher(new Watcher(this))
    {
    }

    void polish(QWidget *w) override
    {
        QProxyStyle::polish(w);
        if (qobject_cast<QToolBar *>(w) || qobject_cast<QMenuBar *>(w)) {
            m_watcher->watch(w);
        }
    }

    void unpolish(QWidget *w) override
    {
        w->removeEventFilter(m_watcher);
        QProxyStyle::unpolish(w);
    }

    // keep the other overloads (QApplication *, QPalette &) visible
    using QProxyStyle::polish;
    using QProxyStyle::unpolish;

private:
    Watcher *m_watcher;
};
}

class S10StylePlugin : public QStylePlugin
{
    Q_OBJECT
    Q_PLUGIN_METADATA(IID QStyleFactoryInterface_iid FILE "s10style.json")

public:
    QStyle *create(const QString &key) override
    {
        if (key.compare(QLatin1String("S10Breeze"), Qt::CaseInsensitive) == 0) {
            return new S10Style;
        }
        return nullptr;
    }
};

#include "s10style.moc"
