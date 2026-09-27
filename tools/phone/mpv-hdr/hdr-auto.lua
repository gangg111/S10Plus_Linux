-- Wlacza profil [hdr] dla plikow PQ (HDR10, HDR10+) i HLG, zanim mpv
-- utworzy wyjscie wideo, i przywraca ustawienia SDR dla pozostalych.
-- Krzywa przejscia z naglowka strumienia przez ffprobe: video-params
-- znane sa dopiero po zdekodowaniu klatki, a zmiana vo wtedy to druga
-- inicjalizacja wyjscia.
local hdr_wlaczony = false

local function krzywa(sciezka)
	local r = mp.command_native({
		name = "subprocess", capture_stdout = true, playback_only = false,
		args = { "ffprobe", "-v", "error", "-select_streams", "v:0",
		         "-show_entries", "stream=color_transfer", "-of", "csv=p=0", sciezka },
	})
	if not r or r.status ~= 0 then
		return nil
	end
	return (r.stdout or ""):match("^%s*(.-)%s*$")
end

mp.add_hook("on_load", 50, function()
	local sciezka = mp.get_property("path")
	if not sciezka then
		return
	end
	local k = krzywa(sciezka)
	local hdr = k == "smpte2084" or k == "arib-std-b67"
	mp.msg.info(string.format("krzywa przejscia %s, HDR %s", tostring(k), hdr and "tak" or "nie"))
	if hdr and not hdr_wlaczony then
		mp.commandv("apply-profile", "hdr")
		hdr_wlaczony = true
	elseif not hdr and hdr_wlaczony then
		mp.commandv("apply-profile", "hdr", "restore")
		hdr_wlaczony = false
	end
end)
