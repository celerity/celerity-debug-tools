# Celerity Debug Tools

`render_graphs.py` can be used to invoke `dot` for all graphs printed by Celerity in logs and tests. To render to .png files in the current directory, Simply prefix the invocation of your application like so:
```sh
python render_graphs.py -- ./my-celerity-application
```
Note that currently, you will have to set `LOG_LEVEL=trace` for the application or pass `--print-graphs` to the test manually.

