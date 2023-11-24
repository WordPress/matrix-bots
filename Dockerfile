FROM dock.mau.dev/maubot/maubot:v0.4.2

# Custom plugins.
ADD build /data/plugins

# Third-party plugins.
ADD https://github.com/maubot/github/releases/download/v0.1.2/xyz.maubot.github-v0.1.2.mbp /data/plugins/
ADD https://github.com/maubot/rss/releases/download/v0.3.2/xyz.maubot.rss-v0.3.2.mbp /data/plugins/
