import asyncio

_loop: asyncio.AbstractEventLoop | None = None
_subscribers: set[asyncio.Queue] = set()


def bind_loop() -> None:
    global _loop
    _loop = asyncio.get_running_loop()


def publish(event: dict) -> None:
    loop = _loop
    if loop is None or not loop.is_running():
        return
    loop.call_soon_threadsafe(_deliver, event)


def _deliver(event: dict) -> None:
    for queue in list(_subscribers):
        try:
            queue.put_nowait(event)
        except asyncio.QueueFull:
            try:
                queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                pass


def listen() -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue(maxsize=16)
    _subscribers.add(queue)
    return queue


def close(queue: asyncio.Queue) -> None:
    _subscribers.discard(queue)
