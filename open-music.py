import threading
from tkinter import filedialog
import yt_dlp
from pathlib import Path
import customtkinter as ctk
import sys
import os
from mutagen.id3 import ID3, TRCK, ID3NoHeaderError

"""
I need functions for the following:

1. determine the type of the youtube url which was provided: single video or url
2. set path for saving the downloaded file
3. function to download the actual file with choices for index-tracking
"""
def get_ffmpeg_path():
    # so if the script is running as a frozen exectuable
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(__file__)
    return base

class SetTrackPostProcessor(yt_dlp.postprocessor.PostProcessor):
    """
    Custom postprocessor that writes the track number using mutagen
    based on playlist_index.
    """

    def run(self, info):
        filepath = info.get("filepath") or info.get("_filename")

        if not filepath:
            return [], info

        track = info.get("playlist_index")
        total = info.get("playlist_count") or info.get("__last_playlist_index")

        if not track:
            return [], info

        try:
            tags = ID3(filepath)
        except ID3NoHeaderError:
            tags = ID3()

        tags.delall("TRCK")

        if total:
            tags.add(TRCK(encoding=3, text=f"{track}/{total}"))
        else:
            tags.add(TRCK(encoding=3, text=str(track)))

        tags.save(filepath, v2_version=3)

        return [], info

def url_type_playlist(url: str) -> bool:
    with yt_dlp.YoutubeDL({"quiet": True}) as ydl:
        if "playlist" in url:
            return True
        info_dict = ydl.extract_info(url, download=False)
    return info_dict.get("_type", "video") == "playlist"

def inspect_metadata(url: str):
    """
    Fetch metadata from yt-dlp without downloading anything.
    Useful for debugging what fields are available.
    """
    with yt_dlp.YoutubeDL({"quiet": False}) as ydl:
        info = ydl.extract_info(url, download=False)

    # If it's a playlist, show the first entry
    if "entries" in info:
        first = info["entries"][0]
        print("\nPLAYLIST DETECTED\n")
        print("playlist_title:", info.get("title"))
        print("playlist_count:", len(info["entries"]))
        print("\nFIRST ENTRY METADATA\n")
        for k, v in first.items():
            print(f"{k}: {v}")
    else:
        print("\nSINGLE VIDEO METADATA\n")
        for k, v in info.items():
            if k in ["title", "playlist_index", "playlist_autonumber"]:
                print(f"{k}: {v}")

def download(url: str, destination: Path, user_use_index: bool = False):
    url_is_playlist = url_type_playlist(url)
    track_index = True if (url_is_playlist and user_use_index) else False
    ffmpeg_path = get_ffmpeg_path()

    if url_is_playlist:
        if track_index:
            outtmpl = f"{destination}/%(playlist_title)s/%(playlist_index)02d - %(title)s.%(ext)s"
        else:
            outtmpl = f"{destination}/%(playlist_title)s/%(title)s.%(ext)s"
    
    else: # is not a playlist
        outtmpl = f"{destination}/%(title)s.%(ext)s"
    # We'll resolve the m3u path once we know the playlist title.
    # We use a mutable container (list) so the inner function can write to it
    # from the enclosing scope — a plain variable wouldn't be reassignable in Python < 3.10
    m3u_path_holder = [None]

    def on_progress(d):
        if d["status"] != "finished":
            return

        info = d.get("info_dict", {})

        # Only write m3u entries for playlist downloads
        if not url_is_playlist:
            return

        # Build the m3u path on the first completed track using the playlist title
        if m3u_path_holder[0] is None:
            playlist_title = info.get("playlist_title", "playlist")
            m3u_dir = destination / playlist_title
            m3u_dir.mkdir(parents=True, exist_ok=True)
            m3u_path_holder[0] = m3u_dir / f"{playlist_title}.m3u"

            # Write the m3u header on first entry
            with open(m3u_path_holder[0], "w", encoding="utf-8") as f:
                f.write("#EXTM3U\n")

        # yt-dlp gives us the pre-conversion filename here, so we swap the extension to .mp3
        raw_filename = d.get("filename", "")
        mp3_filename = Path(raw_filename).with_suffix(".mp3").name

        # Append this track as a relative path so the m3u is portable
        with open(m3u_path_holder[0], "a", encoding="utf-8") as f:
            f.write(f"{mp3_filename}\n")

    ydl_opts = {
        "format": "bestaudio",
        "ffmpeg_location": ffmpeg_path,
        # "verbose": True,
        # "playlist_items": "1-3",  # for testing, only download the first item in a playlist
        "writethumbnail": True,
        "addmetadata": True,
        "parse_metadata": [
            "%(playlist_index)02d:trck",
            "%(playlist_title)s:album",
            "%(uploader)s:artist",
            "%(playlist_uploader)s:album_artist",  # playlist creator as album artist
        ],
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"},
            # embed the downloaded thumbnail as the album cover art
            {"key": "EmbedThumbnail"},            
            # embed metadata (Artist, Title, Date, etc.)
            {"key": "FFmpegMetadata", "add_chapters": True}, 
        ],
        "postprocessor_args": {
            "ffmpegextractaudio": ["-id3v2_version", "3"],
            "ffmpegmetadata": ["-metadata", "track=%(playlist_index)02d"]
        },
        "outtmpl": outtmpl,
        "progress_hooks": [on_progress],
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.add_post_processor(SetTrackPostProcessor(ydl))
        ydl.download([url])


