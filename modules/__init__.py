def register_modules(app, mcp_adapter):
    # Import and register all modules here
    from . import weather
    weather.register(app, mcp_adapter)
    # Add more modules as needed
