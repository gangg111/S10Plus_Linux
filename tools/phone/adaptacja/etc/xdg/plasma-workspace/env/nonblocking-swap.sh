# libhybris blokuje eglSwapBuffers przy zgaszonym ekranie: czeka na frame callback,
# ktorego wayfire przy wylaczonym wyjsciu nie wysyla, wiec watek renderu powloki staje
# i ekran nie wraca po wygaszeniu. Z tym Qt uzywa swap interval 0.
export QT_WAYLAND_FORCE_NONBLOCKING_SWAP_SUPPORT=1
