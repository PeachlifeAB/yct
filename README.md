# ytc

Fetch YouTube transcripts and search for videos from the command line.

## Install

```bash
uv tool install git+https://github.com/PeachlifeAB/yct.git
```

## Usage

### Fetch a transcript

Pass a URL or video ID:

```bash
ytc https://www.youtube.com/watch?v=dQw4w9WgXcQ
ytc dQw4w9WgXcQ
```

Accepts any YouTube URL format — `youtu.be/`, `/shorts/`, `/live/`, `/embed/`, etc.

Multiple inputs from stdin:

```bash
cat urls.txt | ytc
```

### Search videos

```bash
ytc search lex fridman sam altman
```

Returns title, date, URL, channel, and like count for the top results. For URLs only:

```bash
ytc search -q lex fridman sam altman
```

### Channels

Save channels and fetch their transcripts.

**Search for a channel** — returns newline-delimited JSON, ranked by name similarity:

```bash
ytc channels search fireship
```

Each result includes `name`, `id`, `channel_url`, `followers`, `last_video`, and `rank`.

**Save a channel** to `~/.config/ytc/channels.json`:

```bash
ytc channels add UCsBjURrPoezykLs9EqgamOA
```

**Fetch transcripts** from a channel's latest videos — output is newline-delimited JSON:

```bash
ytc channels fetch UCsBjURrPoezykLs9EqgamOA        # last video
ytc channels fetch UCsBjURrPoezykLs9EqgamOA -n 5   # last 5 videos
```

Each record includes `id`, `date`, `likes`, `url`, and `transcript`. If a transcript is unavailable the record still appears with `"transcript": null` and an `"error"` field.

## Shell note

On first run, `ytc` adds a `noglob` alias to your shell config so you can paste YouTube URLs unquoted without zsh/fish glob-expanding the `?` character.

## Built with

- [youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api) — transcript fetching
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) — YouTube search and channel data
