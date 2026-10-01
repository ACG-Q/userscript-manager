_commands: dict = {}

def register(name: str):
    def decorator(func):
        _commands[name] = func
        return func
    return decorator

def get_command(name: str):
    return _commands.get(name)

def get_all_commands() -> dict:
    return _commands.copy()