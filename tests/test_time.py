"""Test the advanced schedulers."""

import unittest
from unittest import TestCase, mock

from mesa.agent import Agent
from mesa.model import Model
from mesa.time import (
    BaseScheduler,
    RandomActivation,
    RandomActivationByType,
    SimultaneousActivation,
    StagedActivation,
)

RANDOM = "random"
STAGED = "staged"
SIMULTANEOUS = "simultaneous"
RANDOM_BY_TYPE = "random_by_type"


class MockAgent(Agent):
    """Minimalistic agent for testing purposes."""

    def __init__(self, model):  # noqa: D107
        super().__init__(model)
        self.steps = 0
        self.advances = 0

    def kill_other_agent(self):  # noqa: D102
        for agent in self.model.schedule.agents:
            if agent is not self:
                agent.remove()

    def stage_one(self):  # noqa: D102
        if self.model.enable_kill_other_agent:
            self.kill_other_agent()
        self.model.log.append(f"{self.unique_id}_1")

    def stage_two(self):  # noqa: D102
        self.model.log.append(f"{self.unique_id}_2")

    def advance(self):  # noqa: D102
        self.advances += 1

    def step(self):  # noqa: D102
        if self.model.enable_kill_other_agent:
            self.kill_other_agent()
        self.steps += 1
        self.model.log.append(self.unique_id)


class MockModel(Model):  # Noqa: D101
    def __init__(
        self, shuffle=False, activation=STAGED, enable_kill_other_agent=False, seed=None
    ):
        """Creates a Model instance with a schedule.

        Args:
            shuffle (Bool): whether or not to instantiate a scheduler
                            with shuffling.
                            This option is only used for
                            StagedActivation schedulers.

            activation (str): which kind of scheduler to use.
                              'random' creates a RandomActivation scheduler.
                              'staged' creates a StagedActivation scheduler.
                              The default scheduler is a BaseScheduler.
            enable_kill_other_agent: whether or not to enable kill_other_agent
            seed : rng
        """
        super().__init__(seed=seed)
        self.log = []
        self.enable_kill_other_agent = enable_kill_other_agent

        # Make scheduler
        if activation == STAGED:
            model_stages = ["stage_one", "model.model_stage", "stage_two"]
            self.schedule = StagedActivation(
                self, stage_list=model_stages, shuffle=shuffle
            )
        elif activation == RANDOM:
            self.schedule = RandomActivation(self)
        elif activation == SIMULTANEOUS:
            self.schedule = SimultaneousActivation(self)
        elif activation == RANDOM_BY_TYPE:
            self.schedule = RandomActivationByType(self)
        else:
            self.schedule = BaseScheduler(self)

        # Make agents
        for _ in range(2):
            agent = MockAgent(self)
            self.schedule.add(agent)

    def step(self):  # noqa: D102
        self.schedule.step()

    def model_stage(self):  # noqa: D102
        self.log.append("model_stage")


class TestStagedActivation(TestCase):
    """Test the staged activation."""

    expected_output = ["1_1", "1_1", "model_stage", "1_2", "1_2"]

    def test_no_shuffle(self):
        """Testing the staged activation without shuffling."""
        model = MockModel(shuffle=False)
        model.step()
        model.step()
        assert all(i == j for i, j in zip(model.log[:5], model.log[5:]))

    def test_shuffle(self):
        """Test the staged activation with shuffling."""
        model = MockModel(shuffle=True)
        model.step()
        for output in self.expected_output[:2]:
            assert output in model.log[:2]
        for output in self.expected_output[3:]:
            assert output in model.log[3:]
        assert self.expected_output[2] == model.log[2]

    def test_shuffle_shuffles_agents(self):  # noqa: D102
        model = MockModel(shuffle=True)
        a = mock.Mock()
        model.schedule._agents.random = a
        assert a.shuffle.call_count == 0
        model.step()
        assert a.shuffle.call_count == 1

    def test_remove(self):
        """Test the staged activation can remove an agent."""
        model = MockModel(shuffle=True)
        agents = list(model.schedule._agents)
        agent = agents[0]
        model.schedule.remove(agents[0])
        assert agent not in model.schedule.agents

    def test_intrastep_remove(self):
        """Test the staged activation can remove an agent in a step of another agent.

        so that the one removed doesn't step.
        """
        model = MockModel(shuffle=True, enable_kill_other_agent=True)
        model.step()
        assert len(model.log) == 3

    def test_add_existing_agent(self):  # noqa: D102
        model = MockModel()
        agent = model.schedule.agents[0]
        with self.assertRaises(Exception):
            model.schedule.add(agent)


