# matrix-bots-wporg
The `community.wordpress.org` Matrix server relies on bots (non-human users) that perform a variety of tasks. Bots can react to messages posted on Matrix, and/or post to Matrix whenever _something_ happens.

Bots run in a _bot engine_ called [Maubot](https://maubot.xyz), which provides a Web UI through which bots can be created and configured. Maubot bots are implemented in Python, and are known as _Plugins_. There is an [ecosystem of existing plugins](https://plugins.mau.bot/) for Maubot, and custom plugins can be implemented as well.

This repository provides the following:

1. Documentation on how to [configure bots through Maubot's Web UI](#configuring-bots)
2. The source code for [custom plugins](#custom-plugins) used in `community.wordpress.org`
3. [Local development environment](#development-environment) to test, modify and create plugins
4. Automation to produce the [Docker image](#docker-image) for `community.wordpress.org`'s Maubot instance
5. Documentation on how to [deploy](#deploying) Maubot so that it uses the latest docker image

## Configuring bots
TODO

## Custom plugins
> You'll need a development environment running locally, see [Development environment](#development-environment) for instructions on how to set it up.

```shell
bin/build plugins/helloworld
```

## Development environment
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

You should now have the following services running:

- `synapse` (Matrix server): http://localhost:8008
- `element` (Matrix client): http://localhost:8009 [user: `admin`, password: `admin`]
- `maubot` (Maubot's Web UI): http://localhost:29316 [user: `admin`, password: `admin`]
- `postgres` (Database server): `postgresql://postgres:postgres@localhost:5432`

If you wish to delete all containers and data, you can use the following script, which will restore the local checkout of the repository to its initial state, as if it had just been cloned:

```shell
bin/wipe
```

## Docker image
This repository provides the [Docker image for `community.wordpress.org`'s Maubot instance](https://github.com/Automattic/matrix-bots-wporg/pkgs/container/matrix-bots-wporg). The image is exactly the same as [Maubot's official image](https://mau.dev/maubot/maubot/container_registry/6?orderBy=NAME&sort=desc&search[]=), but with plugins placed in `/data/plugins`.

Since `community.wordpress.org`'s Maubot instance does not (deliberately) allow uploading plugins through the Web UI, the only plugins that will be available are the ones bundled into this Docker image.

### Issuing a new release
To issue a new release of the image, edit the `version` file so that it contains the version you want to release. The versioning scheme used is: whatever Maubot's version is, with an extra decimal. For example, if Maubot's version (in `Dockerfile`) is `v0.4.2`, the `version` file would contain something like:

```
v0.4.2.0
```

Then commit the `version` file and push. A [GitHub Action](https://github.com/Automattic/matrix-bots-wporg/actions/workflows/publish-image.yml) will then publish the Docker image to the [GitHub Container Registry](https://github.com/Automattic/matrix-bots-wporg/pkgs/container/matrix-bots-wporg).


## Deploying
TODO
