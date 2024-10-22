from agent_network.network.executable import Executable
import threading
from abc import abstractmethod

import pika

from agent_network.utils.message import send_message


class Route:
    def __init__(self, graph, source):
        self.graph = graph
        self.source = source
        self.contact_list = dict()

    def add_contact(self, target, message_type):
        self.contact_list[target] = message_type

    def execute(self, target, message):
        if target == "COMPLETE":
            return "COMPLETE"
        assert target in self.contact_list, f"{target} is not in {self.source}'s contact_list!"
        if self.contact_list[target] == "system":
            return self.graph.get_node(target).execute(message)
        elif self.contact_list[target] == "message":
             return self.graph.get_node(target).execute(message)
            # return send_message(target, message)
        else:
            raise "message type must be system or message"
        # if self.source == "start":
        #     graph.get_node(self.target).execute(task)
        # elif self.target == "end":
        #     return
        # else:
        #     # TODO 根据type进行消息传递
        #     graph.get_node(self.target).execute(task)


class RabbitMQRoute(Route):
    def __init__(self, graph, source, exchange_name, queue_name):
        super().__init__(graph, source)
        self.exchange_name = exchange_name
        self.queue_name = queue_name
        # self.start_communication()

    def start_communication(self):
        self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
        self.channel = self.connection.channel()

        exchange_name = self.exchange_name
        queue_name = self.queue_name

        self.channel.exchange_declare(exchange=exchange_name, exchange_type='direct')
        self.channel.queue_declare(queue=queue_name, durable=True)
        self.channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=queue_name)
        self.channel.basic_consume(queue=queue_name, on_message_callback=self.on_message, auto_ack=True)
        self.channel.start_consuming()

    def execute(self, target, message):
        if target == "COMPLETE":
            return "COMPLETE"
        assert target in self.contact_list, f"target is not in {self.source}'s contact_list!"
        if self.contact_list[target] == "system":
            return self.graph.get_node(target).execute(message)
        elif self.contact_list[target] == "message":
            exchange_name = f"{self.queue_name}WaitingForACKExchange"
            queue_name = f"{self.queue_name}WaitingForACK"
            
            send_message(target, message, header={"message_from": queue_name})

            self.connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
            self.channel = self.connection.channel()
            self.channel.exchange_declare(exchange=exchange_name, exchange_type='direct')
            self.channel.queue_declare(queue=queue_name, durable=True)
            self.channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=queue_name)
            self.channel.basic_consume(queue=queue_name, on_message_callback=self.on_message, auto_ack=True)
            self.channel.start_consuming()

        else:
            raise "message type must be system or message"

    def on_message(self, ch, method, properties, body):
        results = self.graph.get_node(self.source).execute(body)
        message_from = properties["message_from"]
        send_message(message_from, results)
