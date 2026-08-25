"""Domain modules.

Every module in this package follows one contract and nothing else:

    def register(mcp, client) -> None

`register` is called once at startup. Inside it, declare tools, resources, and
prompts with the usual decorators on the `mcp` you were handed, and make HTTP
calls through `client`.

Two rules keep the domains independent, and they are what let you drop a new
file in here without touching the others:

  * a domain module never imports another domain module
  * a domain module never reads os.environ - ask the client instead
"""
