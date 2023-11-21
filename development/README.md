# Development environments

> This directory contains files that are only relevant for local development environments.
> The production environment does not rely on this directory in any way.

If you want to implement a custom Maubot plugin (or test existing ones), you can do so locally using Docker. This repository provides a pre-configured Matrix _node_, which includes Synapse (the homeserver), Element (a Matrix client) and Maubot, so you can run plugins locally.

## Initial setup
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
