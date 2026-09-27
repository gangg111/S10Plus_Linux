pragma Singleton
import QtQuick

QtObject {
    id: root

    // Opis klawisza:
    //   t     - znak wstawiany tapnieciem
    //   alt   - tablica znakow pod dlugim przytrzymaniem
    //   k     - nazwa klawisza systemowego (Backspace, Enter, Tab, ...)
    //   act   - akcja UI: "shift" | "layer" | "hide"
    //   to    - docelowa warstwa dla act:"layer"
    //   label - etykieta, gdy inna niz t
    //   sp    - pusty odstep o zadanej szerokosci (wciecie rzedu)
    //   rh    - mnoznik wysokosci calego rzedu (czyta go pierwszy element)
    //   w     - szerokosc w jednostkach klawisza (domyslnie 1)
    //   rep   - autorepeat przy przytrzymaniu

    readonly property var letters: [
        // Rzad cyfr jest nizszy od liter: trafia sie w niego rzadziej,
        // a pelne 9 mm zabieraloby jedna piata ekranu.
        [ {t:"1", rh:0.78, alt:["!"]}, {t:"2", alt:["@"]}, {t:"3", alt:["#"]},
          {t:"4", alt:["$"]}, {t:"5", alt:["%"]}, {t:"6", alt:["^"]},
          {t:"7", alt:["&"]}, {t:"8", alt:["*"]}, {t:"9", alt:["("]},
          {t:"0", alt:[")"]} ],
        [ {t:"q"}, {t:"w"}, {t:"e", alt:["ę"]}, {t:"r"}, {t:"t"},
          {t:"y"}, {t:"u"}, {t:"i"}, {t:"o", alt:["ó"]}, {t:"p"} ],
        [ {sp:0.5},
          {t:"a", alt:["ą"]}, {t:"s", alt:["ś"]}, {t:"d"}, {t:"f"}, {t:"g"},
          {t:"h"}, {t:"j"}, {t:"k"}, {t:"l", alt:["ł"]},
          {sp:0.5} ],
        [ {act:"shift", label:"⇧", w:1.5},
          {t:"z", alt:["ż","ź"]}, {t:"x", alt:["ź"]}, {t:"c", alt:["ć"]},
          {t:"v"}, {t:"b"}, {t:"n", alt:["ń"]}, {t:"m"},
          {k:"Backspace", label:"⌫", w:1.5, rep:true} ],
        [ {act:"layer", to:"symbols", label:"?123", w:1.5},
          {t:",", alt:[";"]},
          {t:" ", label:"", w:4.5},
          {t:".", alt:["!","?",":"]},
          {act:"layer", to:"nav", label:"Fn", w:1.0},
          {k:"Enter", label:"⏎", w:1.5} ]
    ]

    readonly property var symbols: [
        [ {t:"1"}, {t:"2"}, {t:"3"}, {t:"4"}, {t:"5"},
          {t:"6"}, {t:"7"}, {t:"8"}, {t:"9"}, {t:"0"} ],
        [ {t:"@"}, {t:"#"}, {t:"$"}, {t:"%"}, {t:"&"},
          {t:"-"}, {t:"+"}, {t:"("}, {t:")"}, {t:"/"} ],
        [ {act:"layer", to:"symbols2", label:"=\\<", w:1.5},
          {t:"*"}, {t:"\""}, {t:"'"}, {t:":"}, {t:";"}, {t:"!"}, {t:"?"},
          {k:"Backspace", label:"⌫", w:1.5, rep:true} ],
        [ {act:"layer", to:"letters", label:"ABC", w:1.5},
          {t:"_"},
          {t:" ", label:"", w:4.5},
          {t:"."},
          {act:"layer", to:"nav", label:"Fn", w:1.0},
          {k:"Enter", label:"⏎", w:1.5} ]
    ]

    // Warstwa operatorow. Trzymamy sie ASCII: uinput wysyla scancody,
    // wiec znak spoza ukladu systemowego (π, €, ™) nie ma jak powstac.
    readonly property var symbols2: [
        [ {t:"~"}, {t:"`"}, {t:"|"}, {t:"^"}, {t:"="},
          {t:"<"}, {t:">"}, {t:"{"}, {t:"}"}, {t:"\\"} ],
        [ {t:"["}, {t:"]"}, {t:"("}, {t:")"}, {t:"+"},
          {t:"-"}, {t:"*"}, {t:"/"}, {t:"%"}, {t:"#"} ],
        [ {act:"layer", to:"symbols", label:"?123", w:1.5},
          {t:"&"}, {t:"$"}, {t:"@"}, {t:"!"}, {t:"?"}, {t:":"}, {t:";"},
          {k:"Backspace", label:"⌫", w:1.5, rep:true} ],
        [ {act:"layer", to:"letters", label:"ABC", w:1.5},
          {t:"_"},
          {t:" ", label:"", w:4.5},
          {t:"."},
          {act:"layer", to:"nav", label:"Fn", w:1.0},
          {k:"Enter", label:"⏎", w:1.5} ]
    ]

    // Warstwa systemowa: strzalki, Esc, funkcyjne — do pracy w TTY.
    readonly property var nav: [
        [ {k:"Esc", label:"Esc"}, {k:"Tab", label:"Tab"},
          {k:"Home", label:"Home"}, {k:"End", label:"End"},
          {k:"PageUp", label:"PgUp"}, {k:"PageDown", label:"PgDn"},
          {k:"Delete", label:"Del"}, {k:"Backspace", label:"⌫", rep:true} ],
        [ {k:"F1", label:"F1"}, {k:"F2", label:"F2"}, {k:"F3", label:"F3"},
          {k:"F4", label:"F4"}, {k:"F5", label:"F5"}, {k:"F6", label:"F6"},
          {k:"F7", label:"F7"}, {k:"F8", label:"F8"} ],
        [ {k:"F9", label:"F9"}, {k:"F10", label:"F10"}, {k:"F11", label:"F11"},
          {k:"F12", label:"F12"},
          {k:"Up", label:"↑", rep:true}, {k:"Down", label:"↓", rep:true},
          {k:"Left", label:"←", rep:true}, {k:"Right", label:"→", rep:true} ],
        [ {act:"layer", to:"letters", label:"ABC", w:1.5},
          {act:"mod", mod:"ctrl", label:"Ctrl", w:1.5},
          {act:"mod", mod:"alt", label:"Alt", w:1.5},
          {t:" ", label:"", w:3.0},
          {k:"Enter", label:"⏎", w:1.5} ]
    ]

    function layer(name) {
        switch (name) {
        case "symbols":  return root.symbols
        case "symbols2": return root.symbols2
        case "nav":      return root.nav
        default:         return root.letters
        }
    }
}
