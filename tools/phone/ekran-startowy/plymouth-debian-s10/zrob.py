# Motyw plymouth debian-s10 z motywu droidian: sekcje Logo i Refresh zastapione
# pelnoekranowym obrazem ostatniej klatki S-Boota (logo.jpg z up_param) w (0,0), 1:1,
# bez zanikania i pulsowania; okno hasla, pasek aktualizacji i komunikaty bez zmian.
import sys

src, dst = sys.argv[1], sys.argv[2]
s = open(src, encoding="utf-8").read()
a = s.index("#----------------------------------------- Logo")
b = s.index("#----------------------------------------- Dialogue")
nowe = """#----------------------------------------- Ekran --------------------------------

# Ten sam obraz, ktory S-Boot zostawia na panelu przed startem jadra (logo.jpg,
# 1440x3040, rysowany od (0,0)); narysowany 1:1 w tym samym miejscu nie zmienia
# ani jednego piksela logo przy przejsciu z S-Boota do plymouth.
ekran.image = Image("ekran.png");
if (ekran.image.GetWidth() != Window.GetWidth() || ekran.image.GetHeight() != Window.GetHeight())
    ekran.image = ekran.image.Scale(Window.GetWidth(), Window.GetHeight());
ekran.sprite = Sprite(ekran.image);
ekran.sprite.SetPosition(0, 0, -10);
ekran.sprite.SetOpacity(1);

Window.SetBackgroundTopColor(0, 0, 0);
Window.SetBackgroundBottomColor(0, 0, 0);

"""
s = s[:a] + nowe + s[b:]
assert "glowing" not in s and "Plymouth.SetRefreshFunction" not in s
open(dst, "w", encoding="utf-8", newline="\n").write(s)
open(dst.rsplit("/", 1)[0] + "/debian-s10.plymouth", "w", newline="\n").write(
    "[Plymouth Theme]\nName=Debian S10+\nDescription=Ostatnia klatka S-Boota z logo Debiana\nModuleName=script\n\n"
    "[script]\nImageDir=/usr/share/plymouth/themes/debian-s10\n"
    "ScriptFile=/usr/share/plymouth/themes/debian-s10/debian-s10.script\n")
print("ok", len(s.splitlines()), "linii")
