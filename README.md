# matrix-bots-wporg
The `community.wordpress.org` Matrix server relies on bots (non-human users) that perform a variety of tasks. Bots can react to messages posted on Matrix, and/or post to Matrix whenever _something_ happens.

Bots run in a _bot engine_ called [Maubot](https://maubot.xyz), which provides an Admin UI through which bots can be created and configured. Maubot bots are implemented in Python, and are known as _Plugins_. There is an [ecosystem of existing plugins](https://plugins.mau.bot/) for Maubot, and custom plugins can be implemented as well.

This repository provides the following:

1. Documentation on how to [configure bots through Maubot's Admin UI](#configuring-bots)
2. The source code for [custom plugins](#custom-plugins) used in `community.wordpress.org`
3. [Local development environment](#development-environment) to test, modify and create plugins
4. Automation to produce the [Docker image](#docker-image) for `community.wordpress.org`'s Maubot instance
5. Documentation on how to [redeploy](#deploying) Maubot so that it uses the latest docker image

## Configuring bots
Bots are configured through an Admin UI that is available to server maintainers. You can get a replica of that UI in your local machine, see [development environment](#development-environment) for instructions.

To effectively use the Admin UI, it's important to understand a few Maubot concepts. A Maubot bot is achieved by combining the following three _things_:

- **Plugin**: a Python module that implements the logic of the bot.
- **Client**: the Matrix user that the bot will use to post to Matrix, and to receive messages from Matrix.
- **Instance**: an instance ties a Plugin to a Client, and allows passing configuration to the Plugin. There can be multiple instances of the same Plugin, each potentially using a different Client, and specific configuration.

## Using Maubot's CLI
> To use Maubot's CLI, you first need to set up a [development environment](#development-environment).

Certain operations are easier to do through [Maubot's CLI](https://docs.mau.fi/maubot/usage/cli/index.html) than through the Admin UI. An example of this is creating clients, since it's not possible to automatically retrieve an access token when creating a client through the Admin UI, but the CLI is capable of doing so.

You can access Maubot's CLI with:

```shell
bin/mbc
```

### Login

When using the CLI, the first step is typically to log in to a Maubot instance, so that the CLI can control said instance. As part of the setup process of the development environment, the CLI has already been logged in to the local Maubot instance (`wporg-local`).

However, you can also log in to the production instance (provided you're a server maintainer):

```shell
bin/mbc login \
  --server https://example.com \
  --username foo \
  --alias wporg-prod
```

### Creating clients
TODO

## Development environment
You can set up a local development environment that allows you to do the following:

1. Run a local instance of Maubot, along with a homeserver and a Matrix client. This is useful to test existing plugins or develop new ones.
2. Use the [Maubot CLI](#maubots-cli) to talk to both the local and production Maubot instances. Note the production instance is only available to server maintainers.

### Setup
Start by cloning the repository:

```shell
git clone git@github.com:Automattic/matrix-bots-wporg.git
cd matrix-bots-wporg
```

Do initial setup:

```shell
make
```

From the repo root, run:

```shell
docker compose up
```

The first time you do this, Maubot will likely fail to start due to not being able to connect to Postgres. To fix this, wait for the `matrix-bots-wporg-synapse` container to say `No more background updates`, then restart all containers:

```shell
# ctrl-c to stop all containers, then:
docker compose up
```

Finally, run the setup script:

```shell
bin/setup
```

### Available services

You should now have the following services running:

- `synapse` (Matrix server): http://localhost:8008
- `element` (Matrix client): http://localhost:8009 [user: `admin`, password: `admin`]
- `maubot` (Maubot's Admin UI): http://localhost:29316 [user: `admin`, password: `admin`]
- `postgres` (Database server): `postgresql://postgres:postgres@localhost:5432`

The homeserver domain is `matrix-bots-wporg.local`. An `@admin` Matrix user and a respective Maubot _client_ should have been created. You can use that client to test and develop plugins.

## Custom plugins

Custom plugins are plugins that have been developed by the WordPress.org community. Their source code is contained in this repo (under `plugins/`), and they are made available to the production Maubot through the [Docker image](#docker-image).

> To develop custom plugins, you'll need a [development environment](#development-environment) running locally.

### Building a plugin
You can build a custom plugin and deploy it to the local Maubot instance with the following command (`plugins/example` is the path to the directory containing the plugin you want to build and deploy):

```shell
bin/build plugins/example
```

The local Maubot instance will automatically start using the newly-built version of the plugin.

### Creating a new plugin
TODO

### Start from scratch
If you wish to delete all containers and data, you can use the following script, which will restore the local checkout of the repository to its initial state, as if it had just been cloned:

```shell
bin/wipe
```

## Docker image
This repository provides the [Docker image for `community.wordpress.org`'s Maubot instance](https://github.com/Automattic/matrix-bots-wporg/pkgs/container/matrix-bots-wporg). The image is exactly the same as [Maubot's official image](https://mau.dev/maubot/maubot/container_registry/6?orderBy=NAME&sort=desc&search[]=), but with plugins placed in `/data/plugins`.

Since `community.wordpress.org`'s Maubot instance does not (deliberately) allow uploading plugins through the Admin UI, the only plugins that will be available are the ones bundled into this Docker image.

### Issuing a new release
To issue a new release of the image, edit the `version` file so that it contains the version you want to release. The versioning scheme used is: whatever Maubot's version is, with an extra decimal. For example, if Maubot's version (in `Dockerfile`) is `v0.4.2`, the `version` file would contain something like:

```
v0.4.2.0
```

Then commit the `version` file and push. A [GitHub Action](https://github.com/Automattic/matrix-bots-wporg/actions/workflows/publish-image.yml) will then publish the Docker image to the [GitHub Container Registry](https://github.com/Automattic/matrix-bots-wporg/pkgs/container/matrix-bots-wporg).

## Deploying
TODO