#################################
# CustomTkinter
#################################

class DownloaderApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Setup main window
        self.title("Open-Music")
        self.geometry("600x350")
        ctk.set_appearance_mode("system")
        
        # Default destination path
        self.download_path = Path.home() / "Music"

        # --- UI ELEMENTS ---
        
        # 1. URL Input
        self.url_label = ctk.CTkLabel(self, text="YouTube URL (Video or Playlist):", font=("Arial", 14, "bold"))
        self.url_label.pack(pady=(20, 5), padx=20, anchor="w")
        
        self.url_entry = ctk.CTkEntry(self, width=560, placeholder_text="Paste link here...")
        self.url_entry.pack(pady=5, padx=20)

        # 2. Destination Folder Select
        self.dest_label = ctk.CTkLabel(self, text="Save Destination:", font=("Arial", 14, "bold"))
        self.dest_label.pack(pady=(20, 5), padx=20, anchor="w")

        # Create a frame to hold the path text and the browse button next to each other
        self.path_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.path_frame.pack(fill="x", padx=20, pady=5)

        self.path_display = ctk.CTkLabel(self.path_frame, text=str(self.download_path), text_color="gray")
        self.path_display.pack(side="left")

        self.browse_btn = ctk.CTkButton(self.path_frame, text="Browse...", width=80, command=self.browse_folder)
        self.browse_btn.pack(side="right")

        # 3. Download Button
        self.download_btn = ctk.CTkButton(self, text="Download", height=40, font=("Arial", 16, "bold"), command=self.start_download)
        self.download_btn.pack(pady=(30, 10), padx=20, fill="x")

        # 4. Status Label
        self.status_label = ctk.CTkLabel(self, text="Ready.", text_color="green")
        self.status_label.pack(pady=5)

    def browse_folder(self):
        # Open Windows folder selector
        folder_selected = filedialog.askdirectory(initialdir=self.download_path)
        if folder_selected:
            self.download_path = Path(folder_selected)
            self.path_display.configure(text=str(self.download_path))

    def start_download(self):
        url = self.url_entry.get()
        if not url:
            self.status_label.configure(text="Please enter a URL!", text_color="red")
            return

        # Update UI to show downloading state
        self.status_label.configure(text="Downloading... (Please wait, this may take a while)", text_color="orange")
        self.download_btn.configure(state="disabled") # Prevent clicking twice

        # Run the actual download in a background thread to prevent the GUI from freezing
        thread = threading.Thread(target=self.run_download_thread, args=(url, self.download_path))
        thread.start()

    def run_download_thread(self, url, path):
        try:
            # We assume user wants playlist indexing by default for your use case
            download(url, path)
            
            # Update GUI when done (Safe to do in CustomTkinter)
            self.status_label.configure(text="Download Complete!", text_color="green")
            self.url_entry.delete(0, 'end') # Clear the text box
            
        except Exception as e:
            self.status_label.configure(text=f"Error: {str(e)}", text_color="red")
            print(e)
            
        finally:
            # Re-enable the button regardless of success or failure
            self.download_btn.configure(state="normal")

if __name__ == "__main__":
    app = DownloaderApp()
    app.mainloop()