class TestRandomActivation(TestCase):
    """Test the random activation."""

    def test_init(self):  # noqa: D102
        model = Model()
        agents = [MockAgent(model) for _ in range(10)]

        scheduler = RandomActivation(model, agents)
        assert all(agent in scheduler.agents for agent in agents)

    def test_random_activation_step_shuffles(self):
        """Test the random activation step."""
        model = MockModel(activation=RANDOM)
        a = mock.Mock()
        model.schedule._agents.random = a
        model.schedule.step()
        assert a.shuffle.call_count == 1

    def test_random_activation_step_increments_step_and_time_counts(self):
        """Test the random activation step increments step and time counts."""
        model = MockModel(activation=RANDOM)
        assert model.schedule.steps == 0
        assert model.schedule.time == 0
        model.schedule.step()
        assert model.schedule.steps == 1
        assert model.schedule.time == 1

    def test_random_activation_step_steps_each_agent(self):
        """Test the random activation step causes each agent to step."""
        model = MockModel(activation=RANDOM)
        model.step()
        agent_steps = [i.steps for i in model.schedule.agents]
        # one step for each of 2 agents
        assert all(x == 1 for x in agent_steps)

    def test_intrastep_remove(self):
        """Test the random activation can remove an agent in a step of another agent.

        so that the one removed doesn't step.
        """
        model = MockModel(activation=RANDOM, enable_kill_other_agent=True)
        model.step()
        assert len(model.log) == 1

    def test_get_agent_keys(self):  # noqa: D102
        model = MockModel(activation=RANDOM)

        keys = model.schedule.get_agent_keys()
        agent_ids = [agent.unique_id for agent in model.agents]
        assert all(entry_i == entry_j for entry_i, entry_j in zip(keys, agent_ids))

        keys = model.schedule.get_agent_keys(shuffle=True)
        agent_ids = {agent.unique_id for agent in model.agents}
        assert all(entry in agent_ids for entry in keys)

    def test_not_sequential(self):  # noqa: D102
        model = MockModel(activation=RANDOM)
        # Create 10 agents
        for _ in range(10):
            model.schedule.add(MockAgent(model))
        # Run 3 steps
        for _ in range(3):
            model.step()
        # Filter out non-integer elements from the log
        filtered_log = [item for item in model.log if isinstance(item, int)]

        # Check that there are no 18 consecutive agents id's in the filtered log
        total_agents = 10
        assert not any(
            all(
                (filtered_log[(i + j) % total_agents] - filtered_log[i]) % total_agents
                == j % total_agents
                for j in range(18)
            )
            for i in range(len(filtered_log))
        ), f"Agents are activated sequentially:\n{filtered_log}"


class TestSimultaneousActivation(TestCase):
    """Test the simultaneous activation."""

    def test_simultaneous_activation_step_steps_and_advances_each_agent(self):
        """Test the simultaneous activation step causes each agent to step."""
        model = MockModel(activation=SIMULTANEOUS)
        model.step()
        # one step for each of 2 agents
        agent_steps = [i.steps for i in model.schedule.agents]
        agent_advances = [i.advances for i in model.schedule.agents]
        assert all(x == 1 for x in agent_steps)
        assert all(x == 1 for x in agent_advances)


class TestRandomActivationByType(TestCase):
    """Test the random activation by type.

    TODO implement at least 2 types of agents, and test that step_type only
    does step for one type of agents, not the entire agents.
    """

    def test_init(self):  # noqa: D102
        model = Model()
        agents = [MockAgent(model) for _ in range(10)]
        agents += [Agent(model) for _ in range(10)]

        scheduler = RandomActivationByType(model, agents)
        assert all(agent in scheduler.agents for agent in agents)

    def test_random_activation_step_shuffles(self):
        """Test the random activation by type step."""
        model = MockModel(activation=RANDOM_BY_TYPE)
        a = mock.Mock()
        model.random = a
        for agentset in model.schedule._agents_by_type.values():
            agentset.random = a
        model.schedule.step()
        assert a.shuffle.call_count == 2

    def test_random_activation_step_increments_step_and_time_counts(self):
        """Test the random activation by type step increments step and time counts."""
        model = MockModel(activation=RANDOM_BY_TYPE)
        assert model.schedule.steps == 0
        assert model.schedule.time == 0
        model.schedule.step()
        assert model.schedule.steps == 1
        assert model.schedule.time == 1

    def test_random_activation_step_steps_each_agent(self):
        """Test the random activation by type step causes each agent to step."""
        model = MockModel(activation=RANDOM_BY_TYPE)
        model.step()
        agent_steps = [i.steps for i in model.schedule.agents]
        # one step for each of 2 agents
        assert all(x == 1 for x in agent_steps)

    def test_random_activation_counts(self):
        """Test the random activation by type step causes each agent to step."""
        model = MockModel(activation=RANDOM_BY_TYPE)

        agent_types = model.agent_types
        for agent_type in agent_types:
            assert model.schedule.get_type_count(agent_type) == len(
                model.agents_by_type[agent_type]
            )

    # def test_add_non_unique_ids(self):
    #     """
    #     Test that adding agent with duplicate ids result in an error.
    #     TODO: we need to run this test on all schedulers, not just
    #     TODO:: identical IDs is something for the agent, not the scheduler and should be tested there
    #     RandomActivationByType.
    #     """
    #     model = MockModel(activation=RANDOM_BY_TYPE)
    #     a = MockAgent(0, model)
    #     b = MockAgent(0, model)
    #     model.schedule.add(a)
    #     with self.assertRaises(Exception):
    #         model.schedule.add(b)


if __name__ == "__main__":
    unittest.main()
