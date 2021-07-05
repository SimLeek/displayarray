from displayarray import publish_updates

publish_updates(
    0,
    size=(9999, 9999),
    address="tcp://127.0.0.1:7880",
    topic=b'topic',
    blocking=True
)
