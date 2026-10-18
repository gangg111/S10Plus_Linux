#!/bin/sh
# Dolacza regule otworu aparatu (/usr/share/s10plus/gtk/wyciecie.css) do CSS
# uzytkownika GTK 3 i GTK 4.  GTK czyta wlasny CSS tylko z katalogu domowego,
# wiec robi to autostart sesji; reszta pliku (import colors.css od KDE i
# wlasne reguly) zostaje nietknieta.  Wolane bez argumentow, przy kazdym logowaniu.
IMPORT='@import url("file:///usr/share/s10plus/gtk/wyciecie.css");'
for wersja in gtk-3.0 gtk-4.0; do
	katalog="${XDG_CONFIG_HOME:-$HOME/.config}/$wersja"
	plik="$katalog/gtk.css"
	mkdir -p "$katalog"
	grep -qF "$IMPORT" "$plik" 2>/dev/null && continue
	printf '%s\n' "$IMPORT" >> "$plik"
done
