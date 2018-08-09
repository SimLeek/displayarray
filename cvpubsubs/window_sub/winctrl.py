import pubsub


class WinCtrl:

    @staticmethod
    def key_stroke(key_entered):
        pubsub.publish("CVKeyStroke", key_entered)

    @staticmethod
    def quit():
        pubsub.publish("CVWinCmd", "quit")
