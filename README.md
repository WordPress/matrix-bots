# maubot
This repository provides a Docker image for [Maubot](https://maubot.xyz) (Matrix bot engine) which can be used in environments where there is no persistent storage. Since Maubot reads available plugins from the disk (from e.g. `/data/plugins`), in such an environment, a redeploy would result in the list of plugins being empty.

Effective use of this image also requires disabling plugin uploads through Maubot's configuration, otherwise uploaded plugins would be missing after a redeploy:

```yaml
api_features:
  plugin_upload: false
```

This Docker image is exactly the same as [Maubot's official image](https://mau.dev/maubot/maubot/container_registry/6?orderBy=NAME&sort=desc&search[]=), but with the `plugins/` directory copied into `/data/plugins`.

## Issuing a new release
First fetch plugins:

```shell
bin/fetch-plugins
```

Then edit the `version` file so that it contains the version you want to release. The versioning scheme used is: whatever Maubot's version is, with an extra decimal. For example, if Maubot's version (in `Dockerfile`) is `v0.4.2`, the `version` file would contain something like:

```
v0.4.2.0
```

Then commit and push. A GitHub action will then publish the Docker image to the [GitHub Container Registry](https://github.com/Automattic/matrix-bots-wporg/pkgs/container/maubot).

## Development environment
Start by cloning the repository:

```shell
git clone git@github.com:Automattic/matrix-bots-wporg.git
cd matrix-bots-wporg
```

From the repo root, run:

```shell
docker compose up
```

Wait for synapse container to say `No more background updates`, then stop containers and restart:

```shell
# ctrl-c to stop containers, then:
docker compose up
```

## Usage
TODO
