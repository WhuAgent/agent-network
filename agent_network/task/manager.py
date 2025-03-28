from agent_network.task.vertex import TaskVertex
from agent_network.network.vertexes.vertex import ThirdPartyVertex


class TaskManager:
    def __init__(self):
        self.task_cnt = 0
        self.task_queue = dict()
        
        self.cur_execution = []
        self.cur_third_party_execution = []
        self.next_execution = []
        self.next_third_party_execution = []
        
    def get_task(self, id) -> TaskVertex:
        return self.task_queue[id]
    
    def get_tasks(self, ids) -> list[TaskVertex]:
        return [self.task_queue[id] for id in ids]
    
    def get_cur_execution_tasks(self) -> list[TaskVertex]:
        return self.get_tasks(self.cur_execution), self.get_tasks(self.cur_third_party_execution)
    
    def get_next_execution_tasks(self) -> list[TaskVertex]:
        return self.get_tasks(self.next_execution), self.get_tasks(self.next_third_party_execution)

    def add_task(self, task, executable, prev=[], next=[]) -> int:
        self.task_cnt += 1
        manager_new_task_vertex = TaskVertex(executable=executable, task=task, id=self.task_cnt, prev=prev, next=next)
        self.task_queue[self.task_cnt] = manager_new_task_vertex
        
        return manager_new_task_vertex.id
    
    def add_next_tasks(self, cur_task: TaskVertex, ids, tasks, executors):
        cur_task_next = cur_task.get_next()
        next_task_ids = []
        for next_task_id, next_task, next_executor in zip(ids, tasks, executors):
            # 注册任务以更新任务节点图
            if next_task_id is None:
                next_task_id = self.add_task(next_task, 
                                             next_executor,
                                             prev=[cur_task.id], 
                                             next=cur_task.get_next())
            next_task_ids.append(next_task_id)
            
            # 注册到下一个运行
            if isinstance(next_executor, ThirdPartyVertex):
                self.next_third_party_execution.append(next_task_id)
            else:
                self.next_execution.append(next_task_id)
        
        # 更新任务流程图
        for task_id in cur_task_next:
            new_prev = [id for id in next_task_ids if id not in cur_task_next]
            self.task_queue[task_id].prev.extend(new_prev)
        cur_task.next = next_task_ids
        
    
    def add_next_task(self, cur_task: TaskVertex, next_task, executable, task_id=None):
        if task_id is None:
            task_id = self.add_task(next_task, executable, prev=[cur_task.id])
            cur_task.add_next(task_id)
        if isinstance(executable, ThirdPartyVertex):
            self.next_third_party_execution.append(task_id)
        else:
            self.next_execution.append(task_id)
    
    def refresh(self):
        self.cur_execution = self.next_execution
        self.next_execution = []
        self.cur_third_party_execution = self.next_third_party_execution
        self.next_third_party_execution = []
        
    def task_all_completed(self) -> bool:
        return len(self.cur_execution) == 0 and len(self.cur_third_party_execution) == 0
        