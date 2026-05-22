"""浠诲姟璺熻釜鍣?- 鐢ㄤ簬浼橀泤鍏抽棴锛堢嚎绋嬪畨鍏ㄏ级"""
import threading

_lock = threading.Lock()
_active_tasks: int = 0
_shutting_down: bool = False


def is_shutting_down() -> bool:
    return _shutting_down


def start_task() -> bool:
    global _active_tasks, _shutting_down
    with _lock:
        if _shutting_down:
            return False
        _active_tasks += 1
    return True


def end_task():
    global _active_tasks
    with _lock:
        _active_tasks -= 1


def get_active_count() -> int:
    with _lock:
        return _active_tasks


def set_shutting_down():
    global _shutting_down
    with _lock:
        _shutting_down = True