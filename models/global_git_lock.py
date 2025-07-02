import threading

# Global lock registry for participant git operations (code + logging)
_git_lock_registry = {}
_git_lock_registry_mutex = threading.Lock()

def get_participant_git_lock(participant_id: str) -> threading.RLock:
    """
    Get or create a global reentrant lock for a participant's git operations.
    This lock should be acquired before any git operation in either the code or logging repo.
    """
    with _git_lock_registry_mutex:
        if participant_id not in _git_lock_registry:
            _git_lock_registry[participant_id] = threading.RLock()
        return _git_lock_registry[participant_id]
