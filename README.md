# Care Quick Assign

Plugin to handle quick auto assignments for newly added patients

## Local Development

To develop the plug in local environment along with care, follow the steps below:

1. Go to the care root directory and clone the plugin repository:

```bash
cd care
git clone git@github.com:ohcnetwork/Care Quick Assign.git
```

2. Add the plugin config in plug_config.py

```python
...

Care Quick Assign_plugin = Plug(
    name=Care Quick Assign, # name of the django app in the plugin
    package_name="/app/Care Quick Assign", # this has to be /app/ + plugin folder name
    version="", # keep it empty for local development
    configs={}, # plugin configurations if any
)
plugs = [Care Quick Assign_plugin]

...
```

3. Tweak the code in plugs/manager.py, install the plugin in editable mode

```python
...

subprocess.check_call(
    [sys.executable, "-m", "pip", "install", "-e", *packages] # add -e flag to install in editable mode
)

...
```

4. Rebuild the docker image and run the server

```bash
make re-build
make up
```

> [!IMPORTANT]
> Do not push these changes in a PR. These changes are only for local development.

## Production Setup

To install care Care Quick Assign, you can add the plugin config in [care/plug_config.py](https://github.com/ohcnetwork/care/blob/develop/plug_config.py) as follows:

```python
...

Care Quick Assign_plug = Plug(
    name=Care Quick Assign,
    package_name="git+https://github.com/ohcnetwork/Care Quick Assign.git",
    version="@master",
    configs={},
)
plugs = [Care Quick Assign_plug]
...
```

[Extended Docs on Plug Installation](https://care-be-docs.ohc.network/pluggable-apps/configuration.html)



This plugin was created with [Cookiecutter](https://github.com/audreyr/cookiecutter) using the [ohcnetwork/care-plugin-cookiecutter](https://github.com/ohcnetwork/care-plugin-cookiecutter).
