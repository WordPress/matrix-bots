# maubot
This repository provides a Docker image for [Maubot](https://maubot.xyz) (Matrix bot engine) which can be used in environments where there is no persistent storage. Since Maubot reads available plugins from the disk (from e.g. `/data/plugins`), in such an environment, a redeploy would result in the list of plugins being empty.

Effective use of this image also requires disabling plugin uploads through Maubot's configuration, otherwise uploaded plugins would be missing after a redeploy:

```yaml
api_features:
  plugin_upload: false
```

This Docker image is exactly the same as [Maubot's official image](https://mau.dev/maubot/maubot/container_registry/6?orderBy=NAME&sort=desc&search[]=), but with the `plugins/` directory copied into `/data/plugins`.
