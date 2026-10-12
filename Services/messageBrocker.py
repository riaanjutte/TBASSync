from typing import Callable, Any

class MessageBrocker:

    def __init__(self):
        self.consoleMessageHooks = list[Callable[[str], Any]]()
        self.progressHooks = list[Callable[[float], Any]]()
        self.progressSuccessHooks = list[Callable[[], Any]]()
        self.skinSyncHooks = list[Callable[[str, Any, Any], Any]]()

    #SINGLETON MANAGEMENT
    _instance = None

    @staticmethod
    def getSingletonInstance():
        if MessageBrocker._instance is None:
            MessageBrocker._instance = MessageBrocker()
        return MessageBrocker._instance

    #EXTERNAL INTERRACTIONS
    # --- CONSOLE MESSAGES
    @staticmethod
    def emitConsoleMessage(consoleText: str) -> None:
       brocker_instance = MessageBrocker.getSingletonInstance()
       for hook in brocker_instance.consoleMessageHooks:
           hook(consoleText)

    @staticmethod
    def registerConsoleHook(callback: Callable[[str], Any]):
        brocker_instance = MessageBrocker.getSingletonInstance()
        brocker_instance.consoleMessageHooks.append(callback)

    # --- PROGRESS MESSAGES
    @staticmethod
    def emitProgress(percentage: float) -> None:
       brocker_instance = MessageBrocker.getSingletonInstance()
       for hook in brocker_instance.progressHooks:
           hook(percentage)

    @staticmethod
    def registerProgressHook(callback: Callable[[float], Any]):
        brocker_instance = MessageBrocker.getSingletonInstance()
        brocker_instance.progressHooks.append(callback)

    # --- PROGRESS SUCCESS (downloads complete -> turn bar green at 100%)
    @staticmethod
    def emitProgressSuccess() -> None:
       brocker_instance = MessageBrocker.getSingletonInstance()
       for hook in brocker_instance.progressSuccessHooks:
           hook()

    @staticmethod
    def registerProgressSuccessHook(callback: Callable[[], Any]):
        brocker_instance = MessageBrocker.getSingletonInstance()
        brocker_instance.progressSuccessHooks.append(callback)

    # --- PER-SKIN SYNC EVENTS (emitted from download worker threads)
    # event: "started" (value None), "progress" (value 0..1), "done" (value True/False = success)
    @staticmethod
    def emitSkinSyncEvent(event: str, skin, value=None) -> None:
       brocker_instance = MessageBrocker.getSingletonInstance()
       for hook in brocker_instance.skinSyncHooks:
           hook(event, skin, value)

    @staticmethod
    def registerSkinSyncHook(callback: Callable[[str, Any, Any], Any]):
        brocker_instance = MessageBrocker.getSingletonInstance()
        brocker_instance.skinSyncHooks.append(callback)
