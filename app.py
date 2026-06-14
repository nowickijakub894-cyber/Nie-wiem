import os
import sys
import json
import urllib.request
import ctypes
import threading

sciezka_projektu = os.path.dirname(os.path.abspath(__file__))
if sciezka_projektu not in os.environ["PATH"]:
    os.environ["PATH"] = sciezka_projektu + os.path.pathsep + os.environ["PATH"]

try:
    myappid = 'moja.aplikacja.ytplayer.v11'
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except:
    pass

import customtkinter as ctk
import yt_dlp
import mpv

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

class ModernMediaPlayer(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.sprawdz_i_pobierz_ytdlp()

        self.mpv_player = mpv.MPV(
            player_operation_mode='cplayer',
            ytdl=True,
            vo='gpu',
            ytdl_raw_options='sub-format=srt,sub-langs="pl,en,auto",write-subs=,write-auto-subs=',
            log_handler=print
        )

        self.kolejka_utworow = []
        self.indeks_aktualnego = -1
        self.is_playing = False
        self.is_loop_enabled = False
        self.plik_bazy = "baza_playlisty.json"
       
        # System playlist
        self.playlisty = {
            "Ulubione": [],
            "Moja Playlista": []
        }
        self.aktywna_playlista = "Ulubione"
        self.menu_otwarte = False

        self.title("YT Media Player v11.0 - Direct Play Edition")
        self.geometry("1250x880")
        self.configure(fg_color="#101014")
        if os.path.exists("ikona.ico"):
            self.wm_iconbitmap("ikona.ico")
        self.protocol("WM_DELETE_WINDOW", self.zamknij_aplikacje)

        # --- MAIN LAYOUT ---
        self.main_layout = ctk.CTkFrame(self, fg_color="transparent")
        self.main_layout.pack(fill="both", expand=True)

        # --- BOCZNE MENU ---
        self.side_menu = ctk.CTkFrame(self.main_layout, fg_color="#16161e", border_width=1, border_color="#24283b", width=0)
        self.side_menu.pack(side="left", fill="y", padx=0, pady=0)
        self.side_menu.pack_propagate(False)
       
        self.playlist_title_lbl = ctk.CTkLabel(self.side_menu, text="🗂 TWOJE PLAYLISTY", font=("Arial", 14, "bold"), text_color="#ff9e64")
        self.playlist_title_lbl.pack(pady=(20, 10))
        
        self.new_playlist_entry = ctk.CTkEntry(self.side_menu, placeholder_text="Nazwa playlisty...", height=35, fg_color="#1a1b26")
        self.new_playlist_entry.pack(fill="x", padx=15, pady=5)
       
        self.btn_add_playlist = ctk.CTkButton(self.side_menu, text="Utwórz Playlistę", height=35, font=("Arial", 12, "bold"), command=self.stworz_nowa_playliste)
        self.btn_add_playlist.pack(fill="x", padx=15, pady=(0, 15))
        
        self.playlist_scroll_list = ctk.CTkScrollableFrame(self.side_menu, fg_color="transparent")
        self.playlist_scroll_list.pack(fill="both", expand=True, padx=5, pady=5)

        # --- PANEL CENTRALNY ---
        self.center_content = ctk.CTkFrame(self.main_layout, fg_color="transparent")
        self.center_content.pack(side="right", fill="both", expand=True)

        # --- GÓRNY PANEL ---
        self.top_frame = ctk.CTkFrame(self.center_content, fg_color="transparent")
        self.top_frame.pack(fill="x", padx=30, pady=(20, 10))
        
        self.btn_menu = ctk.CTkButton(self.top_frame, text="☰", width=45, height=45, font=("Arial", 20, "bold"),
                                      fg_color="#16161e", hover_color="#24283b", command=self.przepnij_widok_menu)
        self.btn_menu.pack(side="left", padx=(0, 10))

        self.search_entry = ctk.CTkEntry(self.top_frame, placeholder_text="Wklej link lub wpisz tytuł piosenki...",
                                         height=45, fg_color="#16161e", border_color="#24283b", corner_radius=10)
        self.search_entry.pack(side="left", expand=True, fill="x", padx=(0, 15))
        self.search_entry.bind("<Return>", lambda e: self.uruchom_wyszukiwanie_w_tle())

        self.btn_search = ctk.CTkButton(self.top_frame, text="Szukaj i Dodaj", width=140, height=45,
                                        font=("Arial", 14, "bold"), corner_radius=10, command=self.uruchom_wyszukiwanie_w_tle)
        self.btn_search.pack(side="right")

        self.status_label = ctk.CTkLabel(self.center_content, text="Status: Gotowy", font=("Arial", 12, "italic"), text_color="#71ab7a")
        self.status_label.pack(pady=(0, 10))

        # --- VIDEO FRAME ---
        self.video_frame = ctk.CTkFrame(self.center_content, height=320, fg_color="#000000", corner_radius=14,
                                        border_width=1, border_color="#22c55e")
        self.video_frame.pack(fill="x", padx=30, pady=10)
        self.video_frame.pack_propagate(False)

        self.audio_mode_label = ctk.CTkLabel(self.video_frame, text="🎵 TRYB AUDIO READY\nKliknij dowolny utwór na playliście, aby zacząć słuchać",
                                             font=("Arial", 16, "bold"), text_color="#22c55e", justify="center")
        self.audio_mode_label.place(relx=0.5, rely=0.5, anchor="center")
        self.mpv_player.wid = str(self.video_frame.winfo_id())

        # --- CONTROLS ---
        self.controls_frame = ctk.CTkFrame(self.center_content, fg_color="#16161e", corner_radius=12, border_width=1, border_color="#24283b")
        self.controls_frame.pack(fill="x", padx=30, pady=15, ipady=10)

        self.timeline_frame = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.timeline_frame.pack(fill="x", padx=20, pady=(10, 5))
        self.time_start = ctk.CTkLabel(self.timeline_frame, text="00:00", font=("Arial", 12, "bold"), text_color="#22c55e")
        self.time_start.pack(side="left", padx=(0, 10))
        self.timeline_slider = ctk.CTkSlider(self.timeline_frame, from_=0, to=100, height=8, fg_color="#1a1b26", progress_color="#22c55e")
        self.timeline_slider.set(0)
        self.timeline_slider.pack(side="left", expand=True, fill="x")
        self.time_end = ctk.CTkLabel(self.timeline_frame, text="--:--", font=("Arial", 12), text_color="#71ab7a")
        self.time_end.pack(side="right", padx=(10, 0))

        self.buttons_row = ctk.CTkFrame(self.controls_frame, fg_color="transparent")
        self.buttons_row.pack(fill="x", padx=20, pady=5)
        self.playback_buttons = ctk.CTkFrame(self.buttons_row, fg_color="transparent")
        self.playback_buttons.pack(side="left", expand=True, anchor="center", padx=(100, 0))

        self.btn_prev = ctk.CTkButton(self.playback_buttons, text="⏮", width=45, height=35, font=("Arial", 14), fg_color="#24283b", command=self.poprzedni_utwor)
        self.btn_prev.pack(side="left", padx=5)
        self.btn_play = ctk.CTkButton(self.playback_buttons, text="▶ PLAY", width=120, height=35, font=("Arial", 12, "bold"), command=self.przepnij_play_pause)
        self.btn_play.pack(side="left", padx=5)
        self.btn_next = ctk.CTkButton(self.playback_buttons, text="⏭", width=45, height=35, font=("Arial", 14), fg_color="#24283b", command=self.nastepny_utwor)
        self.btn_next.pack(side="left", padx=5)
        self.btn_loop = ctk.CTkButton(self.playback_buttons, text="🔁 LOOP: WYŁ", width=110, height=35, font=("Arial", 11, "bold"),
                                      fg_color="#24283b", text_color="#71ab7a", command=self.przepnij_loop)
        self.btn_loop.pack(side="left", padx=5)

        self.volume_frame = ctk.CTkFrame(self.buttons_row, fg_color="transparent")
        self.volume_frame.pack(side="right", anchor="center")
        self.volume_icon = ctk.CTkLabel(self.volume_frame, text="🔊", font=("Arial", 14), text_color="#22c55e")
        self.volume_icon.pack(side="left", padx=5)
        self.volume_slider = ctk.CTkSlider(self.volume_frame, from_=0, to=100, width=120, height=8, progress_color="#10b981", command=self.zmien_glosnosc)
        self.volume_slider.set(70)
        self.volume_slider.pack(side="left", padx=5)
        self.mpv_player.volume = 70

        # --- DOLNY UKŁAD ---
        self.bottom_grid = ctk.CTkFrame(self.center_content, fg_color="transparent")
        self.bottom_grid.pack(fill="both", expand=True, padx=30, pady=(10, 20))

        self.queue_container = ctk.CTkScrollableFrame(self.bottom_grid, label_text="🎧 KOLEJKA ODTWARZANIA (z aktualnej playlisty)",
                                                       label_text_color="#22c55e", fg_color="#16161e", border_width=1, border_color="#24283b", corner_radius=12)
        self.queue_container.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self.library_container = ctk.CTkScrollableFrame(self.bottom_grid, label_text="📁 UTWORY W PLAYLIŚCIE",
                                                         label_text_color="#9ece6a", fg_color="#16161e", border_width=1, border_color="#24283b", corner_radius=12)
        self.library_container.pack(side="right", fill="both", expand=True, padx=(10, 0))

        @self.mpv_player.event_callback('end-file')
        def on_end_file(event):
            reason = getattr(event, 'reason', None)
            if reason == 0 or reason == 'eof':
                if self.is_loop_enabled:
                    self.after(0, lambda: self.ustaw_i_graj(self.indeks_aktualnego))
                else:
                    self.after(0, self.nastepny_utwor)

        self.sprawdzaj_pozycje_suwaka()
        self.wczytaj_baze_danych()

        # Automatyczne odtwarzanie z playlisty "Ulubione"
        if self.playlisty["Ulubione"]:
            self.odtworz_bezposrednio_z_playlisty(self.playlisty["Ulubione"][0]["url"])

    # ====================== METODY ======================

    def przepnij_widok_menu(self):
        if self.menu_otwarte:
            self.side_menu.configure(width=0)
            self.btn_menu.configure(fg_color="#16161e", text="☰")
            self.menu_otwarte = False
        else:
            self.side_menu.configure(width=260)
            self.btn_menu.configure(fg_color="#22c55e", text="✕")
            self.menu_otwarte = True

    def sprawdz_i_pobierz_ytdlp(self):
        cel_sciezka = os.path.join(sciezka_projektu, "yt-dlp.exe")
        if not os.path.exists(cel_sciezka):
            try:
                url_ytdlp = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
                urllib.request.urlretrieve(url_ytdlp, cel_sciezka)
            except Exception as e:
                print(f"Błąd pobierania yt-dlp: {e}")

    def aktualizuj_podglad_odtwarzania(self):
        liczba = len(self.playlisty.get(self.aktywna_playlista, []))
        tekst = f"🎵 TRYB AUDIO ACTIVE\n\n💿 Odtwarzanie z playlisty: {self.aktywna_playlista}\n📊 Utworów: {liczba}"
        self.audio_mode_label.configure(text=tekst)

    def odtworz_bezposrednio_z_playlisty(self, klikniety_url):
        for widget in self.queue_container.winfo_children():
            widget.destroy()
        self.kolejka_utworow.clear()

        docelowy_indeks = 0
        lista = self.playlisty.get(self.aktywna_playlista, [])

        for i, utw in enumerate(lista):
            nr = i + 1
            queue_frame = ctk.CTkFrame(self.queue_container, fg_color="#1f2335", height=45, corner_radius=8)
            queue_frame.pack(fill="x", pady=4, padx=5)
            queue_frame.pack_propagate(False)

            lbl = ctk.CTkLabel(queue_frame, text=f"{nr}. {utw['tytul'][:45]}", font=("Arial", 12, "bold"),
                               text_color="#c0caf5", cursor="hand2")
            lbl.pack(side="left", padx=15, anchor="w")

            self.kolejka_utworow.append({'tytul': utw['tytul'], 'url': utw['url'], 'frame': queue_frame, 'label': lbl})
            lbl.bind("<Button-1>", lambda e, idx=i: self.ustaw_i_graj(idx))
            ctk.CTkButton(queue_frame, text="✕", width=32, height=32, fg_color="#f43f5e",
                          command=lambda f=queue_frame: self.usun_z_kolejki(f)).pack(side="right", padx=6, pady=6)

            if utw['url'] == klikniety_url:
                docelowy_indeks = i

        if self.kolejka_utworow:
            self.ustaw_i_graj(docelowy_indeks)

    def ustaw_i_graj(self, indeks):
        if not (0 <= indeks < len(self.kolejka_utworow)):
            return
        if 0 <= self.indeks_aktualnego < len(self.kolejka_utworow):
            try:
                self.kolejka_utworow[self.indeks_aktualnego]['frame'].configure(fg_color="#1f2335")
            except:
                pass

        self.indeks_aktualnego = indeks
        self.kolejka_utworow[indeks]['frame'].configure(fg_color="#22c55e")
        self.mpv_player.play(self.kolejka_utworow[indeks]['url'])
        self.is_playing = True
        self.btn_play.configure(text="⏸ PAUSE")
        self.aktualizuj_podglad_odtwarzania()

    def stworz_nowa_playliste(self):
        nazwa = self.new_playlist_entry.get().strip()
        if not nazwa or nazwa in self.playlisty:
            return
        self.playlisty[nazwa] = []
        self.new_playlist_entry.delete(0, 'end')
        self.aktywna_playlista = nazwa
        self.odswiez_widok_playlist_i_utworow()
        self.zapisz_baze_danych()

    def usun_playliste(self, nazwa):
        if nazwa == "Ulubione" or len(self.playlisty) <= 1:
            return
        del self.playlisty[nazwa]
        if self.aktywna_playlista == nazwa:
            self.aktywna_playlista = list(self.playlisty.keys())[0]
        self.odswiez_widok_playlist_i_utworow()
        self.zapisz_baze_danych()

    def wybierz_playliste(self, nazwa):
        self.aktywna_playlista = nazwa
        self.odswiez_widok_playlist_i_utworow()

    def odswiez_widok_playlist_i_utworow(self):
        for widget in self.playlist_scroll_list.winfo_children():
            widget.destroy()

        for nazwa in self.playlisty.keys():
            jest_aktywna = (nazwa == self.aktywna_playlista)
            ikona = "❤️ " if nazwa == "Ulubione" else ("💿 " if jest_aktywna else "📁 ")

            p_frame = ctk.CTkFrame(self.playlist_scroll_list, fg_color="#1f2335" if jest_aktywna else "transparent", height=40)
            p_frame.pack(fill="x", pady=3, padx=2)
            p_frame.pack_propagate(False)

            btn_sel = ctk.CTkButton(p_frame, text=ikona + nazwa, fg_color="transparent",
                                    text_color="#22c55e" if jest_aktywna else "#787c99",
                                    font=("Arial", 12, "bold" if jest_aktywna else "normal"),
                                    anchor="w", hover=False,
                                    command=lambda n=nazwa: self.wybierz_playliste(n))
            btn_sel.pack(side="left", fill="both", expand=True, padx=5)

            if nazwa != "Ulubione" and len(self.playlisty) > 1:
                btn_del = ctk.CTkButton(p_frame, text="🗑", width=28, fg_color="#f43f5e",
                                        command=lambda n=nazwa: self.usun_playliste(n))
                btn_del.pack(side="right", padx=5, pady=4)

        for widget in self.library_container.winfo_children():
            widget.destroy()
        self.library_container._label.configure(text=f"📁 UTWORY W: {self.aktywna_playlista.upper()}")

        for utw in self.playlisty.get(self.aktywna_playlista, []):
            self.wyswietl_utwor_w_bibliotece_gui(utw['tytul'], utw['url'])

    def zapisz_baze_danych(self):
        try:
            dane_kolejki = [{'tytul': u['tytul'], 'url': u['url']} for u in self.kolejka_utworow]
            struktura = {
                'playlisty': self.playlisty,
                'aktywna_playlista': self.aktywna_playlista,
                'kolejka': dane_kolejki
            }
            with open(self.plik_bazy, "w", encoding="utf-8") as f:
                json.dump(struktura, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"Błąd zapisu: {e}")

    def wczytaj_baze_danych(self):
        if not os.path.exists(self.plik_bazy):
            self.odswiez_widok_playlist_i_utworow()
            return
        try:
            with open(self.plik_bazy, "r", encoding="utf-8") as f:
                paczka = json.load(f)

            self.playlisty = paczka.get('playlisty', {"Ulubione": [], "Moja Playlista": []})
            self.aktywna_playlista = paczka.get('aktywna_playlista', "Ulubione")

            if "Ulubione" not in self.playlisty:
                self.playlisty["Ulubione"] = []

            self.odswiez_widok_playlist_i_utworow()

            for u in paczka.get('kolejka', []):
                nr = len(self.kolejka_utworow) + 1
                queue_frame = ctk.CTkFrame(self.queue_container, fg_color="#1f2335", height=45, corner_radius=8)
                queue_frame.pack(fill="x", pady=4, padx=5)
                queue_frame.pack_propagate(False)
                lbl = ctk.CTkLabel(queue_frame, text=f"{nr}. {u['tytul'][:45]}", font=("Arial", 12, "bold"),
                                   text_color="#c0caf5", cursor="hand2")
                lbl.pack(side="left", padx=15, anchor="w")
                self.kolejka_utworow.append({'tytul': u['tytul'], 'url': u['url'], 'frame': queue_frame, 'label': lbl})
                lbl.bind("<Button-1>", lambda e, idx=len(self.kolejka_utworow)-1: self.ustaw_i_graj(idx))
                ctk.CTkButton(queue_frame, text="✕", width=32, height=32, fg_color="#f43f5e",
                              command=lambda f=queue_frame: self.usun_z_kolejki(f)).pack(side="right", padx=6, pady=6)
        except Exception as e:
            print(f"Błąd odczytu bazy: {e}")
            self.odswiez_widok_playlist_i_utworow()

    def dodaj_do_aktywnej_playlisty(self, tytul, url):
        self.playlisty[self.aktywna_playlista].append({'tytul': tytul, 'url': url})
        self.wyswietl_utwor_w_bibliotece_gui(tytul, url)
        self.status_label.configure(text="Status: Gotowe!")
        self.search_entry.delete(0, 'end')
        self.zapisz_baze_danych()

    def wyswietl_utwor_w_bibliotece_gui(self, tytul, url):
        item_frame = ctk.CTkFrame(self.library_container, fg_color="#1f2335", height=45, corner_radius=8)
        item_frame.pack(fill="x", pady=4, padx=5)
        item_frame.pack_propagate(False)

        lbl_click = ctk.CTkLabel(item_frame, text=f"▶ {tytul[:55]}", font=("Arial", 12, "bold"),
                                 text_color="#a9b1d6", cursor="hand2")
        lbl_click.pack(side="left", padx=15, anchor="w")
        lbl_click.bind("<Button-1>", lambda e: self.odtworz_bezposrednio_z_playlisty(url))

        def usun_utwor():
            if self.aktywna_playlista in self.playlisty:
                self.playlisty[self.aktywna_playlista] = [u for u in self.playlisty[self.aktywna_playlista] if u['url'] != url]
            item_frame.destroy()
            self.zapisz_baze_danych()

        ctk.CTkButton(item_frame, text="🗑", width=32, height=32, fg_color="#f43f5e",
                      command=usun_utwor).pack(side="right", padx=(0, 6), pady=6)

    def usun_z_kolejki(self, frame):
        for i, u in enumerate(self.kolejka_utworow):
            if u['frame'] == frame:
                self.kolejka_utworow.pop(i)
                break
        frame.destroy()
        for i, u in enumerate(self.kolejka_utworow):
            u['label'].configure(text=f"{i+1}. {u['tytul'][:45]}")
        self.zapisz_baze_danych()

    def przepnij_play_pause(self):
        if self.indeks_aktualnego == -1 and self.kolejka_utworow:
            self.ustaw_i_graj(0)
            return
        if self.indeks_aktualnego == -1:
            return
        self.is_playing = not self.is_playing
        self.mpv_player.pause = not self.is_playing
        self.btn_play.configure(text="⏸ PAUSE" if self.is_playing else "▶ PLAY")
        self.aktualizuj_podglad_odtwarzania()

    def nastepny_utwor(self):
        if self.kolejka_utworow:
            self.ustaw_i_graj((self.indeks_aktualnego + 1) % len(self.kolejka_utworow))

    def poprzedni_utwor(self):
        if self.kolejka_utworow:
            self.ustaw_i_graj((self.indeks_aktualnego - 1) % len(self.kolejka_utworow))

    def przepnij_loop(self):
        self.is_loop_enabled = not self.is_loop_enabled
        self.btn_loop.configure(
            fg_color="#22c55e" if self.is_loop_enabled else "#24283b",
            text_color="#000" if self.is_loop_enabled else "#71ab7a",
            text="🔁 LOOP: WŁ" if self.is_loop_enabled else "🔁 LOOP: WYŁ"
        )

    def zmien_glosnosc(self, v):
        self.mpv_player.volume = int(float(v))

    def uruchom_wyszukiwanie_w_tle(self):
        fraza = self.search_entry.get().strip()
        if not fraza:
            return
        self.status_label.configure(text="Status: Szukanie...")
        threading.Thread(target=self.pobierz_info_z_yt, args=(fraza,), daemon=True).start()

    def pobierz_info_z_yt(self, fraza):
        ydl_opts = {'format': 'best', 'default_search': 'ytsearch1', 'noplaylist': True, 'quiet': True}
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(fraza, download=False)
                video_data = info['entries'][0] if 'entries' in info else info
                self.after(0, lambda: self.dodaj_do_aktywnej_playlisty(
                    video_data.get('title', 'Nieznany utwór'),
                    video_data.get('webpage_url', fraza)
                ))
        except:
            self.after(0, lambda: self.status_label.configure(text="Błąd wyszukiwania."))

    def sprawdzaj_pozycje_suwaka(self):
        try:
            p = self.mpv_player.time_pos
            d = self.mpv_player.duration
            if p and d:
                self.time_start.configure(text=f"{int(p)//60:02d}:{int(p)%60:02d}")
                self.time_end.configure(text=f"{int(d)//60:02d}:{int(d)%60:02d}")
                self.timeline_slider.set((p / d) * 100)
        except:
            pass
        self.after(500, self.sprawdzaj_pozycje_suwaka)

    def zamknij_aplikacje(self):
        self.zapisz_baze_danych()
        try:
            self.mpv_player.terminate()
        except:
            pass
        self.destroy()

if __name__ == "__main__":
    app = ModernMediaPlayer()
    app.mainloop()