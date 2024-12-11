import pika


def send_message(target: str, message, header=None):
    exchange = target + "Exchange"
    routing_key = target

    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.exchange_declare(exchange=exchange, exchange_type='direct')
    channel.queue_declare(queue=routing_key, durable=True)
    channel.queue_bind(exchange=exchange, queue=routing_key, routing_key=routing_key)

    if not message:
        message = "OK"

    if header:
        properties = pika.BasicProperties(headers=header)
        channel.basic_publish(exchange=exchange, routing_key=routing_key, body=message, properties=properties)
    else:
        channel.basic_publish(exchange=exchange, routing_key=routing_key, body=message)
    # print(f"Sent: {message}")
    connection.close()
