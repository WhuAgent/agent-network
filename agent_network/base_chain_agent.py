from base import BaseAgent
from utils_agent import ScoreAgent


class BaseCandidateAgent(BaseAgent):
    def __init__(self, logger, title, task, role, description, history_number, prompts, tools,
                 runtime_revision_number, candidate_agent: [BaseAgent], score_max_count):
        super().__init__(logger, title, task, role, description, history_number, prompts, tools,
                         runtime_revision_number)
        self.candidates = [candidate_agent]
        self.score_agent = ScoreAgent(logger, title, task, role, description, history_number)
        self.score_max_count = score_max_count

    def agent_score(self, sub_results):
        return self.score_agent.agent(sub_results)

    def agent(self, runtime_revision_number, current_task=None):
        if not current_task:
            raise Exception("评分Agent的当前任务不能为空")
        candidate_results = []
        for chain in self.candidates:
            result = chain.agent(current_task)
            candidate_results.append(result)
        score_list = self.agent_score(candidate_results)
        return [candidate_results[score_index] for score_index in score_list[:self.score_max_count]]
