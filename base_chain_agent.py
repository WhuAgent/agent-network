from base import BaseAgent
from utils_agent import ScoreAgent


class BaseChainAgent(BaseAgent):

    def __init__(self, logger, demand, chains_agent: [BaseAgent]):
        super().__init__(logger, demand)
        self.chains = [chains_agent]

    def agent(self, current_demand=None):
        result = None
        for chain in self.chains:
            result = chain.agent(current_demand)
            current_demand = result
        return result


class BaseCandidateAgent(BaseAgent):

    def __init__(self, logger, demand, candidate_agent: [BaseAgent], score_max_count):
        super().__init__(logger, demand)
        self.chains = [candidate_agent]
        self.score_agent = ScoreAgent(logger, demand)
        self.score_max_count = score_max_count

    def agent_score(self, sub_results):
        return self.score_agent.agent(sub_results)

    def agent(self, current_demand=None):
        candidate_results = []
        for chain in self.chains:
            result = chain.agent(current_demand)
            candidate_results.append(result)
        score_list = self.agent_score(candidate_results)
        return [candidate_results[score_index] for score_index in score_list[:self.score_max_count]]
