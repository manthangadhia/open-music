# `open-music`

[Click here to download a windows executable version of this app.](https://github.com/manthangadhia/open-music/download/open-music.exe)

And otherwise you can copy this repository and run `open-music.py`, using `conda` as your package manager, or [`pixi` as I do](https://pixi.prefix.dev/latest/tutorials/import/#conda-env-format).

Note: If you want to run this via venv and use pip you can use the `requirements.txt`, but then you will have to install `ffmpeg` binaries separately onto your computer.

## What `open-music` does
You can download high quality mp3 files off of YouTube and YouTube Music in the directory of your choice by simply providing a URL to that song/list. 

You can download single songs/videos, or entire playlists. In the case of playlists, they will be downloaded with "cover art" which is the thumbnail of the first song on the playlist, however you can update this if you wish by simply updating the jpg in the downloaded folder. (Every audio file has its thumbnail embedded as metadata). Finally, the playlist will also be downloaded with a [`.m3u` file](https://en.wikipedia.org/wiki/M3U) which tracks the order of songs/videos in the provided playlist and as long as this file exists in the folder with the music, transfering the folder to any music app will autorecognise the playlist.