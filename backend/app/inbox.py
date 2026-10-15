import asyncio

_loop: asyncio.AbstractEventLoop | None = None
_subscribers: dict[asyncio.Queue, tuple[str, int | None]] = {}


def bind_loop() -> None:
    global _loop
    _loop = asyncio.get_running_loop()


def publish(event: dict) -> None:
    loop = _loop
    if loop is None or not loop.is_running():
        return
    loop.call_soon_threadsafe(_deliver, event)


def _deliver(event: dict) -> None:
    audience = event.get("audience", "admin")
    company_id = event.get("company_id")
    for queue, (sub_audience, sub_company) in list(_subscribers.items()):
        if sub_audience != audience:
            continue
        if audience == "company" and sub_company != company_id:
            continue
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


def listen(audience: str = "admin", company_id: int | None = None) -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue(maxsize=16)
    _subscribers[queue] = (audience, company_id)
    return queue


def close(queue: asyncio.Queue) -> None:
    _subscribers.pop(queue, None)
