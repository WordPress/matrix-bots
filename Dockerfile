FROM dock.mau.dev/maubot/maubot:v0.4.2 as build

WORKDIR /source
ADD plugins /source/plugins

RUN apk add bash git

# Build all custom plugins.
RUN <<-EOF
    set -e
    cd /source || exit 1

    rm -rf build remote-plugins
    mkdir -p build remote-plugins

    # Pull custom plugins from remote repos.
    # Note these are not third-party plugins, but plugins we have forked.
    # Third-party plugins are defined later in this Dockerfile.
    git clone https://github.com/Automattic/maubot-github.git remote-plugins/github

    ## Build remote custom plugins.
    for PLUGIN in ./remote-plugins/*/; do
      mbc build --output ./build/ "$PLUGIN"
    done

    # Build local custom plugins.
    for PLUGIN in ./plugins/*/; do
      mbc build --output ./build/ "$PLUGIN"
    done

    rm -rf ./plugins/example
EOF

FROM dock.mau.dev/maubot/maubot:v0.4.2

# Need a fix made in mautrix v0.20.3 which isn't included in maubot:v0.4.2
RUN pip install --upgrade mautrix

# Custom plugins.
COPY --from=build /source/build /data/plugins

# Third-party plugins.
ADD https://github.com/maubot/rss/releases/download/v0.3.2/xyz.maubot.rss-v0.3.2.mbp /data/plugins/
