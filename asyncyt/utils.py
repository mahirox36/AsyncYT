import inspect

__all__ = ["call_callback"]

async def call_callback(callback, *args, **kwargs):
    if inspect.iscoroutinefunction(callback):
        await callback(*args, **kwargs)
    else:
        callback(*args, **kwargs)
