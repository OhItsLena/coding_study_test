"""
Async GitHub service for the coding study Flask application.
Handles GitHub operations in background threads to prevent UI blocking.
"""

import threading
import queue
import time
import json
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from .github_service import GitHubService
from .study_logger import StudyLogger


class GitHubOperation:
    """Represents a GitHub operation to be processed asynchronously."""
    
    def __init__(self, operation_type: str, participant_id: str, **kwargs):
        self.operation_type = operation_type
        self.participant_id = participant_id
        self.kwargs = kwargs
        self.timestamp = datetime.now()
        self.retry_count = 0
        self.max_retries = 3


class AsyncGitHubService:
    """
    Async wrapper for GitHub operations using background threading.
    Provides non-blocking GitHub operations for better UI responsiveness.
    """
    
    def __init__(self, github_service: GitHubService, study_logger: StudyLogger):
        self.github_service = github_service
        self.study_logger = study_logger
        self.operation_queue = queue.Queue()
        self.failed_operations = []
        self.worker_thread = None
        self.shutdown_event = threading.Event()
        self.stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'queue_size': 0
        }
        
        # Start the background worker
        self.start_worker()
    
    def start_worker(self):
        """Start the background worker thread."""
        if self.worker_thread is None or not self.worker_thread.is_alive():
            # Reset shutdown event for new worker
            self.shutdown_event.clear()
            self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
            self.worker_thread.start()
            print("AsyncGitHubService: Background worker started")
    
    def stop_worker(self):
        """Stop the background worker thread."""
        self.shutdown_event.set()
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=10)
            print("AsyncGitHubService: Background worker stopped")
    
    def _worker_loop(self):
        """Main worker loop that processes queued operations."""
        print("AsyncGitHubService: Worker loop started")
        
        while not self.shutdown_event.is_set():
            try:
                # Get operation from queue with timeout
                try:
                    operation = self.operation_queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                # Update stats
                self.stats['total_operations'] += 1
                self.stats['queue_size'] = self.operation_queue.qsize()
                
                # Process the operation
                success = self._process_operation(operation)
                
                if success:
                    self.stats['successful_operations'] += 1
                else:
                    self.stats['failed_operations'] += 1
                    
                    # Retry failed operations
                    if operation.retry_count < operation.max_retries:
                        operation.retry_count += 1
                        print(f"AsyncGitHubService: Retrying operation {operation.operation_type} "
                              f"for {operation.participant_id} (attempt {operation.retry_count})")
                        self.operation_queue.put(operation)
                    else:
                        print(f"AsyncGitHubService: Operation {operation.operation_type} "
                              f"for {operation.participant_id} failed permanently")
                        self.failed_operations.append(operation)
                
                # Mark task as done
                self.operation_queue.task_done()
                
            except Exception as e:
                print(f"AsyncGitHubService: Worker error: {str(e)}")
                continue
    
    def _process_operation(self, operation: GitHubOperation) -> bool:
        """Process a single GitHub operation."""
        try:
            print(f"AsyncGitHubService: Processing {operation.operation_type} "
                  f"for {operation.participant_id}")
            
            if operation.operation_type == 'log_route_visit':
                return self._process_log_route_visit(operation)
            elif operation.operation_type == 'commit_code_changes':
                return self._process_commit_code_changes(operation)
            elif operation.operation_type == 'test_connectivity':
                return self._process_test_connectivity(operation)
            elif operation.operation_type == 'mark_stage_transition':
                return self._process_mark_stage_transition(operation)
            else:
                print(f"AsyncGitHubService: Unknown operation type: {operation.operation_type}")
                return False
                
        except Exception as e:
            print(f"AsyncGitHubService: Error processing {operation.operation_type}: {str(e)}")
            return False
    
    def _process_log_route_visit(self, operation: GitHubOperation) -> bool:
        """Process route visit logging operation."""
        try:
            return self.study_logger.log_route_visit(
                participant_id=operation.participant_id,
                route_name=operation.kwargs.get('route_name'),
                development_mode=operation.kwargs.get('development_mode'),
                study_stage=operation.kwargs.get('study_stage'),
                session_data=operation.kwargs.get('session_data'),
                github_token=operation.kwargs.get('github_token'),
                github_org=operation.kwargs.get('github_org')
            )
        except Exception as e:
            print(f"AsyncGitHubService: Route visit logging failed: {str(e)}")
            return False
    
    def _process_commit_code_changes(self, operation: GitHubOperation) -> bool:
        """Process code commit operation."""
        try:
            # Import repository manager to avoid circular imports
            from .repository_manager import RepositoryManager
            repo_manager = RepositoryManager(self.github_service)
            return repo_manager.commit_code_changes(
                participant_id=operation.participant_id,
                study_stage=operation.kwargs.get('study_stage'),
                commit_message=operation.kwargs.get('commit_message'),
                development_mode=operation.kwargs.get('development_mode'),
                github_token=operation.kwargs.get('github_token'),
                github_org=operation.kwargs.get('github_org')
            )
        except Exception as e:
            print(f"AsyncGitHubService: Code commit failed: {str(e)}")
            return False
    
    def _process_test_connectivity(self, operation: GitHubOperation) -> bool:
        """Process GitHub connectivity test."""
        try:
            return self.github_service.test_github_connectivity(
                participant_id=operation.participant_id,
                github_token=operation.kwargs.get('github_token'),
                github_org=operation.kwargs.get('github_org')
            )
        except Exception as e:
            print(f"AsyncGitHubService: Connectivity test failed: {str(e)}")
            return False
    
    def _process_mark_stage_transition(self, operation: GitHubOperation) -> bool:
        """Process stage transition marking."""
        try:
            return self.study_logger.mark_stage_transition(
                participant_id=operation.participant_id,
                from_stage=operation.kwargs.get('from_stage'),
                to_stage=operation.kwargs.get('to_stage'),
                development_mode=operation.kwargs.get('development_mode'),
                github_token=operation.kwargs.get('github_token'),
                github_org=operation.kwargs.get('github_org')
            )
        except Exception as e:
            print(f"AsyncGitHubService: Stage transition marking failed: {str(e)}")
            return False
    
    # Public async methods
    def queue_log_route_visit(self, participant_id: str, route_name: str, 
                            development_mode: bool, study_stage: int,
                            session_data: Optional[Dict] = None,
                            github_token: Optional[str] = None,
                            github_org: Optional[str] = None):
        """Queue a route visit logging operation."""
        operation = GitHubOperation(
            operation_type='log_route_visit',
            participant_id=participant_id,
            route_name=route_name,
            development_mode=development_mode,
            study_stage=study_stage,
            session_data=session_data,
            github_token=github_token,
            github_org=github_org
        )
        self.operation_queue.put(operation)
        print(f"AsyncGitHubService: Queued route visit logging for {participant_id}")
    
    def queue_commit_code_changes(self, participant_id: str, study_stage: int,
                                commit_message: str, development_mode: bool,
                                github_token: Optional[str] = None,
                                github_org: Optional[str] = None):
        """Queue a code commit operation."""
        operation = GitHubOperation(
            operation_type='commit_code_changes',
            participant_id=participant_id,
            study_stage=study_stage,
            commit_message=commit_message,
            development_mode=development_mode,
            github_token=github_token,
            github_org=github_org
        )
        self.operation_queue.put(operation)
        print(f"AsyncGitHubService: Queued code commit for {participant_id}")
    
    def queue_test_connectivity(self, participant_id: str, github_token: Optional[str] = None,
                              github_org: Optional[str] = None):
        """Queue a GitHub connectivity test."""
        operation = GitHubOperation(
            operation_type='test_connectivity',
            participant_id=participant_id,
            github_token=github_token,
            github_org=github_org
        )
        self.operation_queue.put(operation)
        print(f"AsyncGitHubService: Queued connectivity test for {participant_id}")
    
    def queue_mark_stage_transition(self, participant_id: str, from_stage: int, to_stage: int,
                                  development_mode: bool, github_token: Optional[str] = None,
                                  github_org: Optional[str] = None):
        """Queue a stage transition marking operation."""
        operation = GitHubOperation(
            operation_type='mark_stage_transition',
            participant_id=participant_id,
            from_stage=from_stage,
            to_stage=to_stage,
            development_mode=development_mode,
            github_token=github_token,
            github_org=github_org
        )
        self.operation_queue.put(operation)
        print(f"AsyncGitHubService: Queued stage transition for {participant_id}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get current operation statistics."""
        self.stats['queue_size'] = self.operation_queue.qsize()
        self.stats['failed_operations_count'] = len(self.failed_operations)
        self.stats['worker_alive'] = self.worker_thread.is_alive() if self.worker_thread else False
        return self.stats.copy()
    
    def get_queue_size(self) -> int:
        """Get current queue size."""
        return self.operation_queue.qsize()
    
    def wait_for_completion(self, timeout: Optional[float] = None):
        """Wait for all queued operations to complete."""
        print("AsyncGitHubService: Waiting for queue completion...")
        self.operation_queue.join()
        print("AsyncGitHubService: All operations completed")
